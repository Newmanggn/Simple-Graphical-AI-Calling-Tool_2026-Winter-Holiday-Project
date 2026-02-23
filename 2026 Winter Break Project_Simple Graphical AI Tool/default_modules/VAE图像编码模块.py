#input_quantity=2
#variable_quantity=2
#userinput=false
#setting=false
#output_quantity=1
#time_late=0
#name=VAE图像编码模块
#excitedbydata=true
#variables_name=vae,图像
#kind=处理模块
#output_name=Latent数据

"""
VAE图像编码模块（极致优化版）
功能：将图像编码为Latent张量
输入：VAE模型路径、PIL图像对象
输出：Latent张量
优化：
1. 完全禁用缓存，每次重新加载VAE后立即清理
2. 只加载VAE组件，不加载完整pipeline
3. 及时清理中间张量，强制垃圾回收
4. 使用 AutoencoderKL 直接加载 VAE，不通过 StableDiffusionPipeline
"""

import os
import re
import gc
import json
import traceback
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

import torch
from diffusers import AutoencoderKL
from PIL import Image
import numpy as np

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

def pil_to_tensor(pil_image):
    """
    PIL图像转PyTorch张量（内存优化版）
    """
    if isinstance(pil_image, list):
        if not pil_image:
            raise ValueError("图像列表为空")
        pil_image = pil_image[0]
    
    if not isinstance(pil_image, Image.Image):
        raise TypeError(f"期望PIL.Image对象，实际得到: {type(pil_image)}")
    
    print(f"VAE编码输入: 图像尺寸={pil_image.size}, 模式={pil_image.mode}")
    
    # 转换为numpy数组（处理灰度/透明图）
    image_np = np.array(pil_image)
    if image_np.ndim == 2:  # 灰度图转RGB
        image_np = np.expand_dims(image_np, axis=-1)
        image_np = np.repeat(image_np, 3, axis=-1)
    elif image_np.shape[-1] == 4:  # RGBA转RGB
        image_np = image_np[..., :3]
    
    # 归一化到[-1, 1]（SD标准）
    image_np = image_np.astype(np.float32) / 127.5 - 1.0
    
    # 转换为张量 [1, 3, H, W]
    image_tensor = torch.from_numpy(image_np).permute(2, 0, 1).unsqueeze(0)
    
    return image_tensor

def force_cleanup():
    """强制清理内存"""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()

def execute(vae_model_path=None, image=None):
    """
    执行模块逻辑（极致内存优化版）
    :param vae_model_path: VAE模型路径
    :param image: PIL图像对象或PIL图像列表
    :return: Latent张量 [1,4,H/8,W/8]
    """
    print(f"\n=== VAE编码开始（优化版） ===")
    print(f"模型路径: {vae_model_path if vae_model_path else '空'}")
    print(f"图像类型: {type(image)}")
    
    # 初始清理
    force_cleanup()
    
    # 初始化变量
    vae = None
    image_tensor = None
    latents = None
    result = None
    
    try:
        # 必要参数校验
        if vae_model_path is None or not os.path.exists(vae_model_path):
            raise ValueError(f"VAE模型路径无效或不存在: {vae_model_path}")
        if image is None:
            raise ValueError("输入图像为空")
        
        # 获取设备和精度配置
        device, use_half = get_device_from_engine_setting()
        # 确定数据类型（CUDA用fp16，其他用fp32，VAE不支持bf16）
        if device.startswith("cuda") and use_half:
            dtype = torch.float16
        else:
            dtype = torch.float32
        print(f"使用设备: {device}, 数据类型: {dtype}")
        
        # 加载VAE模型（仅加载核心组件）
        print("加载VAE模型（仅加载VAE组件）...")
        try:
            vae = AutoencoderKL.from_single_file(
                vae_model_path,
                torch_dtype=dtype,
                use_safetensors=True,
                local_files_only=True  # 优先本地文件，避免下载
            )
        except Exception as e:
            print(f"AutoencoderKL加载失败，尝试通过StableDiffusionPipeline加载: {e}")
            from diffusers import StableDiffusionPipeline
            pipe = StableDiffusionPipeline.from_single_file(
                vae_model_path,
                torch_dtype=dtype,
                use_safetensors=True,
                safety_checker=None,
                requires_safety_checker=False,
                local_files_only=True
            )
            vae = pipe.vae
            del pipe  # 立即清理pipe，释放显存
            force_cleanup()
        
        # 移到指定设备并设置为评估模式
        vae = vae.to(device=device, dtype=dtype).eval()
        print("VAE加载完成")
        
        # 图像转张量并移到设备
        image_tensor = pil_to_tensor(image)
        image_tensor = image_tensor.to(device=device, dtype=dtype, non_blocking=device.startswith("cuda"))
        
        # 核心编码逻辑（修复autocast错误）
        print("开始编码...")
        with torch.no_grad():
            # 正确的autocast用法：只指定device_type，不指定dtype
            if device.startswith("cuda") and use_half:
                autocast_ctx = torch.amp.autocast(device_type="cuda", enabled=True)
            else:
                autocast_ctx = torch.no_grad()  # 非CUDA/不使用半精度时，直接用no_grad
            
            with autocast_ctx:
                # VAE编码：生成Latent分布并采样
                latent_dist = vae.encode(image_tensor).latent_dist
                latents = latent_dist.sample()
                
                # 关键：乘以scaling_factor（SD1.x=0.18215，SD2.x=0.13025）
                latents = latents * vae.config.scaling_factor
        
        # 校验Latent数值范围（关键调试信息）
        print(f"VAE编码完成:")
        print(f"  - Latent形状: {latents.shape}")
        print(f"  - 缩放系数: {vae.config.scaling_factor}")
        print(f"  - 数值范围: min={latents.min().item():.4f}, max={latents.max().item():.4f}")  # 正常范围±1左右
        print(f"=== VAE编码结束 ===\n")
        
        # 先克隆到CPU再清理（避免显存丢失）
        result = {"samples": latents.detach().cpu().clone()}
        
    except Exception as e:
        error_msg = f"VAE编码失败: {str(e)}"
        print(error_msg)
        traceback.print_exc()
    finally:
        # 强制清理所有临时变量（无论是否异常）
        for var_name in ['vae', 'image_tensor', 'latents']:
            if var_name in locals():
                del locals()[var_name]
        force_cleanup()
    
    return result

if __name__ == "__main__":
    print("测试VAE图像编码模块（优化版）:")
    # 构造测试图像
    test_image = Image.new('RGB', (512, 512), color='blue')
    # 替换为你的VAE模型路径
    test_vae_path = "./models/vae.safetensors"
    
    # 执行测试
    result = execute(test_vae_path, test_image)
    print(f"测试结果: {result.shape if result is not None else '失败'}")