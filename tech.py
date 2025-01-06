zhangsan=90
lisi=89
wangwu=34

total=zhangsan+lisi+wangwu
print(total)
average=total/3
print(average)

zhangsan = {} 

zhangsan["english"]=90
zhangsan["math"]=89

print(zhangsan["english"])

lisi={}
lisi["english"]=89
lisi["math"]=90

print(lisi["math"])
print((89+90)/2)
print((zhangsan['english']+lisi["english"])/2)
# lisi["english"]=88
# lisi["math"]=77
# wangwu["english"]=67
# wangwu["math"]=66

zs = zhangsan
ls = lisi
ww = wangwu
stu_score = [ zs, ls, ww]

stu_score[0]["english"]

stu_score = {
    "zhangsan": zhangsan,
    "lisi": lisi,
    "wangwu": wangwu
}

stu_score["lisi"]["english"]

stu = [ "zhangsan", "lisi", "wangwu"]

print(len(stu))
x="a"
y="b"
print(x, end="")
print(y, end="")