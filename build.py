import TransPyC


def ProcessFile(file: str, output: str):
    """保留原有文件转换逻辑：py转c并添加符号"""
    with open(file, "r") as f:
        code = f.read()
    trans = TransPyC.TransPyC(code=code)
    trans.AddSymbol(TransPyC.SymbolFile("test2.py", type="py"))
    result = trans.Convert()
    # 写入时指定utf-8编码，避免中文/特殊字符乱码
    with open(output, "w") as f:
        f.write(result)
ProcessFile("test.py", "test.c")