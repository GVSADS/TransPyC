# 简单测试文件
import stdio  # std: standard
import lib.includes.c as c
import lib.includes.t as t

# 定义一个简单的函数
def add(a: int, b: int) -> int:
    return a + b

# 定义一个简单的类
class Person:
    name: t.CChar | t.CPtr
    age: t.CInt
    
    def __init__(self, name: t.CChar | t.CPtr, age: t.CInt):
        self.name = name
        self.age = age
    
    def greet(self):
        print(f"Hello, my name is {self.name}")

# 主函数
def main() -> t.CInt:
    # 测试简单函数
    result = add(5, 3)
    print(f"5 + 3 = {result}")

    # 测试类
    p = Person("Alice", 30)
    p.greet()
    
    return 0

if __name__ == "__main__":
    main()
