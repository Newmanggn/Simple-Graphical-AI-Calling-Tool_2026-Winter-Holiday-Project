#input_quantity=0
#variable_quantity=0
#userinput=false
#setting=true
#output_quantity=2
#time_late=0
#name=加载图像模块
#excitedbydata=true
#variables_name=
#kind=图像
#output_name=图像,遮罩
#showingwindow_quantity=1

from PIL import Image
import io
import base64

def execute(settings=None):
    """
    执行模块逻辑
    :param settings: 设置字典，包含imageData和maskData
    :return: [image, mask]
    """
    print("加载图像模块执行")
    
    image = None
    mask = None
    
    if settings is not None:
        # 处理图像数据
        if 'imageData' in settings and settings['imageData']:
            try:
                from PIL import Image
                import io
                import base64
                
                # 移除data:image/...前缀
                img_data = settings['imageData']
                if ',' in img_data:
                    img_data = img_data.split(',')[1]
                
                # 解码base64
                img_bytes = base64.b64decode(img_data)
                img_buffer = io.BytesIO(img_bytes)
                image = Image.open(img_buffer).convert('RGB')
                print(f"加载图像成功: 尺寸={image.size}")
            except Exception as e:
                print(f"加载图像失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 处理遮罩数据
        if 'maskData' in settings and settings['maskData']:
            try:
                from PIL import Image
                import io
                import base64
                
                # 移除data:image/...前缀
                mask_data = settings['maskData']
                if ',' in mask_data:
                    mask_data = mask_data.split(',')[1]
                
                # 解码base64
                mask_bytes = base64.b64decode(mask_data)
                mask_buffer = io.BytesIO(mask_bytes)
                mask = Image.open(mask_buffer).convert('L')
                print(f"加载遮罩成功: 尺寸={mask.size}")
            except Exception as e:
                print(f"加载遮罩失败: {e}")
                import traceback
                traceback.print_exc()
    
    return [image, mask]

if __name__ == "__main__":
    print("测试加载图像模块:")
    result = execute()
    print(f"结果: {result}")

"""
加载图像模块

功能：
- 加载图像文件
- 支持预览图像
- 支持绘制和加载遮罩
- 处理base64编码的图像数据

使用场景：
- 作为图生图工作流的起点，加载输入图像
- 作为遮罩重绘工作流的起点，加载图像和遮罩

输入：
- 无输入端口，通过设置界面加载图像和遮罩

输出：
- 图像：加载的PIL图像对象
- 遮罩：加载的PIL遮罩图像（单通道）

端口详细说明：
- 输入端口：0个（无输入）
- 输出端口：2个
  - 端口0: 图像（加载的图像）
  - 端口1: 遮罩（遮罩图像）
"""
