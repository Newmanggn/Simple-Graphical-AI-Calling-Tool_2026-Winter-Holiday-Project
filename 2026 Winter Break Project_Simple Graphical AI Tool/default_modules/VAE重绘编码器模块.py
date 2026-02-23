#input_quantity=3
#variable_quantity=0
#userinput=false
#setting=false
#output_quantity=1
#time_late=0
#name=VAE重绘编码器模块
#excitedbydata=true
#variables_name=图像,vae,遮罩
#kind=处理模块
#output_name=Latent数据


"""
VAE重绘编码器模块
功能：将图像+遮罩一起编码为Latent张量
输入：VAE模型路径、PIL图像对象、PIL遮罩对象
输出：Latent张量（包含noise_mask）
"""

import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

import torch
from diffusers import StableDiffusionPipeline, AutoencoderKL
from PIL import Image
import numpy as np

_model_cache = {}

def get_device_from_engine_setting():
    """
    从gui_settings.json读取生成引擎设置，返回对应的PyTorch设备
    返回: (device_str, use_half_precision)
    """
    import os
    import json
    import torch
    
    settings_file = os.path.join(os.getcwd(), "gui_settings.json")
    default_engine = "CPU"
    use_cpu_for_vae = False
    
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                engine = settings.get("生成引擎", default_engine)
                use_cpu_for_vae = settings.get("使用 CPU 运行 VAE", False)
        except Exception as e:
            print(f"读取生成引擎设置失败: {e}")
            engine = default_engine
    else:
        engine = default_engine
    
    print(f"读取到的生成引擎设置: {engine}")
    print(f"读取到的使用 CPU 运行 VAE 设置: {use_cpu_for_vae}")
    
    # 如果启用使用 CPU 运行 VAE
    if use_cpu_for_vae:
        print("使用 CPU 运行 VAE 已启用，强制使用 CPU")
        return "cpu", False
    
    # 解析引擎设置
    if engine == "CPU":
        return "cpu", False
    
    # 检查是否有CUDA可用
    has_cuda = torch.cuda.is_available()
    
    # 尝试提取GPU索引
    import re
    gpu_idx = 0
    match = re.search(r'GPU\s+(\d+)', engine)
    if match:
        gpu_idx = int(match.group(1))
    
    # 处理不同类型的引擎
    if "CUDA" in engine:
        if has_cuda:
            if gpu_idx < torch.cuda.device_count():
                return f"cuda:{gpu_idx}", True
            return "cuda", True
        else:
            print("警告: 选择了CUDA引擎但CUDA不可用，回退到CPU")
            return "cpu", False
    elif "TensorRT" in engine:
        if has_cuda:
            print("注意: TensorRT引擎当前使用CUDA后端")
            if gpu_idx < torch.cuda.device_count():
                return f"cuda:{gpu_idx}", True
            return "cuda", True
        else:
            print("警告: 选择了TensorRT引擎但CUDA不可用，回退到CPU")
            return "cpu", False
    elif "DML" in engine:
        # DML (DirectML) - 检查是否有torch_directml可用
        try:
            import torch_directml
            has_dml = True
        except ImportError:
            has_dml = False
        
        if has_dml:
            print(f"使用DML后端，GPU索引: {gpu_idx}")
            return f"privateuseone:{gpu_idx}", False
        elif has_cuda:
            print("警告: DML不可用，回退到CUDA")
            if gpu_idx < torch.cuda.device_count():
                return f"cuda:{gpu_idx}", True
            return "cuda", True
        else:
            print("警告: 选择了DML引擎但DML和CUDA都不可用，回退到CPU")
            return "cpu", False
    elif "ZLUDA" in engine:
        if has_cuda:
            print("注意: ZLUDA引擎当前使用CUDA后端")
            if gpu_idx < torch.cuda.device_count():
                return f"cuda:{gpu_idx}", True
            return "cuda", True
        else:
            print("警告: 选择了ZLUDA引擎但CUDA不可用，回退到CPU")
            return "cpu", False
    
    # 默认回退
    return "cpu", False

def pil_to_tensor(pil_image):
    """
    PIL图像转PyTorch张量
    """
    if isinstance(pil_image, list):
        pil_image = pil_image[0]
    
    print(f"VAE编码输入: 图像尺寸={pil_image.size}")
    
    # 转换为numpy数组
    image_np = np.array(pil_image)
    
    # 如果是RGBA，转换为RGB
    if image_np.shape[-1] == 4:
        image_np = image_np[..., :3]
    
    # 归一化到[-1, 1]
    image_np = image_np.astype(np.float32) / 127.5 - 1.0
    
    # 转换为张量 [H, W, C] -> [C, H, W]
    image_tensor = torch.from_numpy(image_np).permute(2, 0, 1).unsqueeze(0)
    
    return image_tensor

