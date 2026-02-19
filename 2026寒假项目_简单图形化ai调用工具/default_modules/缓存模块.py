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

"""
缓存模块
功能：缓存输入数据并输出
"""

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
