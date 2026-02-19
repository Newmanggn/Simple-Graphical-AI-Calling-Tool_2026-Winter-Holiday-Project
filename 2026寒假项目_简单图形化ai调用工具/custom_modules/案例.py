#input_quantity=002
#variable_quantity=002
#userinput=F
#showingwindow_quantity=001
#inputtingwindow_quantity=000
#setting=F
#output_quantity=002
#time_late=00000000
#excitedbydata=T
#name=案例
#kind=判断模块
#variables_name=数据,判断
#output_name=out0,out1

def choose(data, select):
    out0=None
    out1=None

    if select==0:
        out0=data
    if select==1:
        out1=data
    return out0, out1