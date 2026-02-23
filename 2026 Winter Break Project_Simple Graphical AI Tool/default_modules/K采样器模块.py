#input_quantity=4
#variable_quantity=11
#userinput=false
#setting=true
#output_quantity=1
#time_late=0
#name=K采样器模块
#excitedbydata=true
#variables_name=模型,正面条件,负面条件,Latent图像,种子,生成后控制,步数,cfg,采样器名称,调度器,降噪
#kind=采样
#output_name=生成的Latent张量

"""
K采样器模块（Inpaint增强版）
核心改进：
1. 加噪后立刻混合mask，仅mask区域保留噪声，确保模型聚焦重绘区域
2. 新增mask边缘高斯模糊，增强提示词引导性
3. 优化CFG默认值，提升提示词权重
4. 修复inpaint mask处理逻辑，确保mask生效且边缘自然
"""
import os
import gc
import traceback
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

import torch
from diffusers import StableDiffusionPipeline
from diffusers import EulerDiscreteScheduler, DDIMScheduler, DPMSolverMultistepScheduler
# 新增：导入模糊所需模块
from torchvision import transforms

# 模型和调度器缓存
_model_cache = {}
_scheduler_cache = {}

def clean_model_cache():
    """清理缓存释放显存"""
    global _model_cache, _scheduler_cache
    for key in list(_model_cache.keys()):
        del _model_cache[key]
    _model_cache.clear()
    _scheduler_cache.clear()
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def get_scheduler(sampler_name, steps, device):
    """
    根据采样器名称创建对应的调度器
    """
    sampler_name = sampler_name or "euler"
    sampler_name = sampler_name.lower()
    
    print(f"创建调度器: {sampler_name}")
    
    if "euler" in sampler_name:
        return EulerDiscreteScheduler(
            num_train_timesteps=1000,
            beta_start=0.00085,
            beta_end=0.012,
            beta_schedule="scaled_linear",
            steps_offset=1
        )
    elif "ddim" in sampler_name:
        return DDIMScheduler(
            num_train_timesteps=1000,
            beta_start=0.00085,
            beta_end=0.012,
            beta_schedule="scaled_linear",
            clip_sample=False,
            set_alpha_to_one=False,
            steps_offset=1,
            prediction_type="epsilon"
        )
    elif "dpm" in sampler_name or "sde" in sampler_name:
        # 支持dpmpp_2m_sde和其他DPM变体
        return DPMSolverMultistepScheduler(
            num_train_timesteps=1000,
            beta_start=0.00085,
            beta_end=0.012,
            beta_schedule="scaled_linear",
            steps_offset=1,
            prediction_type="epsilon",
            solver_type="midpoint"
        )
    else:
        # 默认使用Euler调度器
        return EulerDiscreteScheduler(
            num_train_timesteps=1000,
            beta_start=0.00085,
            beta_end=0.012,
            beta_schedule="scaled_linear",
            steps_offset=1
        )

