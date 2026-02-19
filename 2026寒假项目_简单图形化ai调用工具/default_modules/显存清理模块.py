#input_quantity=1
#variable_quantity=2
#userinput=false
#setting=true
#output_quantity=0
#time_late=0
#name=显存清理模块
#excitedbydata=true
#variables_name=触发信号
#kind=处理模块

import gc

"""
显存清理模块
功能：接收K采样器的Latent张量作为触发信号，自动清理GPU显存
"""

def execute(trigger_signal, settings=None, cancel_token=None):
    """
    执行模块逻辑
    :param trigger_signal: 触发信号（通常是K采样器的Latent张量）
    :param settings: 设置参数
    :param cancel_token: 取消令牌
    :return: None（无输出值）
    """
    # 默认设置
    default_settings = {
        "清理时机": "采样后",
        "强制清理": True
    }
    
    # 合并设置
    if settings:
        default_settings.update(settings)
    
    # 获取设置值
    clean_timing = default_settings.get("清理时机", "采样后")
    force_clean = bool(default_settings.get("强制清理", True))
    
    print(f"显存清理参数: 时机={clean_timing}, 强制清理={force_clean}")
    
    try:
        # 检查取消令牌
        if cancel_token and cancel_token():
            raise Exception("清理已取消")
        
        # 模拟清理显存
        # 实际项目中应替换为真实的显存清理代码
        print(f"开始清理显存...")
        print(f"触发信号: {trigger_signal}")
        print(f"清理时机: {clean_timing}")
        
        # 模拟清理过程
        print("执行垃圾回收...")
        gc.collect()
        
        # 模拟GPU显存清理
        # 实际项目中应使用torch.cuda.empty_cache()等方法
        print("清理GPU显存...")
        
        if force_clean:
            print("执行强制清理...")
        
        print("显存清理完成")
        
        # 无输出值
        return None
    except Exception as e:
        print(f"显存清理失败: {str(e)}")
        # 返回错误信息
        return f"清理失败: {str(e)}"

# 模块入口
if __name__ == "__main__":
    # 模拟触发信号
    class MockTrigger:
        def __repr__(self):
            return "MockLatentTensor()"
    
    # 测试清理功能
    print("测试显存清理模块:")
    test_trigger = MockTrigger()
    test_settings = {
        "清理时机": "采样后",
        "强制清理": True
    }
    result = execute(test_trigger, test_settings)
    print(f"执行结果: {result}")
