#input_quantity=002
#variable_quantity=003
#userinput=F
#showingwindow_quantity=000
#inputtingwindow_quantity=000
#setting=T
#output_quantity=001
#time_late=00000000
#excitedbydata=T
#name=比大小
#kind=处理模块
#variables_name=a,b,运算符
#output_name=结果

def compare(a, b, operator='>'):
    """
    比较两个值的大小
    输入口全none（无输入或输入全为空）不输出
    若一口输入none，则none小于任何东西
    若比大小结果为True则输出1，False输出0
    """
    print(f'比大小模块输入: a={a}, b={b}, operator={operator}, 类型: a={type(a)}, b={type(b)}')
    
    # 检查是否全为None
    if a is None and b is None:
        print('全为None，返回None')
        return None
    
    # 处理None值
    if a is None:
        # None小于任何东西
        # a < b 或 a <= b 为 True
        # a > b 或 a >= b 为 False
        # a != b 为 True（因为None不等于任何值）
        # a == b 为 False（除非b也是None）
        if operator in ('<', '<='):
            print('a为None，operator为<或<=，返回1')
            return "1"
        elif operator == '!=':
            print('a为None，operator为!=，返回1')
            return "1"
        else:
            print('a为None，operator为其他，返回0')
            return "0"
    if b is None:
        # None小于任何东西
        # a > b 或 a >= b 为 True
        # a < b 或 a <= b 为 False
        # a != b 为 True（因为None不等于任何值）
        # a == b 为 False
        if operator in ('>', '>='):
            print('b为None，operator为>或>=，返回1')
            return "1"
        elif operator == '!=':
            print('b为None，operator为!=，返回1')
            return "1"
        else:
            print('b为None，operator为其他，返回0')
            return "0"
    
    # 尝试将a和b转换为数值
    try:
        # 首先尝试转换为浮点数
        a_val = float(a)
        b_val = float(b)
        print(f'转换为数值: a_val={a_val}, b_val={b_val}')
        
        # 执行数值比较
        if operator == '>':
            result = a_val > b_val
        elif operator == '>=':
            result = a_val >= b_val
        elif operator == '<':
            result = a_val < b_val
        elif operator == '<=':
            result = a_val <= b_val
        elif operator == '==':
            result = a_val == b_val
        elif operator == '!=':
            result = a_val != b_val
        else:
            print(f'未知运算符: {operator}，返回0')
            return "0"
        
        print(f'比较结果: {result}，返回{"1" if result else "0"}')
        return "1" if result else "0"
    except (ValueError, TypeError):
        # 如果转换失败，尝试字符串比较
        print('转换为数值失败，尝试字符串比较')
        try:
            result = eval(f"{repr(a)} {operator} {repr(b)}")
            print(f'字符串比较结果: {result}，返回{"1" if result else "0"}')
            return "1" if result else "0"
        except:
            # 如果比较失败，返回0
            print('比较失败，返回0')
            return "0"