#input_quantity=001
#variable_quantity=001
#userinput=false
#showingwindow_quantity=001
#inputtingwindow_quantity=000
#setting=false
#output_quantity=001
#time_late=000
#name=缓存模块
#excitedbydata=true
#variables_name=input
#kind=处理模块
#output_name=output

# 全局缓存变量
_cache = ""


def execute(input_data):
    """
    执行缓存逻辑
    :param input_data: 输入数据
    :return: 缓存的数据
    """
    global _cache
    
    # 如果输入数据不是None，则更新缓存（包括空字符串、0、False等）
    if input_data is not None:
        _cache = input_data
    
    # 返回缓存的数据
    return _cache


# 模块入口
if __name__ == "__main__":
    # 测试缓存模块
    test_data = "测试缓存数据"
    result = execute(test_data)
    print(f"缓存模块测试结果: {result}")
    
    # 测试无输入时返回缓存数据
    result2 = execute(None)
    print(f"无输入时返回缓存: {result2}")

"""
缓存模块

功能：
- 缓存输入数据并输出
- 当输入数据为None时，返回之前缓存的数据
- 当输入数据不为None时，更新缓存并返回

使用场景：
- 作为工作流中的数据缓存器
- 在需要保存中间结果的工作流中使用
- 用于实现数据的持久化传递

输入：
- input：需要缓存的输入数据

输出：
- output：缓存的数据

端口详细说明：
- 输入端口：1个
  - 端口0: input（需要缓存的数据）
- 输出端口：1个
  - 端口0: output（缓存的数据）
"""