def execute(model_path=None, positive_embeds=None, negative_embeds=None, latents=None, 
             seed=None, post_control=None, steps=None, cfg=None, sampler_name=None, 
             scheduler_name=None, denoise=None):
    """
    使用diffusers官方标准流程的K采样器实现
    增强Inpaint逻辑，确保提示词引导生效，mask区域精准生成
    """
    # ====================== 1. 基础参数 ======================
    seed = int(seed) if seed is not None else 42
    steps = max(1, int(steps)) if steps is not None else 20
    # 修改1：提升CFG默认值（从8→12），增强提示词引导力
    cfg_scale = float(cfg) if cfg is not None else 12.0
    denoise = max(0.0, min(1.0, float(denoise))) if denoise is not None else 0.6
    
    # 从字典中提取samples张量
    original_latents = latents
    if isinstance(latents, dict) and "samples" in latents:
        latents = latents["samples"]
    
    # 必要校验
    if None in [model_path, positive_embeds, negative_embeds, latents]:
        print("错误：缺少核心输入参数")
        if isinstance(original_latents, dict):
            return original_latents
        return {"samples": latents, "noise_mask": None}
    
    # 第一步：采样最开始的时候
    original_samples = latents.clone()  # 原始latent，全程不动
    noise_mask = None
    if isinstance(original_latents, dict) and "noise_mask" in original_latents:
        noise_mask = original_latents["noise_mask"]
        # 修复：正确的mask形状校验（只对比空间维度）
        if noise_mask is not None and noise_mask.shape[2:] != original_samples.shape[2:]:
            print(f"mask空间形状 {noise_mask.shape[2:]} 与latent空间形状 {original_samples.shape[2:]} 不一致，忽略mask")
            noise_mask = None
        else:
            print(f"使用noise_mask，形状: {noise_mask.shape if noise_mask is not None else 'None'}")
    
    print(f"=== K采样器（Inpaint增强版）参数 ===")
    print(f"种子={seed}, 步数={steps}, CFG={cfg_scale}, 降噪={denoise}")
    print(f"采样器: {sampler_name or 'euler'}")
    print(f"初始Latent形状: {latents.shape}, 设备: {latents.device}")
    
    # 降噪为0时直接返回原图
    if denoise == 0:
        print("降噪值为0，直接返回原始Latent")
        if isinstance(original_latents, dict):
            return original_latents
        return {"samples": latents}
    
    # ====================== 2. 设备和数据类型 ======================
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    print(f"使用设备: {device}, 数据类型: {dtype}")
    
    # 所有张量移到对应设备
    latents = latents.to(device=device, dtype=dtype)
    positive_embeds = positive_embeds.to(device=device, dtype=dtype)
    negative_embeds = negative_embeds.to(device=device, dtype=dtype)
    text_embeddings = torch.cat([negative_embeds, positive_embeds])
    
    # 处理mask：对齐设备、精度+扩展4通道+边缘模糊（关键修改）
    if noise_mask is not None:
        noise_mask = noise_mask.to(device=device, dtype=dtype)
        # 修改2：mask边缘高斯模糊，增强模型对mask区域的关注度
        blur = transforms.GaussianBlur(kernel_size=5, sigma=2)  # 5核模糊，sigma=2（可调整）
        noise_mask_single = noise_mask[:, 0:1, :, :]  # 先转回单通道
        noise_mask_blurred = blur(noise_mask_single)
        noise_mask = noise_mask_blurred.repeat(1, 4, 1, 1)  # 扩展回4通道
        noise_mask = torch.clamp(noise_mask, 0.0, 1.0)  # 限制0~1范围
        print(f"mask模糊+扩展后形状: {noise_mask.shape}")
    
    # ====================== 3. 加载UNet和调度器 ======================
    try:
        # 加载UNet
        if model_path not in _model_cache:
            print("加载UNet模型...")
            pipe = StableDiffusionPipeline.from_single_file(
                model_path,
                torch_dtype=dtype,
                use_safetensors=True,
                safety_checker=None,
                requires_safety_checker=False,
                local_files_only=True
            )
            _model_cache[model_path] = pipe.unet.to(device).eval()
            del pipe
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        unet = _model_cache[model_path]
        
        # 加载或创建调度器
        scheduler_key = f"{sampler_name or 'euler'}_{steps}"
        if scheduler_key not in _scheduler_cache:
            print("初始化调度器...")
            scheduler = get_scheduler(sampler_name, steps, device)
            _scheduler_cache[scheduler_key] = scheduler
        
        scheduler = _scheduler_cache[scheduler_key]
        
    except Exception as e:
        print(f"模型或调度器加载失败: {e}")
        traceback.print_exc()
        clean_model_cache()
        if isinstance(original_latents, dict):
            return original_latents
        return {"samples": latents, "noise_mask": None}
    
    # ====================== 4. 标准采样流程（核心增强） ======================
    try:
        # 设置随机种子
        torch.manual_seed(seed)
        if device == "cuda":
            torch.cuda.manual_seed_all(seed)
        
        # 设置调度器时间步
        scheduler.set_timesteps(steps, device=device)
        timesteps = scheduler.timesteps
        num_inference_steps = steps
        strength = denoise
        
        # 计算实际时间步
        start_step = max(0, num_inference_steps - int(num_inference_steps * strength))
        timesteps = timesteps[start_step:]
        actual_timesteps = timesteps
        
        print(f"实际时间步数量: {len(actual_timesteps)}")
        
        # 图生图：添加噪声 + 关键修改3（仅mask区域保留噪声）
        if strength < 1.0:
            print("\n图生图：添加噪声（仅mask区域）...")
            start_timestep = actual_timesteps[0]
            noise = torch.randn_like(latents, device=device, dtype=dtype)
            
            # 标准化start_timestep
            if isinstance(start_timestep, torch.Tensor):
                start_timestep = start_timestep.unsqueeze(0) if start_timestep.dim() == 0 else start_timestep
            else:
                start_timestep = torch.tensor([start_timestep], device=device, dtype=torch.long)
            
            # 全图加噪后，仅mask区域保留噪声，非mask区域还原原始latent
            latents = scheduler.add_noise(latents, noise, start_timestep)
            if noise_mask is not None:
                latents = noise_mask * latents + (1 - noise_mask) * original_samples.to(device, dtype)
            
            print(f"加噪完成，仅mask区域保留噪声")
        
        # 标准采样循环
        print("\n开始采样循环...")
        with torch.no_grad():
            for i, t in enumerate(actual_timesteps):
                if i % 5 == 0:
                    print(f"采样进度: {i+1}/{len(actual_timesteps)}")
                
                # 进模型前混合mask（核心逻辑）
                current_latents = latents
                if noise_mask is not None:
                    current_latents = noise_mask * latents + (1 - noise_mask) * original_samples.to(device, dtype)
                
                # CFG逻辑
                latent_model_input = torch.cat([current_latents] * 2)
                latent_model_input = scheduler.scale_model_input(latent_model_input, t)
                
                # UNet推理
                try:
                    if device == "cuda":
                        with torch.amp.autocast(device_type="cuda", dtype=dtype):
                            noise_pred = unet(
                                latent_model_input,
                                t,
                                encoder_hidden_states=text_embeddings
                            ).sample
                    else:
                        noise_pred = unet(
                            latent_model_input,
                            t,
                            encoder_hidden_states=text_embeddings
                        ).sample
                    
                    # CFG计算（增强版）
                    noise_pred_uncond, noise_pred_text = noise_pred.chunk(2)
                    noise_pred = noise_pred_uncond + cfg_scale * (noise_pred_text - noise_pred_uncond)
                    
                    # 更新latent：使用混合后的current_latents而不是原始latents
                    # 这样模型的预测和更新才会基于相同的输入，确保提示词生效
                    new_latents = scheduler.step(noise_pred, t, current_latents).prev_sample
                    
                    # 模型输出后混合mask（核心逻辑）
                    if noise_mask is not None:
                        latents = noise_mask * new_latents + (1 - noise_mask) * original_samples.to(device, dtype)
                    else:
                        latents = new_latents
                    
                except Exception as e:
                    print(f"UNet推理失败: {e}")
                    continue
        
        print(f"\n采样完成！输出Latent设备: {latents.device}")
        
        # 构建结果字典
        result = {"samples": latents}
        if isinstance(original_latents, dict):
            for key, value in original_latents.items():
                if key != "samples":
                    result[key] = value
        
        return result
    
    except Exception as e:
        print(f"采样异常: {e}")
        traceback.print_exc()
        if isinstance(original_latents, dict):
            return original_latents
        return {"samples": latents}
