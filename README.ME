# TransPyC README

TransPyC 是一个 Python 到 C 代码生成器，它可以将 Python 代码转换为等效的 C 代码，特别适用于系统编程和嵌入式开发。

## 项目结构

```
TransPyC/
├── TransPyC.py          # 主程序入口
├── c.py                 # C 语言辅助函数
├── t.py                 # 类型定义模块
├── lib/                 # 核心库
│   ├── constants/       # 常量定义
│   ├── core/            # 核心翻译逻辑
│   └── includes/        # 包含文件
├── test/                # 测试示例
├── backup_test/         # 备份测试文件
└── README.ME            # 项目文档
```

## 安装和使用

### 依赖项
- Python 3.6+
- 无其他外部依赖

### 安装
1. 克隆或下载 TransPyC 到本地目录
   ```bash
   git clone https://github.com/GVSADS/TransPyC.git
   cd TransPyC
   ```
2. 确保安装了 Python 3.6+

### 使用方法
```bash
python TransPyC.py -f input.py -o output.c
```
- `-f`: 指定输入的 Python 文件
- `-o`: 指定输出的 C 文件

### 命令行选项
```bash
python TransPyC.py --help
```

## 基本语法规则

### 1. 变量声明和类型注解

使用 `t` 模块提供的类型进行注解：

```python
import t

# 声明整型变量
x: t.CInt = 42

# 声明结构体指针
var: t.CStruct | t.CPtr = value
```

### 2. 指针操作

#### 指针声明
```python
import t

# 声明结构体指针
p: t.CStruct | t.CPtr = value

# 声明普通指针
ptr: t.CPtr = 0x1000
```

#### 指针解引用
在 Python 中，TransPyC 会自动处理指针解引用：

```python
# 读取指针指向的值
value = c.Ptr(0x1000)

# 写入指针指向的值
c.Ptr(0x1000, 42)

# 带类型的指针操作
value = c.Ptr(0x1000, type=t.CInt())
c.Ptr(0x1000, 42, type=t.CInt())
```

#### 取地址操作
使用 `c.Addr()` 函数获取变量的地址：

```python
# 获取变量的地址
p = c.Addr(s)  # 等价于 C 中的 p = &s
```

### 3. 结构体和类

#### 类定义
在 Python 中定义类，TransPyC 会将其转换为 C 结构体：

```python
class a:
    k1: t.CInt
    led: t.CInt
    
    def __init__(self, led: t.CInt = 0):
        self.led = led
        self.led += 1
    
    def add(self, x: t.CInt) -> t.CInt:
        self.led += x
        return self.led
```

生成的 C 代码：
```c
struct a {
    int k1;
    int led;
};

void a____init__(struct a* self, int led) {
    self->led = led;
    self->led += 1;
}

int a__add(struct a* self, int x) {
    self->led += x;
    return self->led;
}
```

#### 结构体实例化和使用
```python
# 实例化结构体
s: t.CStruct | a = a(1)

# 结构体成员访问
s.k1 = 42

# 指针成员访问
p = c.Addr(s)
p->led = 10
```

### 4. 方法调用

```python
# 方法调用
s.test_bubble_sort()
```

生成的 C 代码：
```c
a__test_bubble_sort(&s);
```

### 5. 复合赋值运算符

支持所有复合赋值运算符，如 `+=`, `-=`, `*=`, `/=`, `|=`, `&=`, `^=`, `<<=`, `>>=` 等：

```python
# 复合赋值
s.led += 1
p.flags |= 0x20
```

生成的 C 代码：
```c
s.led += 1;
p->flags |= 32;
```

### 6. 汇编代码支持

使用 `c.Asm()` 函数嵌入汇编代码：

```python
def io_out8(port: t.CInt, value: t.CInt):
    c.Asm("out %0, %1" % (value, port))
```

生成的 C 代码：
```c
void io_out8(int port, int value) {
    asm volatile ("out %0, %1" : : "a"(value), "d"(port));
}
```

## 指针操作详细说明

### 自动指针检测
TransPyC 会根据变量名和类型注解自动检测指针：

1. **通过类型注解检测**：
   - 带有 `t.CPtr` 注解的变量被视为指针
   - 带有 `t.CStruct | t.CPtr` 注解的变量被视为结构体指针

