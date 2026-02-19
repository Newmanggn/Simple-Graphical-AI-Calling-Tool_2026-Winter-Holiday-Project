#input_quantity=2      # 输入端口数量
#variable_quantity=3    # 变量数量
#userinput=false          # 是否支持用户输入
#setting=true            # 是否支持设置
#output_quantity=1      # 输出端口数量
#time_late=0            # 延迟时间
#name=负面提示词编码模块    # 模块名称
#excitedbydata=true        # 是否可被数据激活
#variables_name=优化后CLIP,负面提示词,最大Token长度,提示词输入  # 变量名称
#kind=处理模块            # 模块类型
#output_name=负面文本向量

"""
负面提示词编码模块
功能：把负面提示词转为文本嵌入向量，输出到采样模块
"""

class MockTextEmbedding:
    """
    模拟文本嵌入向量对象
    实际项目中应替换为真实的文本编码逻辑
    """
    def __init__(self, prompt, max_tokens):
        self.prompt = prompt
        self.max_tokens = max_tokens
        self.embedding_shape = (1, max_tokens, 768)  # 模拟嵌入向量形状
    
    def __repr__(self):
        return f"MockTextEmbedding(prompt='{self.prompt[:20]}...', max_tokens={self.max_tokens}, shape={self.embedding_shape})"

def execute(optimized_clip, prompt_input=None, settings=None):
    """
    执行模块逻辑
    :param optimized_clip: 优化后的CLIP模型对象
    :param prompt_input: 提示词输入（可选，优先使用）
    :param settings: 设置参数
    :return: 负面文本嵌入向量
    """
    # 默认设置
    default_settings = {
        "负面提示词": "ugly, blurry, bad quality",
        "最大Token长度": 77
    }
    
    # 合并设置
    if settings:
        default_settings.update(settings)
    
    # 获取设置值 - 优先使用输入端口的提示词
    negative_prompt = prompt_input if prompt_input is not None else default_settings.get("负面提示词", "ugly, blurry, bad quality")
    max_tokens = int(default_settings.get("最大Token长度", 77))
    
    print(f"负面提示词编码参数: 提示词='{negative_prompt}', 最大Token长度={max_tokens}")
    
    try:
        # 模拟编码负面提示词
        # 实际项目中应替换为真实的文本编码代码
        text_embedding = MockTextEmbedding(negative_prompt, max_tokens)
        print(f"负面提示词编码成功: {text_embedding}")
        
        return text_embedding
    except Exception as e:
        print(f"负面提示词编码失败: {str(e)}")
        # 返回错误信息
        return f"编码失败: {str(e)}"

# 模块入口
if __name__ == "__main__":
    # 模拟优化后的CLIP对象
    class MockOptimizedCLIP:
        def __repr__(self):
            return "MockOptimizedCLIP()"
    
    # 测试编码功能
    print("测试负面提示词编码:")
    test_clip = MockOptimizedCLIP()
    test_settings = {
        "负面提示词": "ugly, blurry, bad quality, low resolution",
        "最大Token长度": 77
    }
    result = execute(test_clip, test_settings)
    print(f"编码结果: {result}")
