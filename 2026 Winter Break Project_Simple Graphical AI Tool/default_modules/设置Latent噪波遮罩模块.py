#input_quantity=2
#variable_quantity=0
#userinput=false
#setting=false
#output_quantity=1
#time_late=0
#name=设置Latent噪波遮罩模块
#excitedbydata=true
#variables_name=latent,遮罩
#kind=处理模块
#output_name=Latent

"""
设置Latent噪波遮罩模块
功能：把遮罩存到latent的字典里之后输出
输入：Latent张量、遮罩
输出：Latent字典 {"latent": latents, "noise_mask": mask_tensor}
"""

import torch
from PIL import Image
import numpy as np

def mask_to_latent_mask(pil_mask, latent_height, latent_width, device):
    """
    将PIL遮罩转换为Latent尺寸的遮罩张量
    """
    if isinstance(pil_mask, list):
        pil_mask = pil_mask[0]
    
    print(f"遮罩处理: 原始尺寸={pil_mask.size}")
    
    # 转换为numpy数组
    mask_np = np.array(pil_mask)
    
    # 如果是3通道或4通道，取第一个通道或转灰度
    if len(mask_np.shape) == 3:
        mask_np = mask_np[..., 0]
    
    # 归一化到[0, 1]
    # 用户涂掉的地方（黑色，值低）应该是要重绘的地方（mask=1）
    # 用户没涂的地方（白色，值高）应该是要保留的地方（mask=0）
    mask_np = mask_np.astype(np.float32) / 255.0
    mask_np = 1.0 - mask_np  # 反转遮罩值，黑色（0）变为1表示重绘，白色（1）变为0表示保留
    
    # 转换为PIL并缩放到Latent尺寸
    mask_pil = Image.fromarray((mask_np * 255).astype(np.uint8))
    mask_pil = mask_pil.resize((latent_width, latent_height), Image.LANCZOS)  # 使用LANCZOS重采样获得更好效果
    
    # 转换回numpy数组
    mask_np_resized = np.array(mask_pil).astype(np.float32) / 255.0
    
    # 添加高斯模糊，避免边缘生硬
    from scipy.ndimage import gaussian_filter
    mask_np_blurred = gaussian_filter(mask_np_resized, sigma=1.0)  # 模糊半径1.0
    
    # 确保mask值在0-1范围内
    mask_np_blurred = np.clip(mask_np_blurred, 0.0, 1.0)
    
    # 转换为PyTorch张量并移动到指定设备
    mask_tensor = torch.from_numpy(mask_np_blurred).unsqueeze(0).unsqueeze(0)
    
    # 扩展为4通道：[1, 1, H, W] → [1, 4, H, W]
    mask_tensor = mask_tensor.repeat(1, 4, 1, 1)  # 关键：复制到4通道
    
    print(f"遮罩处理完成: Latent尺寸={mask_tensor.shape}")
    return mask_tensor.to(device=device)

def execute(latent=None, 遮罩=None):
    """
    执行模块逻辑
    :param latent: Latent张量或者包含latent的字典
    :param 遮罩: PIL遮罩对象或PIL遮罩列表
    :return: Latent字典 {"samples": latent_tensor, "noise_mask": mask_tensor}
    """
    print(f"设置Latent噪波遮罩: 输入latent类型={type(latent)}, 遮罩类型={type(遮罩)}")
    
    try:
        if latent is None:
            print("错误: 缺少Latent输入")
            return None
        
        # 提取latent张量
        if isinstance(latent, dict) and "samples" in latent:
            latent_tensor = latent["samples"]
        elif isinstance(latent, dict) and "latent" in latent:
            latent_tensor = latent["latent"]
        else:
            latent_tensor = latent
        
        print(f"Latent张量形状: {latent_tensor.shape}")
        
        # 处理遮罩
        noise_mask = None
        if 遮罩 is not None:
            latent_height = latent_tensor.shape[2]
            latent_width = latent_tensor.shape[3]
            device = latent_tensor.device
            noise_mask = mask_to_latent_mask(遮罩, latent_height, latent_width, device)
            noise_mask = noise_mask.to(dtype=latent_tensor.dtype)
        elif isinstance(latent, dict) and "noise_mask" in latent:
            # 如果输入latent字典中已经有noise_mask，使用它
            noise_mask = latent["noise_mask"]
        
        # 返回字典格式
        result = {
            "samples": latent_tensor,
            "noise_mask": noise_mask
        }
        
        print(f"设置Latent噪波遮罩完成: 有遮罩={noise_mask is not None}")
        return result
    
    except Exception as e:
        print(f"设置Latent噪波遮罩失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("测试设置Latent噪波遮罩模块:")
    result = execute(None, None)
    print(f"结果: {result}")