2. **通过变量名检测**：
   - 变量名 `p` 被默认为指针
   - 其他单字母变量名可能也会被视为指针（可根据需要扩展）

3. **通过上下文检测**：
   - 使用 `c.Addr()` 函数的结果被视为指针
   - 方法调用的第一个参数（self）被视为指针

### 指针成员访问

- **指针**：使用 `->` 运算符（如 `p->led`）
- **非指针**：使用 `.` 运算符（如 `s.led`）

TransPyC 会根据变量是否是指针自动选择正确的运算符：

```python
# s 是结构体变量
s.led = 10  # 生成 s.led = 10;

# p 是指针
p.led = 10  # 生成 p->led = 10;
```

## 示例代码

### 完整示例

```python
import t
import c

# 定义类（会转换为结构体）
class a:
    k1: t.CInt
    led: t.CInt
    
    def __init__(self, led: t.CInt = 0):
        self.led = led
        self.led += 1
    
    def add(self, x: t.CInt) -> t.CInt:
        self.led += x
        return self.led

# 测试函数
def test_ptr_operations():
    # 测试指针操作
    c.Ptr(0x1000, 42)  # 写入指针
    value = c.Ptr(0x1000)  # 读取指针
    
    # 声明指针
    var: t.CStruct | t.CPtr = value
    var2: t.CStruct | t.CPtr = value()

# IO 操作函数
def io_out8(port: t.CInt, value: t.CInt):
    c.Asm("out %0, %1" % (value, port))

def main() -> t.CInt:
    # 实例化结构体
    s: t.CStruct | a = a(1)
    
    # 使用指针
    p = c.Addr(s)
    p.flags |= 0x20
    
    # 调用方法
    s.add(5)
    
    # 调用 IO 函数
    io_out8(0x3C8, 0)
    
    return 0
```

## 测试方法

### 生成和编译测试代码

1. 生成 C 代码
   ```bash
   python TransPyC.py -f test/example1.py -o test/example1.c
   ```

2. 编译生成的 C 代码
   ```bash
   gcc -o test/example1.exe test/example1.c
   ```

3. 运行测试
   ```bash
   test/example1.exe
   ```

### 示例测试文件

- `test/example1.py` - 基本语法测试
- `test/example2.py` - 指针操作测试
- `test/test_simple.py` - 简单功能测试

## 故障排除

### 常见问题

1. **指针操作错误**
   - 症状：生成的 C 代码中指针操作不正确
   - 解决方案：确保使用正确的类型注解，或使用 `c.Addr()` 明确获取地址

2. **类型不匹配**
   - 症状：生成的 C 代码编译失败，提示类型错误
   - 解决方案：为所有变量添加明确的类型注解

3. **不支持的语法**
   - 症状：生成的 C 代码不完整或有错误
   - 解决方案：避免使用高级 Python 特性，如列表推导式、生成器等

4. **汇编代码错误**
   - 症状：生成的汇编代码编译失败
   - 解决方案：确保汇编代码符合 GCC 内联汇编语法

### 调试技巧

1. **查看生成的 C 代码**：检查生成的 C 代码是否符合预期
2. **使用简单示例**：从简单的代码开始测试，逐步添加复杂性
3. **参考示例代码**：查看 `test/` 目录中的示例代码

## 贡献指南

### 如何贡献

1. **Fork 仓库**：在 GitHub 上 fork 项目仓库
2. **创建分支**：创建一个新的分支进行开发
3. **提交更改**：提交你的更改并添加详细的提交信息
4. **创建 Pull Request**：向主仓库提交 Pull Request

### 代码风格

- 遵循 Python PEP 8 代码风格
- 保持代码清晰、简洁、易于理解
- 添加适当的注释说明复杂逻辑

### 开发建议

- **核心功能**：修改 `lib/core/translator.py` 以扩展核心翻译功能
- **类型系统**：修改 `t.py` 和 `lib/includes/` 中的文件以扩展类型系统
- **辅助函数**：修改 `c.py` 以添加新的辅助函数

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 结语

TransPyC 提供了一种从 Python 生成 C 代码的简单方法，特别适用于需要精确控制内存和硬件的系统编程场景。通过本文档介绍的语法和规则，你可以编写清晰、可维护的 Python 代码，并将其转换为高效的 C 代码。

如果你有任何问题或建议，欢迎在 GitHub 上提出 Issue 或 Pull Request。