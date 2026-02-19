#input_quantity=0      # 输入端口数量
#variable_quantity=3    # 变量数量
#userinput=false          # 是否支持用户输入
#setting=true            # 是否支持设置
#output_quantity=1      # 输出端口数量
#time_late=0            # 延迟时间
#name=CLIP文本编码器加载模块  # 模块名称
#excitedbydata=true        # 是否可被数据激活
#variables_name=CLIP路径,CLIP类型,设备选择  # 变量名称
#kind=输入模块            # 模块类型
#output_name=CLIP模型

import os
import glob

"""
CLIP文本编码器加载模块
功能：加载千问定制CLIP编码器，输出CLIP模型对象
"""

class MockCLIP:
    """
    模拟CLIP模型对象
    实际项目中应替换为真实的CLIP模型加载逻辑
    """
    def __init__(self, clip_path, clip_type, device):
        self.clip_path = clip_path
        self.clip_type = clip_type
        self.device = device
        self.name = os.path.basename(clip_path) if clip_path else "default"
    
    def __repr__(self):
        return f"MockCLIP(model={self.name}, type={self.clip_type}, device={self.device})"

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
    :return: CLIP模型对象
    """
    # 默认设置
    default_settings = {
        "CLIP路径": "",
        "CLIP类型": "默认",
        "设备选择": "cuda"
    }
    
    # 合并设置
    if settings:
        default_settings.update(settings)
    
    # 获取设置值
    clip_path = default_settings.get("CLIP路径", "")
    clip_type = default_settings.get("CLIP类型", "默认")
    device = default_settings.get("设备选择", "cuda")
    
    print(f"CLIP加载参数: 路径={clip_path}, 类型={clip_type}, 设备={device}")
    
    try:
        # 扫描safetensors文件
        if not clip_path:
            safetensors_files = scan_safetensors_files()
            if safetensors_files:
                clip_path = safetensors_files[0]
                print(f"自动选择第一个safetensors文件: {clip_path}")
        
        # 模拟加载CLIP模型
        # 实际项目中应替换为真实的模型加载代码
        clip_model = MockCLIP(clip_path, clip_type, device)
        print(f"CLIP模型加载成功: {clip_model}")
        
        return clip_model
    except Exception as e:
        print(f"CLIP模型加载失败: {str(e)}")
        # 返回错误信息
        return f"加载失败: {str(e)}"

# 模块入口
if __name__ == "__main__":
    # 测试扫描功能
    print("测试扫描safetensors文件:")
    files = scan_safetensors_files()
    print(f"找到的文件: {files}")
    
    # 测试加载功能
    print("\n测试加载CLIP模型:")
    test_settings = {
        "CLIP路径": "test_clip.safetensors",
        "CLIP类型": "qwen_image",
        "设备选择": "cuda"
    }
    result = execute(test_settings)
    print(f"加载结果: {result}")
