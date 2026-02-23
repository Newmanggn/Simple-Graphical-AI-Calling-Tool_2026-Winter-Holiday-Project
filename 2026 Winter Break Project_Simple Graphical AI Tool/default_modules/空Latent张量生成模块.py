#input_quantity=0
#variable_quantity=4
#userinput=false
#setting=true
#output_quantity=1
#time_late=0
#name=空Latent张量生成模块
#excitedbydata=true
#variables_name=宽度,高度,批量大小,种子
#kind=处理模块
#output_name=空Latent张量

"""
空Latent张量生成模块
功能：按尺寸生成噪声 latent
输出：真实的PyTorch噪声张量
"""

import torch

def get_device_from_engine_setting():
    """
    从gui_settings.json读取生成引擎设置，返回对应的PyTorch设备
    返回: (device_str, use_half_precision)
    """
    import os
    import json
    
    settings_file = os.path.join(os.getcwd(), "gui_settings.json")
    default_engine = "CPU"
    
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                engine = settings.get("生成引擎", default_engine)
        except Exception as e:
            print(f"读取生成引擎设置失败: {e}")
            engine = default_engine
    else:
        engine = default_engine
    
    print(f"读取到的生成引擎设置: {engine}")
    
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

def execute(width=None, height=None, batch_size=None, seed=None):
    """
    执行模块逻辑
    :param width: 宽度
    :param height: 高度
    :param batch_size: 批量大小
    :param seed: 随机种子 (-1表示随机)
    :return: Latent噪声张量
    """
    if width is None or width == '':
        width = 512
    if height is None or height == '':
        height = 512
    if batch_size is None or batch_size == '':
        batch_size = 1
    if seed is None or seed == '':
        seed = -1
    width = int(width)
    height = int(height)
    batch_size = int(batch_size)
    seed = int(seed)
    
    print(f"空Latent张量参数: 宽度={width}, 高度={height}, 批量大小={batch_size}, 种子={seed}")
    
    try:
        if width <= 0 or height <= 0 or batch_size <= 0:
            raise ValueError("宽度、高度和批量大小必须为正数")
        
        # 从设置中获取设备
        device, use_half = get_device_from_engine_setting()
        print(f"使用设备: {device}")
        
        latent_width = width // 8
        latent_height = height // 8
        
        if device.startswith("cuda") or device.startswith("privateuseone"):
            dtype = torch.float16
        else:
            dtype = torch.float32
        
        # 种子为-1时随机生成，不为-1时使用固定种子
        if seed != -1:
            # 注意：privateuseone设备可能不支持Generator，回退到CPU
            try:
                generator = torch.Generator(device=device).manual_seed(seed)
                latents = torch.randn(
                    (batch_size, 4, latent_height, latent_width),
                    device=device,
                    dtype=dtype,
                    generator=generator
                )
            except:
                generator = torch.Generator(device="cpu").manual_seed(seed)
                latents = torch.randn(
                    (batch_size, 4, latent_height, latent_width),
                    device="cpu",
                    dtype=dtype,
                    generator=generator
                ).to(device=device)
        else:
            # 种子为-1，完全随机
            latents = torch.randn(
                (batch_size, 4, latent_height, latent_width),
                device=device,
                dtype=dtype
            )
        
        print(f"空Latent张量生成完成: 形状={latents.shape}, 设备={device}")
        
        return {"samples": latents}
    except Exception as e:
        print(f"空Latent张量生成失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("测试空Latent张量生成:")
    result = execute(512, 512, 4)
    if result is not None:
        print(f"生成结果形状: {result.shape}")
    else:
        print("生成失败")
