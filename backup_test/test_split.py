# 测试文件

import c
import t

class Person:
    name: t.CChar
    age: t.CInt
    
    def __init__(self, name: t.CChar, age: t.CInt):
        self.name = name
        self.age = age
    
    def get_name(self) -> t.CChar:
        return self.name
    
    def get_age(self) -> t.CInt:
        return self.age

def main() -> t.CInt:
    p = Person("Alice", 30)
    print(p.get_name())
    print(p.get_age())
    return 0

if __name__ == "__main__":
    main()
