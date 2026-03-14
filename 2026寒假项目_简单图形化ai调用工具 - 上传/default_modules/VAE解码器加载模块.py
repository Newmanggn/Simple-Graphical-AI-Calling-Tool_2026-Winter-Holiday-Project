#input_quantity=0
#variable_quantity=2
#userinput=false
#setting=true
#output_quantity=1
#time_late=0
#name=VAE解码器加载模块
#excitedbydata=true
#variables_name=模型文件夹路径,模型文件选择
#kind=加载器
#output_name=VAE解码器路径

import os
import glob

def scan_model_files(directory="."):
    try:
        model_files = []
        
        vae_dir = os.path.join(directory, "vae")
        if os.path.exists(vae_dir):
            patterns = [
                os.path.join(vae_dir, "*.safetensors"),
                os.path.join(vae_dir, "*.ckpt"),
                os.path.join(vae_dir, "*.bin")
            ]
            for pattern in patterns:
                files = glob.glob(pattern)
                model_files.extend(files)
        
        if not model_files:
            patterns = [
                os.path.join(directory, "**", "*.safetensors"),
                os.path.join(directory, "**", "*.ckpt"),
                os.path.join(directory, "**", "*.bin")
            ]
            for pattern in patterns:
                files = glob.glob(pattern, recursive=True)
                model_files.extend(files)
        
        return model_files
    except Exception as e:
        print(f"扫描VAE模型文件失败: {str(e)}")
        return []

def execute(model_folder=None, selected_model=None):
    """
    执行模块逻辑
    :return: vae_path - VAE模型文件路径字符串
    """
    default_model_path = os.path.join(os.getcwd(), "models")
    settings_file = os.path.join(os.getcwd(), "gui_settings.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                import json
                gui_settings = json.load(f)
                if "模型文件夹路径" in gui_settings:
                    default_model_path = gui_settings["模型文件夹路径"]
        except Exception as e:
            print(f"加载GUI设置失败: {e}")
    
    if model_folder is None or not model_folder:
        model_folder = default_model_path
    if selected_model is None:
        selected_model = ""
    
    model_path = selected_model if selected_model else ""
    
    print(f"VAE解码器加载器: 文件夹={model_folder}, 模型={model_path}")
    
    try:
        if not model_path:
            model_files = scan_model_files(model_folder)
            if model_files:
                model_path = model_files[0]
                print(f"自动选择VAE模型: {model_path}")
        
        print(f"VAE解码器加载器完成: 只传路径={model_path}")
        
        model_path = os.path.normpath(model_path)
        
        return model_path
    except Exception as e:
        print(f"VAE解码器加载失败: {str(e)}")
        return f"加载失败: {str(e)}"

if __name__ == "__main__":
    print("测试VAE解码器加载器:")
    result = execute()
    print(f"结果: {result}")

"""
VAE解码器加载模块

功能：
- 纯指路牌，只传VAE模型文件路径，不加载不运算
- 自动扫描指定文件夹中的VAE模型文件
- 从GUI设置中读取默认模型路径

使用场景：
- 作为VAE解码模块的输入，提供模型路径
- 在需要VAE模型的工作流中使用

输入：
- 模型文件夹路径：VAE模型所在的文件夹
- 模型文件选择：具体的VAE模型文件路径

输出：
- VAE解码器路径：选中的VAE模型文件路径字符串

端口详细说明：
- 输入端口：0个（无输入）
- 输出端口：1个
  - 端口0: VAE解码器路径（VAE模型路径）
"""
