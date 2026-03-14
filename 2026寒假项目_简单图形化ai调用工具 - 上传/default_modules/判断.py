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

"""
判断模块

功能：
- 根据输入的判断值，将数据输出到不同的端口
- 当判断值为0时，将数据输出到out0端口
- 当判断值为1时，将数据输出到out1端口
- 支持自动将判断值转换为整数

使用场景：
- 作为工作流中的条件分支
- 在需要根据条件选择不同路径的工作流中使用
- 用于实现简单的逻辑判断

输入：
- 数据：需要根据判断值分发的数据
- 判断：判断值，0或1

输出：
- out0：当判断值为0时的数据
- out1：当判断值为1时的数据

端口详细说明：
- 输入端口：2个
  - 端口0: 数据（需要分发的数据）
  - 端口1: 判断（判断值，0或1）
- 输出端口：2个
  - 端口0: out0（当判断值为0时的数据）
  - 端口1: out1（当判断值为1时的数据）
"""