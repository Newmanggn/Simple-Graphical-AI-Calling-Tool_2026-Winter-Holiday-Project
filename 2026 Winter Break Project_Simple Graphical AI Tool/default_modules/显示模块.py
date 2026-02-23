#input_quantity=001
#variable_quantity=001
#userinput=F
#showingwindow_quantity=001
#inputtingwindow_quantity=000
#setting=F
#output_quantity=001
#time_late=00000000
#excitedbydata=T
#name=显示模块
#kind=处理模块
#variables_name=input_data
#output_name=output

"""
显示模块
功能：显示输入数据值，并将输入数据原样输出
"""

def execute(input_data):
    """
    执行显示逻辑
    :param input_data: 输入数据
    :return: 输入数据（原样输出）
    """
    # 显示数据值（在后端日志中显示）
    print(f'显示模块接收到数据: {input_data}, 类型: {type(input_data)}')
    
    # 将输入数据原样输出
    return input_data


# 模块入口
if __name__ == "__main__":
    # 测试显示模块
    test_data = "测试数据"
    result = execute(test_data)
    print(f"显示模块测试结果: {result}")
    
    # 测试数字数据
    test_data = 123
    result = execute(test_data)
    print(f"显示模块测试结果（数字）: {result}")
    
    # 测试None值
    test_data = None
    result = execute(test_data)
    print(f"显示模块测试结果（None）: {result}")
