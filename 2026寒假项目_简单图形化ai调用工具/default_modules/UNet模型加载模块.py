#input_quantity=0      # 输入端口数量
#variable_quantity=3    # 变量数量
#userinput=false          # 是否支持用户输入
#setting=true            # 是否支持设置
#output_quantity=1      # 输出端口数量
#time_late=0            # 延迟时间
#name=UNet模型加载模块    # 模块名称
#excitedbydata=true        # 是否可被数据激活
#variables_name=权重路径,数据类型,加载设备  # 变量名称
#kind=输入模块            # 模块类型
#output_name=UNet模型

import os
import glob

"""
UNet模型加载模块
功能：加载UNet扩散模型，输出UNet模型对象，适配千问定制的fp8量化权重
"""

class MockUNet:
    """
    模拟UNet模型对象
    实际项目中应替换为真实的UNet模型加载逻辑
    """
    def __init__(self, model_path, dtype, device):
        self.model_path = model_path
        self.dtype = dtype
        self.device = device
        self.name = os.path.basename(model_path) if model_path else "default"
    
    def __repr__(self):
        return f"MockUNet(model={self.name}, dtype={self.dtype}, device={self.device})"

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

def execute(settings=None):
    """
    执行模块逻辑
    :param settings: 设置参数
    :return: UNet模型对象
    """
    # 默认设置
    default_settings = {
        "权重路径": "",
        "数据类型": "default",
        "加载设备": "cuda"
    }
    
    # 合并设置
    if settings:
        default_settings.update(settings)
    
    # 获取设置值
    model_path = default_settings.get("权重路径", "")
    dtype = default_settings.get("数据类型", "default")
    device = default_settings.get("加载设备", "cuda")
    
    print(f"UNet模型加载参数: 路径={model_path}, 数据类型={dtype}, 设备={device}")
    
    try:
        # 扫描safetensors文件
        if not model_path:
            safetensors_files = scan_safetensors_files()
            if safetensors_files:
                model_path = safetensors_files[0]
                print(f"自动选择第一个safetensors文件: {model_path}")
        
        # 模拟加载UNet模型
        # 实际项目中应替换为真实的模型加载代码
        unet_model = MockUNet(model_path, dtype, device)
        print(f"UNet模型加载成功: {unet_model}")
        
        return unet_model
    except Exception as e:
        print(f"UNet模型加载失败: {str(e)}")
        # 返回错误信息
        return f"加载失败: {str(e)}"

# 模块入口
if __name__ == "__main__":
    # 测试扫描功能
    print("测试扫描safetensors文件:")
    files = scan_safetensors_files()
    print(f"找到的文件: {files}")
    
    # 测试加载功能
    print("\n测试加载UNet模型:")
    test_settings = {
        "权重路径": "test_unet.safetensors",
        "数据类型": "fp16",
        "加载设备": "cuda"
    }
    result = execute(test_settings)
    print(f"加载结果: {result}")
