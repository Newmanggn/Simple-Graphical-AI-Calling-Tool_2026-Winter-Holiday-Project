#input_quantity=1
#variable_quantity=3
#userinput=false
#setting=true
#output_quantity=0
#time_late=0
#name=图片保存/显示模块
#excitedbydata=true
#variables_name=RGB图像,保存路径,是否保存
#kind=输出模块
#showingwindow_quantity=1

import os
import time
import json

"""
图片保存/显示模块
功能：纯 IO，不参与生成，只显示和写入文件
"""

def execute(image=None, save_path=None, should_save=True):
    """
    执行模块逻辑
    :param image: PIL图像对象或图像列表
    :param save_path: 保存路径
    :param should_save: 是否保存（默认True）
    :return: 保存结果信息
    """
    fallback_save_path = os.path.join(os.getcwd(), "output")
    settings_file = os.path.join(os.getcwd(), "gui_settings.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                gui_settings = json.load(f)
                if "默认图片保存路径" in gui_settings:
                    default_save_path = gui_settings["默认图片保存路径"]
                    if save_path is None or not save_path:
                        save_path = default_save_path
        except Exception as e:
            print(f"加载GUI设置失败: {e}")
    
    if save_path is None or not save_path:
        save_path = fallback_save_path
    
    # 处理should_save参数，确保是布尔值
    if isinstance(should_save, str):
        should_save = should_save.lower() in ('true', '1', 'yes', 'on')
    
    print(f"图片保存参数: 路径={save_path}, 是否保存={should_save}")
    print(f"输入图像类型: {type(image)}, 值: {image}")
    
    try:
        if image is None:
            print("错误: 未提供图像")
            return f"操作失败: 未提供图像"
        
        from PIL import Image
        
        # 处理批量图像
        images_to_save = []
        if isinstance(image, list):
            images_to_save = image
        elif isinstance(image, Image.Image):
            images_to_save = [image]
        else:
            print(f"错误: 图像类型不正确，类型={type(image)}")
            return f"操作失败: 图像类型不正确"
        
        if len(images_to_save) == 0:
            print("错误: 没有图像可保存")
            return f"操作失败: 没有图像可保存"
        
        saved_paths = []
        if should_save:
            tried_paths = []
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            # 确保保存路径存在
            for current_path in [save_path, fallback_save_path]:
                try:
                    if not os.path.exists(current_path):
                        try:
                            os.makedirs(current_path)
                            print(f"创建保存路径: {current_path}")
                        except Exception as e:
                            print(f"创建路径失败: {e}")
                            tried_paths.append(f"{current_path} (创建失败)")
                            continue
                    
                    # 保存所有图像
                    for idx, img in enumerate(images_to_save):
                        if len(images_to_save) == 1:
                            filename = f"{timestamp}.png"
                        else:
                            filename = f"{timestamp}_{idx+1}.png"
                        
                        file_path = os.path.join(current_path, filename)
                        print(f"尝试保存图像 {idx+1}/{len(images_to_save)} 到: {file_path}")
                        img.save(file_path)
                        saved_paths.append(file_path)
                    
                    # 所有图像保存成功
                    break
                    
                except Exception as e:
                    print(f"保存到 {current_path} 失败: {e}")
                    tried_paths.append(f"{current_path} (保存失败)")
                    saved_paths = []
                    continue
        
        if should_save and saved_paths:
            print(f"图像保存成功: {', '.join(saved_paths)}")
            return f"图像保存成功: {len(saved_paths)} 张"
        elif not should_save:
            print("跳过保存，仅显示图像")
            return f"图像显示完成: {len(images_to_save)} 张（未保存）"
        else:
            return f"操作失败: 所有保存路径都失败了 ({', '.join(tried_paths)})"
    
    except Exception as e:
        print(f"图片保存/显示失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"操作失败: {str(e)}"

if __name__ == "__main__":
    print("测试图片保存/显示模块:")
    result = execute(None)
    print(f"执行结果: {result}")
