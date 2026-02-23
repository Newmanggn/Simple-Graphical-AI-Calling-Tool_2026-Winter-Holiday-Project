#input_quantity=2
#variable_quantity=2
#userinput=false
#setting=true
#output_quantity=1
#time_late=0
#name=VAE解码模块
#excitedbydata=true
#variables_name=生成的Latent张量,VAE解码器
#kind=处理模块
#output_name=RGB图像

"""
VAE解码模块（重构版）
功能：加载VAE → 正确缩放Latent → 解码为RGB图像
输出：PIL图像对象
"""
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

import torch
from diffusers import StableDiffusionPipeline
from PIL import Image
import numpy as np
import os
import json
import re

_model_cache = {}

def get_device_from_engine_setting():
    """
    从gui_settings.json读取生成引擎设置，返回对应的PyTorch设备
    返回: (device_str, use_half_precision)
    """
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
    
    if engine == "CPU":
        return "cpu", False
    
    has_cuda = torch.cuda.is_available()
    
    gpu_idx = 0
    match = re.search(r'GPU\s+(\d+)', engine)
    if match:
        gpu_idx = int(match.group(1))
    
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
    
    return "cpu", False

def tensor_to_pil(tensor):
    """
    标准张量转PIL图像（无色彩偏差）
    """
    # 增加维度校验：确保是4维张量 [B,C,H,W]
    if len(tensor.shape) == 3:
        tensor = tensor.unsqueeze(0)
    # 标准反归一化流程（无偏差）
    tensor = (tensor / 2 + 0.5).clamp(0, 1)
    tensor = tensor.cpu().permute(0, 2, 3, 1).numpy()
    images = (tensor * 255).round().astype(np.uint8)  # round()避免浮点精度导致的偏色
    pil_images = [Image.fromarray(image) for image in images]
    return pil_images[0]

def execute(latents=None, vae_model_path=None):
    """
    执行模块逻辑
    """
    global _model_cache
    
    # 从字典中提取samples张量
    if isinstance(latents, dict) and "samples" in latents:
        latents = latents["samples"]
    
    print(f"VAE解码参数: latents形状={latents.shape if latents is not None else 'None'}, 模型路径={vae_model_path}")
    
    try:
        if latents is None or vae_model_path is None:
            print("错误: 缺少Latent张量或模型路径")
            return None
        
        # 1. 设备/精度配置（强制对齐）
        device, use_half = get_device_from_engine_setting()
        # 确定数据类型（CUDA用fp16，其他用fp32，VAE不支持bf16）
        if device.startswith("cuda") and use_half:
            dtype = torch.float16
        else:
            dtype = torch.float32
        print(f"使用设备: {device}, 数据类型: {dtype}")
        
        # 2. 加载VAE（强制精度/设备对齐）
        if vae_model_path not in _model_cache:
            print("开始加载VAE模型...")
            pipe = StableDiffusionPipeline.from_single_file(
                vae_model_path,
                torch_dtype=dtype,
                use_safetensors=True,
                safety_checker=None,
                requires_safety_checker=False  # 新增：避免安全检查器警告
            )
            # 强制VAE到指定设备和精度
            vae = pipe.vae.to(device=device, dtype=dtype)
            vae.eval()  # 强制进入评估模式（关键！避免训练模式的随机行为）
            _model_cache[vae_model_path] = vae
            del pipe  # 释放无关资源
            # 清空CUDA缓存，避免残留
            if device == "cuda":
                torch.cuda.empty_cache()
            print("VAE加载完成")
        
        vae = _model_cache[vae_model_path]
        
        # 3. Latent预处理（核心修正）
        # 扩展批次维度：如果是3维 [4,64,64] → 4维 [1,4,64,64]
        if len(latents.shape) == 3:
            latents = latents.unsqueeze(0)
        # 强制对齐设备和精度（CPU下禁用non_blocking）
        non_blocking = True if device == "cuda" else False
        latents = latents.to(device=device, dtype=dtype, non_blocking=non_blocking)
        # 标准缩放（必须！）- 解码时用除法还原像素空间
        latents = latents / vae.config.scaling_factor
        
        # 4. VAE解码（兼容CPU/GPU的autocast）
        autocast_enabled = device == "cuda"
        # 兼容新旧版PyTorch的autocast写法
        if hasattr(torch.amp, 'autocast'):
            autocast_ctx = torch.amp.autocast(device_type="cuda" if autocast_enabled else "cpu", enabled=autocast_enabled)
        else:
            autocast_ctx = torch.cuda.amp.autocast(enabled=autocast_enabled)
        
        with torch.no_grad(), autocast_ctx:
            image_tensor = vae.decode(latents, return_dict=False)[0]
        
        # 5. 转PIL图像（无色彩偏差）
        pil_image = tensor_to_pil(image_tensor)
        
        print(f"VAE解码完成: 图像尺寸={pil_image.size}")
        return pil_image
    
    except Exception as e:
        print(f"VAE解码失败: {str(e)}")
        import traceback
        traceback.print_exc()
        # 出错后清空缓存，避免下次加载异常
        if vae_model_path in _model_cache:
            del _model_cache[vae_model_path]
        if 'device' in locals() and device == "cuda":
            torch.cuda.empty_cache()
        return None

if __name__ == "__main__":
    print("测试VAE解码模块:")
    result = execute(None, None)
    print(f"解码结果: {result}")