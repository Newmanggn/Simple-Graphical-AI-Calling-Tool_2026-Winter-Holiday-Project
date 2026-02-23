#input_quantity=002
#variable_quantity=002
#userinput=F
#showingwindow_quantity=000
#inputtingwindow_quantity=000
#setting=T
#output_quantity=002
#time_late=00000000
#excitedbydata=T
#name=判断
#kind=处理模块
#variables_name=数据,判断,测试
#output_name=out0,out1

def choose(data, select):
    print(f'判断模块输入: data={data}, select={select}, type={type(select)}')
    out0=None
    out1=None

    # 尝试将select转换为整数
    try:
        select_int = int(select)
    except (ValueError, TypeError):
        select_int = 1  # 默认值为1
    
    print(f'转换后的select: {select_int}')

    if select_int==0:
        out0=data
    if select_int==1:
        out1=data
    print(f'判断模块输出: out0={out0}, out1={out1}')
    return out0, out1