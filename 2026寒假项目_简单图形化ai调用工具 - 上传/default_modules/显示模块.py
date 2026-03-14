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

"""
显示模块

功能：
- 显示输入数据值
- 将输入数据原样输出
- 在后端日志中显示数据内容

使用场景：
- 作为工作流中的调试工具，显示中间数据
- 在需要查看数据内容的工作流中使用
- 作为数据传递的中间节点

输入：
- input_data：需要显示和传递的输入数据

输出：
- output：原样输出的输入数据

端口详细说明：
- 输入端口：1个
  - 端口0: input_data（需要显示的数据）
- 输出端口：1个
  - 端口0: output（原样输出的数据）
"""