def mask_to_latent_mask(pil_mask, latent_height, latent_width):
    """
    将PIL遮罩转换为Latent尺寸的遮罩张量
    用户涂掉的地方（黑色）应该是要被重绘的地方，所以需要反转遮罩值
    """
    if isinstance(pil_mask, list):
        pil_mask = pil_mask[0]
    
    print(f"遮罩处理: 原始尺寸={pil_mask.size}")
    
    # 转换为numpy数组
    mask_np = np.array(pil_mask)
    
    # 如果是3通道或4通道，取第一个通道或转灰度
    if len(mask_np.shape) == 3:
        mask_np = mask_np[..., 0]
    
    # 归一化到[0, 1]
    # 用户涂掉的地方（黑色，值低）应该是要重绘的地方（mask=1）
    # 用户没涂的地方（白色，值高）应该是要保留的地方（mask=0）
    mask_np = mask_np.astype(np.float32) / 255.0
    mask_np = 1.0 - mask_np  # 反转遮罩值，黑色（0）变为1表示重绘，白色（1）变为0表示保留
    
    # 转换为PIL并缩放到Latent尺寸
    mask_pil = Image.fromarray((mask_np * 255).astype(np.uint8))
    mask_pil = mask_pil.resize((latent_width, latent_height), Image.LANCZOS)  # 使用LANCZOS重采样获得更好效果
    
    # 转换回numpy数组
    mask_np_resized = np.array(mask_pil).astype(np.float32) / 255.0
    
    # 添加高斯模糊，避免边缘生硬
    from scipy.ndimage import gaussian_filter
    mask_np_blurred = gaussian_filter(mask_np_resized, sigma=1.0)  # 模糊半径1.0
    
    # 确保mask值在0-1范围内
    mask_np_blurred = np.clip(mask_np_blurred, 0.0, 1.0)
    
    # 转换为张量并扩展为4通道：[1, 1, H, W] → [1, 4, H, W]
    mask_tensor = torch.from_numpy(mask_np_blurred).unsqueeze(0).unsqueeze(0)
    mask_tensor = mask_tensor.repeat(1, 4, 1, 1)  # 关键：复制到4通道
    
    print(f"遮罩处理完成: Latent尺寸={mask_tensor.shape}")
    return mask_tensor

def execute(image=None, vae_model_path=None, mask=None):
    """
    执行模块逻辑
    :param image: PIL图像对象或PIL图像列表
    :param vae_model_path: VAE模型路径
    :param mask: PIL遮罩对象或PIL遮罩列表
    :return: Latent字典 {"samples": latents, "noise_mask": mask_tensor}
    """
    global _model_cache
    
    print(f"VAE重绘编码参数: 图像类型={type(image)}, 模型路径={vae_model_path}, 遮罩类型={type(mask)}")
    
    try:
        if vae_model_path is None or image is None:
            print("错误: 缺少VAE模型路径或图像")
            return {"samples": None, "noise_mask": None}
        
        # 1. 设备/精度配置
        device, use_half = get_device_from_engine_setting()
        # 确定数据类型（CUDA用fp16，其他用fp32，VAE不支持bf16）
        if device.startswith("cuda") and use_half:
            dtype = torch.float16
        else:
            dtype = torch.float32
        print(f"使用设备: {device}, 数据类型: {dtype}")
        
        # 2. 加载VAE
        if vae_model_path not in _model_cache:
            print("开始加载VAE模型...")
            try:
                # 直接使用AutoencoderKL加载VAE，不通过StableDiffusionPipeline
                vae = AutoencoderKL.from_single_file(
                    vae_model_path,
                    torch_dtype=dtype,
                    use_safetensors=True,
                    local_files_only=True
                )
                print("通过AutoencoderKL加载VAE成功")
            except Exception as e:
                print(f"AutoencoderKL加载失败，尝试通过StableDiffusionPipeline加载: {e}")
                # 备用方案：通过StableDiffusionPipeline加载
                pipe = StableDiffusionPipeline.from_single_file(
                    vae_model_path,
                    torch_dtype=dtype,
                    use_safetensors=True,
                    safety_checker=None,
                    requires_safety_checker=False,
                    local_files_only=True
                )
                vae = pipe.vae
                # 关键：清理不需要的组件，释放大量内存！
                del pipe.text_encoder
                del pipe.unet
                del pipe.tokenizer
                del pipe.scheduler
                del pipe.feature_extractor
                del pipe.image_processor
                del pipe
                print("通过StableDiffusionPipeline加载VAE成功")
            
            vae = vae.to(device=device, dtype=dtype)
            vae.eval()
            
            # 强制释放内存
            import gc
            gc.collect()
            
            if device.startswith("cuda"):
                torch.cuda.empty_cache()
            
            _model_cache[vae_model_path] = vae
            print("VAE加载完成")
        
        vae = _model_cache[vae_model_path]
        
        # 3. 图像预处理
        image_tensor = pil_to_tensor(image)
        image_tensor = image_tensor.to(device=device, dtype=dtype)
        
        # 4. VAE编码
        autocast_enabled = device.startswith("cuda")
        if hasattr(torch.amp, 'autocast'):
            if device.startswith("privateuseone"):
                autocast_ctx = torch.amp.autocast(device_type="cpu", enabled=False)
            else:
                autocast_ctx = torch.amp.autocast(device_type="cuda" if autocast_enabled else "cpu", enabled=autocast_enabled)
        else:
            autocast_ctx = torch.cuda.amp.autocast(enabled=autocast_enabled)
        
        with torch.no_grad(), autocast_ctx:
            latents = vae.encode(image_tensor).latent_dist.sample()
            latents = latents * vae.config.scaling_factor
        
        # 5. 处理遮罩
        noise_mask = None
        if mask is not None:
            latent_height = latents.shape[2]
            latent_width = latents.shape[3]
            noise_mask = mask_to_latent_mask(mask, latent_height, latent_width)
            noise_mask = noise_mask.to(device=device, dtype=dtype)
        
        # 返回字典格式
        result = {
            "samples": latents,
            "noise_mask": noise_mask
        }
        
        print(f"VAE重绘编码完成: Latent形状={latents.shape}, 有遮罩={mask is not None}")
        return result
    
    except Exception as e:
        print(f"VAE重绘编码失败: {str(e)}")
        import traceback
        traceback.print_exc()
        if vae_model_path in _model_cache:
            del _model_cache[vae_model_path]
        if 'device' in locals() and device.startswith("cuda"):
            torch.cuda.empty_cache()
        return {"samples": None, "noise_mask": None}

if __name__ == "__main__":
    print("测试VAE重绘编码器模块:")
    result = execute(None, None, None)
    print(f"编码结果: {result}")
