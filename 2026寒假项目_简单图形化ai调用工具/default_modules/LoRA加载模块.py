#input_quantity=1
#variable_quantity=3
#userinput=false
#setting=true
#output_quantity=1
#time_late=0
#name=LoRA加载模块
#excitedbydata=true
#variables_name=UNet模型,LoRA路径,LoRA强度,仅注入UNet
#kind=输入模块
#output_name=带LoRA的UNet模型

import os
import glob

"""
LoRA加载模块
功能：加载Lightning-4steps LoRA权重，注入到UNet模型中，输出带LoRA的UNet对象
"""

class MockLoRA:
    """
    模拟LoRA对象
    实际项目中应替换为真实的LoRA加载逻辑
    """
    def __init__(self, lora_path, strength):
        self.lora_path = lora_path
        self.strength = strength
        self.name = os.path.basename(lora_path) if lora_path else "default"
    
    def __repr__(self):
        return f"MockLoRA(name={self.name}, strength={self.strength})"

class MockUNetWithLoRA:
    """
    模拟带LoRA的UNet模型对象
    实际项目中应替换为真实的UNet+LoRA逻辑
    """
    def __init__(self, unet_model, lora_model, only_unet=True):
        self.unet_model = unet_model
        self.lora_model = lora_model
        self.only_unet = only_unet
    
    def __repr__(self):
        return f"MockUNetWithLoRA(unet={self.unet_model}, lora={self.lora_model}, only_unet={self.only_unet})"

def scan_safetensors_files(directory="."):
    """
    扫描本地safetensors文件
    :param directory: 扫描目录
    :return: safetensors文件路径列表
    """
    try:
        # 搜索当前目录及子目录的safetensors文件
        pattern = os.path.join(directory, "**", "*.safetensors")
        files = glob.glob(pattern, recursive=True)
        return files
    except Exception as e:
        print(f"扫描safetensors文件失败: {str(e)}")
        return []

def execute(unet_model, settings=None):
    """
    执行模块逻辑
    :param unet_model: UNet模型对象
    :param settings: 设置参数
    :return: 带LoRA的UNet模型对象
    """
    # 默认设置
    default_settings = {
        "LoRA路径": "",
        "LoRA强度": 1.0,
        "仅注入UNet": True
    }
    
    # 合并设置
    if settings:
        default_settings.update(settings)
    
    # 获取设置值
    lora_path = default_settings.get("LoRA路径", "")
    lora_strength = float(default_settings.get("LoRA强度", 1.0))
    only_unet = bool(default_settings.get("仅注入UNet", True))
    
    print(f"LoRA加载参数: 路径={lora_path}, 强度={lora_strength}, 仅注入UNet={only_unet}")
    
    try:
        # 扫描safetensors文件
        if not lora_path:
            safetensors_files = scan_safetensors_files()
            if safetensors_files:
                lora_path = safetensors_files[0]
                print(f"自动选择第一个safetensors文件: {lora_path}")
        
        # 模拟加载LoRA
        # 实际项目中应替换为真实的LoRA加载代码
        lora_model = MockLoRA(lora_path, lora_strength)
        print(f"LoRA加载成功: {lora_model}")
        
        # 模拟注入LoRA到UNet
        # 实际项目中应替换为真实的LoRA注入代码
        unet_with_lora = MockUNetWithLoRA(unet_model, lora_model, only_unet)
        print(f"LoRA注入成功: {unet_with_lora}")
        
        return unet_with_lora
    except Exception as e:
        print(f"LoRA加载失败: {str(e)}")
        # 返回错误信息
        return f"加载失败: {str(e)}"

# 模块入口
if __name__ == "__main__":
    # 测试扫描功能
    print("测试扫描safetensors文件:")
    files = scan_safetensors_files()
    print(f"找到的文件: {files}")
    
    # 模拟UNet模型
    class MockUNet:
        def __repr__(self):
            return "MockUNet()"
    
    # 测试加载功能
    print("\n测试加载LoRA:")
    test_unet = MockUNet()
    test_settings = {
        "LoRA路径": "test_lora.safetensors",
        "LoRA强度": 1.0,
        "仅注入UNet": True
    }
    result = execute(test_unet, test_settings)
    print(f"加载结果: {result}")
