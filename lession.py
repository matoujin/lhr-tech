# 打印“Hello, World!”
print ("hello world!")

# 编写一个程序，输出字符串 "Hello, World!".
#变量赋值

#创建两个变量 a 和 b，分别赋值为 10 和 20，然后打印它们的和.
a=10
b=20
print(a+b)

#用户输入

#编写一个程序，提示用户输入自己的名字，然后输出 "Hello, [名字]!".
# print("请输入你的名字：")
# name = input()
# print("hello. ", name)

#条件判断

#编写一个程序，提示用户输入一个数字，判断该数字是正数、负数还是零，并输出相应的结果.
#循环打印
print("请输入一个数字")
# number = int(input())
# print(type(number))

def judge_func(number):
    if number > 0:
        print("正数")
    elif number < 0:
        print("负数")
    else: print ("零")
    
number = int(input())
judge_func(number)

print ("number:")


#使用 for 循环，打印从 1 到 10 的所有整数.
for i in range(1,10):
    print(i)
#列表操作

#创建一个列表 numbers，包含元素 [1, 2, 3, 4, 5]，然后打印列表的长度和列表中的最后一个元素.
#字符串操作

#创建一个字符串 s，内容为 "Python is fun"，然后打印字符串的长度和字符串中 "fun" 的位置.
#函数定义

#定义一个函数 add，接受两个参数并返回它们的和，然后调用该函数并打印结果.
#简单数学运算

#编写一个程序，提示用户输入两个数字，然后计算并输出它们的和、差、积和商.
#列表推导式

#创建一个列表 squares，包含从 1 到 5 的每个数字的平方，然后打印该列表.