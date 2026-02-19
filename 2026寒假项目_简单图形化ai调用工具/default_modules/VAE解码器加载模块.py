#input_quantity=0
#variable_quantity=2
#userinput=false
#setting=true
#output_quantity=1
#time_late=0
#name=VAE解码器加载模块
#excitedbydata=true
#variables_name=VAE路径,解码精度
#kind=输入模块
#output_name=VAE解码器

import os
import glob

"""
VAE解码器加载模块
功能：加载千问定制VAE模型，输出VAE解码器对象
"""

class MockVAE:
    """
    模拟VAE模型对象
    实际项目中应替换为真实的VAE模型加载逻辑
    """
    def __init__(self, vae_path, decode_precision):
        self.vae_path = vae_path
        self.decode_precision = decode_precision
        self.name = os.path.basename(vae_path) if vae_path else "default"
    
    def __repr__(self):
        return f"MockVAE(model={self.name}, precision={self.decode_precision})"

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
    :return: VAE解码器对象
    """
    # 默认设置
    default_settings = {
        "VAE路径": "",
        "解码精度": "fp16"
    }
    
    # 合并设置
    if settings:
        default_settings.update(settings)
    
    # 获取设置值
    vae_path = default_settings.get("VAE路径", "")
    decode_precision = default_settings.get("解码精度", "fp16")
    
    print(f"VAE加载参数: 路径={vae_path}, 解码精度={decode_precision}")
    
    try:
        # 扫描safetensors文件
        if not vae_path:
            safetensors_files = scan_safetensors_files()
            if safetensors_files:
                vae_path = safetensors_files[0]
                print(f"自动选择第一个safetensors文件: {vae_path}")
        
        # 模拟加载VAE模型
        # 实际项目中应替换为真实的模型加载代码
        vae_model = MockVAE(vae_path, decode_precision)
        print(f"VAE模型加载成功: {vae_model}")
        
        return vae_model
    except Exception as e:
        print(f"VAE模型加载失败: {str(e)}")
        # 返回错误信息
        return f"加载失败: {str(e)}"

# 模块入口
if __name__ == "__main__":
    # 测试扫描功能
    print("测试扫描safetensors文件:")
    files = scan_safetensors_files()
    print(f"找到的文件: {files}")
    
    # 测试加载功能
    print("\n测试加载VAE模型:")
    test_settings = {
        "VAE路径": "test_vae.safetensors",
        "解码精度": "fp8"
    }
    result = execute(test_settings)
    print(f"加载结果: {result}")
