#input_quantity=2
#variable_quantity=2
#userinput=false
#setting=true
#output_quantity=1
#time_late=0
#name=CLIP文本编码模块
#excitedbydata=true
#variables_name=CLIP模型,提示词
#kind=模型条件
#output_name=文本向量

"""
CLIP文本编码模块
功能：拿路径 → 加载自己需要的权重 → 编码提示词
输出：正面+负面文本embedding张量
"""

import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

import torch
from diffusers import StableDiffusionPipeline

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

def execute(clip_model_path=None, prompt=None):
    """
    执行模块逻辑
    :param clip_model_path: CLIP模型路径（来自Checkpoint加载器的输出）
    :param prompt: 提示词
    :return: 文本向量
    """
    global _model_cache
    
    default_prompt = "a beautiful cat"
    
    if prompt is None:
        prompt = default_prompt
    
    print(f"CLIP文本编码参数: 模型路径='{clip_model_path}', 提示词='{prompt}'")
    
    try:
        if not clip_model_path:
            print("错误: 未提供模型路径")
            return None
        
        # 从设置中获取设备
        device, use_half = get_device_from_engine_setting()
        print(f"使用设备: {device}")
        
        pipe = None
        if clip_model_path in _model_cache:
            print("使用缓存的模型")
            pipe = _model_cache[clip_model_path]
        
        if pipe is None:
            print("开始加载模型...")
            # 根据设备选择精度
            if device.startswith("cuda") or device.startswith("privateuseone"):
                torch_dtype = torch.float16
            else:
                torch_dtype = torch.float32
            pipe = StableDiffusionPipeline.from_single_file(
                clip_model_path,
                torch_dtype=torch_dtype,
                use_safetensors=True
            )
            pipe = pipe.to(device)
            _model_cache[clip_model_path] = pipe
            print("模型加载完成")
        
        print("开始编码提示词...")
        positive_embeds, negative_embeds = pipe.encode_prompt(
            prompt=prompt,
            device=device,
            num_images_per_prompt=1,
            do_classifier_free_guidance=True
        )
        
        print(f"CLIP文本编码完成: 形状={positive_embeds.shape}")
        
        return positive_embeds
    except Exception as e:
        print(f"CLIP文本编码失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"CLIP编码错误: {str(e)}"

if __name__ == "__main__":
    print("测试CLIP文本编码模块:")
    result = execute(None, "a beautiful cat")
    print(f"编码结果: {result}")
