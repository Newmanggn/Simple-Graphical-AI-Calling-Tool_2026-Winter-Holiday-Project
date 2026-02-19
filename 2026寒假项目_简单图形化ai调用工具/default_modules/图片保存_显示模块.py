#input_quantity=1
#variable_quantity=4
#userinput=false
#setting=true
#output_quantity=0
#time_late=0
#name=图片保存/显示模块
#excitedbydata=true
#variables_name=RGB图像张量
#kind=输出模块

import os
import time

"""
图片保存/显示模块
功能：接收VAE解码后的图像张量，保存到本地并在工具界面显示
"""

def execute(rgb_image, settings=None, cancel_token=None):
    """
    执行模块逻辑
    :param rgb_image: RGB图像张量对象
    :param settings: 设置参数
    :param cancel_token: 取消令牌
    :return: None（输出模块无返回值）
    """
    # 默认设置
    default_settings = {
        "文件名前缀": "Qwen-image-2512",
        "保存格式": "PNG",
        "保存路径": "auto_save",
        "显示尺寸": "原图"
    }
    
    # 合并设置
    if settings:
        default_settings.update(settings)
    
    # 获取设置值
    file_prefix = default_settings.get("文件名前缀", "Qwen-image-2512")
    save_format = default_settings.get("保存格式", "PNG")
    save_path = default_settings.get("保存路径", "auto_save")
    display_size = default_settings.get("显示尺寸", "原图")
    
    print(f"图片保存/显示参数: 前缀='{file_prefix}', 格式={save_format}, 路径={save_path}, 显示尺寸={display_size}")
    
    try:
        # 检查取消令牌
        if cancel_token and cancel_token():
            raise Exception("保存已取消")
        
        # 确保保存路径存在
        if not os.path.exists(save_path):
            os.makedirs(save_path)
            print(f"创建保存路径: {save_path}")
        
        # 生成文件名
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{file_prefix}_{timestamp}.{save_format.lower()}"
        file_path = os.path.join(save_path, filename)
        
        # 模拟保存图片
        # 实际项目中应替换为真实的图片保存代码
        print(f"保存图片到: {file_path}")
        print(f"图片信息: {rgb_image}")
        print(f"显示尺寸设置: {display_size}")
        
        # 模拟图片保存成功
        print(f"图片保存成功: {filename}")
        
        # 输出模块无返回值
        return None
    except Exception as e:
        print(f"图片保存/显示失败: {str(e)}")
        # 返回错误信息
        return f"操作失败: {str(e)}"

# 模块入口
if __name__ == "__main__":
    # 模拟RGB图像对象
    class MockRGBImage:
        def __init__(self):
            self.width = 928
            self.height = 1664
        def __repr__(self):
            return "MockRGBImage(width=928, height=1664)"
    
    # 测试保存功能
    print("测试图片保存/显示模块:")
    test_image = MockRGBImage()
    test_settings = {
        "文件名前缀": "Qwen-image-2512",
        "保存格式": "PNG",
        "保存路径": "auto_save",
        "显示尺寸": "原图"
    }
    result = execute(test_image, test_settings)
    print(f"执行结果: {result}")
