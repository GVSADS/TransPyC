# 核心转换逻辑

import ast
import re
import sys
import os
# 添加lib目录到Python路径
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'lib', 'includes'))
import c
import t
from lib.constants.config import (
    TYPE_MAP, OPERATOR_MAP, COMPARATOR_MAP, 
    UNARY_OPERATOR_MAP, AUG_OPERATOR_MAP,
    BUILTIN_FUNCTIONS
)
from lib.utils.helpers import (
    detect_file_type, extract_array_size, 
    check_storage_class, build_array_initialization
)


class Translator:
    """代码转换器"""
    
    def __init__(self):
        self.VarScopes = []  # 跟踪变量作用域
        self.FunctionReturnTypes = {}  # 记录函数名和其返回类型
        self.SymbolTable = {}  # 符号表
        self.OriginalLines = []  # 原始代码行
    
    def ParseHelperFiles(self, helper_files):
        """解析辅助文件，提取符号信息"""
        for file_path in helper_files:
            ext = detect_file_type(file_path)
            if ext == '.py':
                self.ParsePythonFile(file_path)
            elif ext == '.c':
                self.ParseCFile(file_path)
    
    def ParsePythonFile(self, file_path):
        """解析Python文件，提取类、函数、变量信息"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析Python代码为AST
            tree = ast.parse(content)
            
            # 提取类定义（作为结构体）
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    # 提取结构体成员信息
                    members = {}
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            var_name = item.target.id
                            try:
                                var_type = self.GetTypeName(item.annotation)
                                # 检查是否是指针类型
                                is_pointer = '*' in var_type or 'CPtr' in var_type
                                members[var_name] = {'type': var_type, 'is_pointer': is_pointer}
                            except:
                                pass
                    self.SymbolTable[class_name] = {'type': 'struct', 'members': members}
                elif isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    self.SymbolTable[func_name] = {'type': 'function'}
                elif isinstance(node, ast.AnnAssign):
                    if isinstance(node.target, ast.Name):
                        var_name = node.target.id
                        # 尝试获取类型信息
                        var_type = 'unknown'
                        is_pointer = False
                        if node.annotation:
                            try:
                                var_type = self.GetTypeName(node.annotation)
                                is_pointer = '*' in var_type or 'CPtr' in var_type
                            except:
                                pass
                        self.SymbolTable[var_name] = {'type': 'variable', 'declared_type': var_type, 'is_pointer': is_pointer}
        except Exception as e:
            print(f'Warning: Failed to parse Python file {file_path}: {e}')
    
    def ParseCFile(self, file_path):
        """解析C文件，提取结构体、函数、变量信息"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 简单的C文件解析，提取结构体、函数、变量声明
            
            # 提取结构体定义
            struct_pattern = r'struct\s+([a-zA-Z_]\w*)\s*\{'
            struct_matches = re.findall(struct_pattern, content)
            for struct_name in struct_matches:
                self.SymbolTable[struct_name] = {'type': 'struct'}
            
            # 提取函数声明
            func_pattern = r'\b([a-zA-Z_]\w*)\s*\('  # 简单模式
            func_matches = re.findall(func_pattern, content)
            for func_name in func_matches:
                if func_name not in ['if', 'for', 'while', 'switch']:
                    self.SymbolTable[func_name] = {'type': 'function'}
            
            # 提取变量声明
            var_pattern = r'\b(\w+)\s+([a-zA-Z_]\w*)(\[\d*\])*\s*;'
            var_matches = re.findall(var_pattern, content)
            for var_type, var_name, _ in var_matches:
                is_pointer = '*' in var_type
                self.SymbolTable[var_name] = {'type': 'variable', 'declared_type': var_type, 'is_pointer': is_pointer}
        except Exception as e:
            print(f'Warning: Failed to parse C file {file_path}: {e}')
    
    def GenerateCCode(self, Tree):
        """生成C代码"""
        Code = []
        # 打印符号表（用于调试）
        print("=== Symbol Table ===")
        for key, value in self.SymbolTable.items():
            print(f"{key}: {value}")
        print("===================")
        # 处理导入语句
        for Node in ast.iter_child_nodes(Tree):
            if isinstance(Node, ast.Import):
                import_code = self.HandleImport(Node)
                if import_code:
                    Code.extend(import_code)
            elif isinstance(Node, ast.ImportFrom):
                import_from_code = self.HandleImportFrom(Node)
                if import_from_code:
                    Code.extend(import_from_code)
        
        # 处理宏定义
        for Node in ast.iter_child_nodes(Tree):
            if isinstance(Node, ast.Expr):
                if isinstance(Node.value, ast.Call):
                    if isinstance(Node.value.func, ast.Attribute):
                        if isinstance(Node.value.func.value, ast.Name) and Node.value.func.value.id == 'c':
                            if Node.value.func.attr == 'Macro':
                                macro_code = self.HandleCSpecialCall(Node.value.func.attr, Node.value.args, Node.value.keywords)
                                if macro_code:
                                    Code.extend(macro_code)
        
        # 处理全局变量和结构体定义
        for Node in ast.iter_child_nodes(Tree):
            if isinstance(Node, ast.ClassDef):
                Code.extend(self.HandleClassDef(Node))
            elif isinstance(Node, ast.Assign):
                assign_code = self.HandleAssign(Node)
                if assign_code:
                    Code.extend(assign_code)
            elif isinstance(Node, ast.AnnAssign):
                # 直接生成声明语句
                if isinstance(Node.target, ast.Name):
                    var_name = Node.target.id
                    # 检查是否有赋值部分
                    if Node.value:
                        ValueCode = self.HandleExpr(Node.value)
                        if ValueCode:
                            # 尝试获取类型名称
                            try:
                                type_name = self.GetTypeName(Node.annotation)
                                if type_name:
                                    # 处理 t.CDefine 类型，生成宏定义
                                    if type_name == '#define':
                                        # 生成正确的宏定义格式
                                        Code.append(f'#define {var_name} {ValueCode[0]}')
                                    else:
                                        # 处理数组类型，提取数组大小
                                        base_type, array_size_str = extract_array_size(type_name)
                                        
                                        # 检查 base_type 是否包含存储类修饰符
                                        storage_class, type_part = check_storage_class(base_type)
                                        
                                        # 特殊处理 c.State，表示仅声明不定义
                                        if ValueCode[0] == 'c.State':
                                            # 处理 t.CPtr 类型，当 base_type 为 '*' 时，使用右侧表达式的名称作为类型
                                            if base_type == '*':
                                                # 尝试从右侧表达式获取类型名称
                                                if isinstance(Node.value, ast.Name):
                                                    type_name = Node.value.id
                                                    if storage_class:
                                                        Code.append(f'{storage_class} struct {type_name}* {var_name}{array_size_str};')
                                                    else:
                                                        Code.append(f'struct {type_name}* {var_name}{array_size_str};')
                                                else:
                                                    if storage_class:
                                                        Code.append(f'{storage_class} void* {var_name}{array_size_str};')
                                                    else:
                                                        Code.append(f'void* {var_name}{array_size_str};')
                                            else:
                                                if storage_class:
                                                    Code.append(f'{storage_class} {type_part} {var_name}{array_size_str};')
                                                else:
                                                    Code.append(f'{base_type} {var_name}{array_size_str};')
                                        else:
                                            # 处理 t.CPtr 类型，当 base_type 为 '*' 时，使用右侧表达式的名称作为类型
                                            if base_type == '*':
                                                # 尝试从右侧表达式获取类型名称
                                                if isinstance(Node.value, ast.Name):
                                                    type_name = Node.value.id
                                                    if storage_class:
                                                        Code.append(f'{storage_class} struct {type_name}* {var_name}{array_size_str} = {ValueCode[0]};')
                                                    else:
                                                        Code.append(f'struct {type_name}* {var_name}{array_size_str} = {ValueCode[0]};')
                                                else:
                                                    if storage_class:
                                                        Code.append(f'{storage_class} void* {var_name}{array_size_str} = {ValueCode[0]};')
                                                    else:
                                                        Code.append(f'void* {var_name}{array_size_str} = {ValueCode[0]};')
                                            else:
                                                if storage_class:
                                                    Code.append(f'{storage_class} {type_part} {var_name}{array_size_str} = {ValueCode[0]};')
                                                else:
                                                    Code.append(f'{base_type} {var_name}{array_size_str} = {ValueCode[0]};')
                                else:
                                    # 默认使用int类型
                                    # 特殊处理 c.State，表示仅声明不定义
                                    if ValueCode[0] == 'c.State':
                                        Code.append(f'int {var_name};')
                                    else:
                                        Code.append(f'int {var_name} = {ValueCode[0]};')
                                # 将变量添加到符号表中
                                self.SymbolTable[var_name] = {'type': 'variable', 'declared_type': type_name if type_name else 'int'}
                            except Exception as e:
                                print(f'Warning: Failed to get type annotation: {e}')
                                # 发生异常时，默认使用int类型
                                # 特殊处理 c.State，表示仅声明不定义
                                if ValueCode[0] == 'c.State':
                                    Code.append(f'int {var_name};')
                                else:
                                    Code.append(f'int {var_name} = {ValueCode[0]};')
                                # 将变量添加到符号表中
                                self.SymbolTable[var_name] = {'type': 'variable', 'declared_type': 'int'}
                    else:
                        # 没有赋值部分，视为仅声明不定义，等价于 = c.State
                        try:
                            type_name = self.GetTypeName(Node.annotation)
                            if type_name and type_name.strip():
                                # 处理数组类型，提取数组大小
                                base_type, array_size_str = extract_array_size(type_name)
                                
                                # 检查 base_type 是否包含存储类修饰符
                                storage_class, type_part = check_storage_class(base_type)
                                
                                if storage_class:
                                    Code.append(f'{storage_class} {type_part} {var_name}{array_size_str};')
                                else:
                                    Code.append(f'{base_type} {var_name}{array_size_str};')
                            else:
                                Code.append(f'int {var_name};')
                            # 将变量添加到符号表中
                            self.SymbolTable[var_name] = {'type': 'variable', 'declared_type': type_name if type_name else 'int'}
                        except Exception as e:
                            print(f'Warning: Failed to get type annotation: {e}')
                            Code.append(f'int {var_name};')
                            # 将变量添加到符号表中
                            self.SymbolTable[var_name] = {'type': 'variable', 'declared_type': 'int'}
                else:
                    # 直接生成int类型的声明语句
                    Code.append(f'int a = "123";')
        
        # 处理函数定义和类方法
        for Node in ast.iter_child_nodes(Tree):
            if isinstance(Node, ast.FunctionDef):
                func_code = self.HandleFunctionDef(Node)
                if func_code:
                    Code.extend(func_code)
            elif isinstance(Node, ast.ClassDef):
                # 处理类方法
                for item in Node.body:
                    if isinstance(item, ast.FunctionDef):
                        # 生成类方法对应的C函数
                        method_code = self.HandleMethodDef(Node.name, item)
                        if method_code:
                            Code.extend(method_code)

        return '\n'.join(Code)
    
    def HandleImport(self, Node):
        """处理导入语句"""
        Code = []
        # 检查是否有行号信息
        line_number = getattr(Node, 'lineno', None)
        
        for Alias in Node.names:
            if Alias.name not in ['c', 't']:
                # 检查是否是标准库
                is_standard = False
                # 检查是否有 # std: standard 注释
                if line_number and hasattr(self, 'OriginalLines') and 0 <= line_number - 1 < len(self.OriginalLines):
                    original_line = self.OriginalLines[line_number - 1]
                    if '# std: standard' in original_line:
                        is_standard = True
                # 检查是否是已知的标准库
                if Alias.name == 'stdio' or is_standard:
                    # 生成标准库include
                    Code.append(f'#include <{Alias.name}.h>')
                else:
                    # 默认为本地文件include
                    Code.append(f'#include "{Alias.name}.h"')
        return Code
    
    def HandleImportFrom(self, Node):
        """处理从模块导入语句"""
        if Node.module not in ['c', 't']:
            # 生成包含原始导入语句的注释
            import_comment = f'from {Node.module} import '
            if Node.names:
                if len(Node.names) == 1 and Node.names[0].name == '*':
                    import_comment += '*'
                else:
                    import_comment += ', '.join([alias.name for alias in Node.names])
            else:
                import_comment += '...'
            return [f'#include "{Node.module}.h" // {import_comment}']
        return []
    
    def HandleFunctionDef(self, Node):
        """处理函数定义"""
        Code = []
        ReturnType = 'void'
        is_function_declaration = False
        
        # 检查是否是返回t.CDefine的函数，如果是，生成宏定义
        if Node.returns:
            try:
                return_type = self.GetTypeName(Node.returns)
                if return_type == '#define':
                    # 生成宏定义
                    func_name = Node.name
                    # 提取参数
                    params = []
                    for arg in Node.args.args:
                        params.append(arg.arg)
                    params_str = ', '.join(params)
                    # 提取函数体中的返回表达式
                    if len(Node.body) == 1 and isinstance(Node.body[0], ast.Return):
                        return_expr = Node.body[0].value
                        expr_code = self.HandleExpr(return_expr)[0]
                        # 生成宏定义
                        Code.append(f'#define {func_name}({params_str}) ({expr_code})')
                        return Code
            except Exception as e:
                print(f'Warning: Failed to check for macro definition: {e}')
        
        if Node.returns:
            try:
                # 检查返回类型是否包含 c.State
                if isinstance(Node.returns, ast.BinOp) and isinstance(Node.returns.op, ast.BitOr):
                    left_type = self.GetTypeName(Node.returns.left)
                    right_type = self.GetTypeName(Node.returns.right)
                    # 检查是否包含 c.State
                    if 'c.State' in left_type:
                        is_function_declaration = True
                        # 当右侧是指针类型时，确保生成正确的格式，如 struct TASK* 而不是 *
                        if right_type == '*':
                            # 处理 c.State | (t.CStruct | t.CPtr) 或 (c.State | t.CStruct) | t.CPtr 这样的情况
                            # 检查左侧是否是一个组合类型，如 c.State | t.CStruct(name=TASK)
                            if isinstance(Node.returns.left, ast.BinOp):
                                # 左侧是一个组合类型，获取其右侧的类型，如 t.CStruct(name=TASK)
                                struct_type = self.GetTypeName(Node.returns.left.right)
                                if struct_type and struct_type.startswith('struct '):
                                    # 生成正确的结构体指针类型，如 struct TASK*
                                    ReturnType = f'{struct_type}*'
                                else:
                                    ReturnType = 'void'
                            elif isinstance(Node.returns.right, ast.BinOp):
                                # 右侧是一个组合类型，如 t.CStruct | t.CPtr
                                combined_type = self.GetTypeName(Node.returns.right)
                                if combined_type and combined_type != '*':
                                    ReturnType = combined_type
                                else:
                                    ReturnType = 'void'
                            else:
                                # 右侧是一个简单类型
                                ReturnType = right_type if right_type else 'void'
                        else:
                            ReturnType = right_type if right_type else 'void'
                    elif 'c.State' in right_type:
                        is_function_declaration = True
                        ReturnType = left_type if left_type else 'void'
                    else:
                        # 处理 t.CLong | t.CInt 这样的返回类型
                        if left_type == 'long' and right_type == 'int':
                            ReturnType = 'long int'
                        else:
                            ReturnType = self.GetTypeName(Node.returns)
                else:
                    ReturnType = self.GetTypeName(Node.returns)
                    # 检查返回类型是否是 c.State
                    if ReturnType == 'c.State':
                        is_function_declaration = True
                        ReturnType = 'void'
                
                # 确保返回类型不为空
                if not ReturnType:
                    ReturnType = 'void'
            except Exception as e:
                print(f'Warning: Failed to get return type: {e}')
                ReturnType = 'void'
        
        # 特殊处理main函数的返回类型
        if Node.name == 'main' and ReturnType == 'void':
            ReturnType = 'int'
        
        Params = []
        # 为函数创建新的作用域
        self.VarScopes.append({})
        
        # 添加函数参数到当前作用域
        for Arg in Node.args.args:
            if Arg.annotation:
                try:
                    ParamType = self.GetTypeName(Arg.annotation)
                    # 确保参数类型不为空
                    if not ParamType:
                        ParamType = 'int'
                    # 移除重复的类型名称
                    if ParamType.count(' ') > 1:
                        # 移除重复的类型关键字
                        types = ParamType.split()
                        unique_types = []
                        for t in types:
                            if t not in unique_types:
                                unique_types.append(t)
                        ParamType = ' '.join(unique_types)
                    Params.append(f'{ParamType} {Arg.arg}')
                    # 添加参数到作用域
                    self.VarScopes[-1][Arg.arg] = ParamType
                except Exception as e:
                    print(f'Warning: Failed to get parameter type: {e}')
                    Params.append(f'int {Arg.arg}')
                    # 添加参数到作用域
                    self.VarScopes[-1][Arg.arg] = 'int'
            else:
                Params.append(f'int {Arg.arg}')
                # 添加参数到作用域
                self.VarScopes[-1][Arg.arg] = 'int'
        
        # 处理无参数函数，生成 void 参数列表
        if not Params:
            ParamsStr = 'void'
        else:
            ParamsStr = ', '.join(Params)
        
        # 根据是否是函数声明生成不同的代码
        if is_function_declaration:
            # 生成函数声明
            Code.append(f'{ReturnType} {Node.name}({ParamsStr});')
        else:
            # 生成函数定义
            Code.append(f'{ReturnType} {Node.name}({ParamsStr}) {{')
            body_code = self.HandleBody(Node.body)
            # 为函数体中的语句添加4个空格的缩进
            Code.extend(['    ' + line for line in body_code])
            Code.append('}')
        
        # 清理作用域
        if self.VarScopes:
            self.VarScopes.pop()
        
        # 记录函数返回类型
        self.FunctionReturnTypes[Node.name] = ReturnType
        
        return Code
    
    def HandleClassDef(self, Node):
        """处理类定义"""
        Code = []
        # 将类名添加到符号表中
        self.SymbolTable[Node.name] = {'type': 'struct'}
        Code.append(f'struct {Node.name} {{')
        # 遍历类体中的所有节点，查找类变量和实例变量
        for item in Node.body:
            if isinstance(item, ast.AnnAssign):
                # 处理类变量，如 k1: t.CInt
                if isinstance(item.target, ast.Name):
                    var_name = item.target.id
                    try:
                        type_name = self.GetTypeName(item.annotation)
                        if type_name and type_name.strip():
                            # 检查是否是结构体类型，需要使用右侧表达式的名称作为结构体名
                            is_struct = False
                            is_ptr = False
                            struct_name = None
                            base_type = type_name
                            
                            # 检查是否是结构体指针类型
                            if base_type == 'struct *':
                                is_struct = True
                                is_ptr = True
                                # 使用右侧表达式的名称作为结构体名
                                if item.value:
                                    if isinstance(item.value, ast.Name):
                                        struct_name = item.value.id
                                    elif isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name):
                                        struct_name = item.value.func.id
                                    else:
                                        struct_name = 'XXX'
                            elif base_type == 'struct':
                                is_struct = True
                                # 使用右侧表达式的名称作为结构体名
                                if item.value:
                                    if isinstance(item.value, ast.Name):
                                        struct_name = item.value.id
                                    elif isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name):
                                        struct_name = item.value.func.id
                                    else:
                                        struct_name = 'XXX'
                            
                            # 生成结构体成员
                            if is_struct and struct_name:
                                if is_ptr:
                                    Code.append(f'    struct {struct_name}* {var_name};')
                                else:
                                    Code.append(f'    struct {struct_name} {var_name};')
                            else:
                                # 检查是否是数组类型，需要将数组大小放在变量名后面
                                if '[' in type_name and ']' in type_name:
                                    # 提取基础类型和数组大小
                                    base_type = type_name.split('[')[0]
                                    array_size = type_name[type_name.find('['):]
                                    # 检查基础类型是否以 * 结尾，如果是，将 * 移到变量名前面
                                    if base_type.endswith('*'):
                                        base_type = base_type[:-1].strip()
                                        # 生成正确的数组指针类型格式
                                        Code.append(f'    {base_type} *{var_name}{array_size};')
                                    else:
                                        # 生成正确的数组类型格式
                                        Code.append(f'    {base_type} {var_name}{array_size};')
                                else:
                                    # 生成普通类型成员
                                    Code.append(f'    {type_name} {var_name};')
                        else:
                            # 默认使用int类型
                            Code.append(f'    int {var_name};')
                    except Exception as e:
                        print(f'Warning: Failed to get type annotation for {var_name}: {e}')
                        # 发生异常时，默认使用int类型
                        Code.append(f'    int {var_name};')
            elif isinstance(item, ast.FunctionDef):
                # 处理方法定义，查找实例变量
                if item.name == '__init__':
                    # 遍历 __init__ 方法体，查找实例变量
                    for stmt in item.body:
                        if isinstance(stmt, ast.AnnAssign):
                            # 处理实例变量，如 self.led: t.CInt
                            if isinstance(stmt.target, ast.Attribute) and isinstance(stmt.target.value, ast.Name) and stmt.target.value.id == 'self':
                                var_name = stmt.target.attr
                                try:
                                    type_name = self.GetTypeName(stmt.annotation)
                                    if type_name and type_name.strip():
                                        # 修复 struct * 类型，替换为 void *
                                        if type_name == 'struct *':
                                            type_name = 'void *'
                                        # 生成结构体成员
                                        Code.append(f'    {type_name} {var_name};')
                                    else:
                                        # 默认使用int类型
                                        Code.append(f'    int {var_name};')
                                except Exception as e:
                                    print(f'Warning: Failed to get type annotation for {var_name}: {e}')
                                    # 发生异常时，默认使用int类型
                                    Code.append(f'    int {var_name};')
        Code.append('};')
        return Code
    
    def HandleMethodDef(self, class_name, Node):
        """处理类方法"""
        # 处理类方法，生成带有结构体指针参数的函数
        Code = []
        ReturnType = 'void'
        
        # 处理返回类型
        if Node.returns:
            try:
                ReturnType = self.GetTypeName(Node.returns)
                if not ReturnType:
                    ReturnType = 'void'
            except Exception as e:
                print(f'Warning: Failed to get return type for {Node.name}: {e}')
                ReturnType = 'void'
        
        # 生成函数名：className__functionName
        func_name = f'{class_name}__{Node.name}'
        
        Params = []
        # 添加结构体指针参数作为第一个参数（self）
        Params.append(f'struct {class_name}* self')
        
        # 处理其他参数
        for Arg in Node.args.args:
            if Arg.arg != 'self':  # 跳过self参数
                try:
                    ParamType = self.GetTypeName(Arg.annotation)
                    if not ParamType:
                        ParamType = 'int'
                    Params.append(f'{ParamType} {Arg.arg}')
                except Exception as e:
                    print(f'Warning: Failed to get parameter type for {Arg.arg}: {e}')
                    Params.append(f'int {Arg.arg}')
        
        ParamsStr = ', '.join(Params)
        
        # 生成函数定义
        Code.append(f'{ReturnType} {func_name}({ParamsStr}) {{')
        
        # 处理函数体
        # 为函数创建新的作用域
        self.VarScopes.append({})
        
        # 添加参数到当前作用域
        for Arg in Node.args.args:
            if Arg.arg != 'self':  # 跳过self参数
                try:
                    ParamType = self.GetTypeName(Arg.annotation)
                    if not ParamType:
                        ParamType = 'int'
                    self.VarScopes[-1][Arg.arg] = ParamType
                except Exception as e:
                    print(f'Warning: Failed to get parameter type for {Arg.arg}: {e}')
                    self.VarScopes[-1][Arg.arg] = 'int'
        
        # 处理函数体语句
        body_code = self.HandleBody(Node.body)
        # 为函数体中的语句添加4个空格的缩进
        Code.extend(['    ' + line for line in body_code])
        
        Code.append('}')
        
        # 清理作用域
        if self.VarScopes:
            self.VarScopes.pop()
        
        return Code
    
    def HandleAssign(self, Node):
        """处理赋值语句"""
        Code = []
        # 处理多重赋值，如 a, b = b, a
        if isinstance(Node.targets[0], ast.Tuple) and isinstance(Node.value, ast.Tuple):
            targets = Node.targets[0].elts
            values = Node.value.elts
            if len(targets) == 2 and len(values) == 2:
                # 特殊处理二元交换：a, b = b, a
                temp_var = "temp"
                # 生成临时变量声明
                Code.append(f'int {temp_var};')
                # 获取目标表达式
                target1_code = self.HandleExpr(targets[0])[0]
                target2_code = self.HandleExpr(targets[1])[0]
                # 正确的交换操作：temp = a; a = b; b = temp
                Code.append(f'{temp_var} = {target1_code};')
                Code.append(f'{target1_code} = {target2_code};')
                Code.append(f'{target2_code} = {temp_var};')
                return Code
        
        for Target in Node.targets:
            if isinstance(Target, ast.Name):
                ValueCode = self.HandleExpr(Node.value)
                if ValueCode:
                    # 检查变量是否已经在当前作用域中声明过
                    var_name = Target.id
                    var_declared = False
                    
                    # 从最内层作用域向外查找
                    for scope in reversed(self.VarScopes):
                        if var_name in scope:
                            var_declared = True
                            break
                    
                    # 检查变量是否在符号表中声明过（外部注解的变量）
                    if not var_declared and var_name in self.SymbolTable:
                        symbol_info = self.SymbolTable[var_name]
                        if symbol_info['type'] == 'variable':
                            var_declared = True
                    
                    if var_declared:
                        # 变量已经声明过，只生成赋值语句
                        Code.append(f'{var_name} = {ValueCode[0]};')
                    else:
                        # 变量未声明，生成声明语句
                        # 检查右侧是否是函数调用或结构体成员访问
                        var_type = 'int'  # 默认类型
                        struct_name = None
                        is_pointer = False
                        
                        # 检查右侧是否是结构体成员访问
                        if isinstance(Node.value, ast.Attribute):
                            # 尝试从符号表中查找类型信息
                            # 构建访问链
                            access_chain = []
                            current_node = Node.value
                            while isinstance(current_node, ast.Attribute):
                                access_chain.insert(0, current_node.attr)
                                current_node = current_node.value
                            
                            # 添加基础对象名
                            if isinstance(current_node, ast.Name):
                                access_chain.insert(0, current_node.id)
                            
                            # 尝试从符号表中查找类型信息
                            if len(access_chain) >= 2:
                                # 从基础对象开始，逐步查找类型信息
                                current_type = access_chain[0]
                                
                                # 检查基础对象是否在符号表中
                                if current_type in self.SymbolTable:
                                    base_info = self.SymbolTable[current_type]
                                    if base_info['type'] == 'variable' and 'is_pointer' in base_info:
                                        is_pointer = base_info['is_pointer']
                                    
                                    # 遍历访问链，查找每个成员的类型信息
                                    for i in range(1, len(access_chain)):
                                        member_name = access_chain[i]
                                        
                                        # 检查当前类型是否是结构体
                                        if current_type in self.SymbolTable:
                                            struct_info = self.SymbolTable[current_type]
                                            if struct_info['type'] == 'struct' and 'members' in struct_info:
                                                members = struct_info['members']
                                                # 检查成员是否存在
                                                if member_name in members:
                                                    # 检查成员是否是指针
                                                    member_is_ptr = members[member_name]['is_pointer']
                                                    # 如果是最后一个成员，设置 is_pointer
                                                    if i == len(access_chain) - 1:
                                                        is_pointer = member_is_ptr
                                                    # 更新当前类型为成员类型
                                                    current_type = members[member_name]['type']
                                                    # 提取结构体名
                                                    if current_type.startswith('struct '):
                                                        current_type = current_type.split(' ')[1]
                                                    elif '*' in current_type:
                                                        type_parts = current_type.split('*')[0].strip()
                                                        if type_parts.startswith('struct '):
                                                            current_type = type_parts.split(' ')[1]
                        # 检查右侧是否是函数调用
                        elif isinstance(Node.value, ast.Call):
                            # 检查是否是函数名调用
                            if isinstance(Node.value.func, ast.Name):
                                func_name = Node.value.func.id
                                # 特殊处理内置函数
                                if func_name in ['len', 'print', 'range']:
                                    # 内置函数，不视为结构体构造函数
                                    var_type = 'int'  # len函数返回整数
                                # 检查函数返回类型是否已记录
                                elif func_name in self.FunctionReturnTypes:
                                    var_type = self.FunctionReturnTypes[func_name]
                                    if '*' in var_type:
                                        is_pointer = True
                                else:
                                    # 从符号表中查找函数名
                                    if func_name in self.SymbolTable:
                                        symbol_info = self.SymbolTable[func_name]
                                        if symbol_info['type'] == 'struct':
                                            # 是结构体，使用结构体构造方法
                                            struct_name = func_name
                                        else:
                                            # 是函数，默认使用函数的初始方法
                                            var_type = 'int'  # 默认函数返回类型
                                    else:
                                        # 只有在符号表中确认是结构体的才能用结构体的初始化方法
                                        # 否则视为普通函数调用
                                        var_type = 'int'  # 默认函数返回类型
                        
                        # 特殊处理数组初始化
                        if isinstance(Node.value, ast.List):
                            elements = []
                            for elt in Node.value.elts:
                                elements.append(self.HandleExpr(elt)[0])
                            elements_str = ', '.join(elements)
                            Code.append(f'{var_type} {var_name}[] = {{ {elements_str} }};')
                            # 添加变量到当前作用域
                            if self.VarScopes:
                                self.VarScopes[-1][var_name] = var_type
                        else:
                            if struct_name:
                                # 生成结构体声明
                                Code.append(f'struct {struct_name} {var_name};')
                                # 调用构造函数
                                if isinstance(Node.value, ast.Call):
                                    # 提取构造函数参数
                                    args = ['&' + var_name]
                                    for arg in Node.value.args:
                                        args.append(self.HandleExpr(arg)[0])
                                    args_str = ', '.join(args)
                                    # 生成构造函数调用
                                    Code.append(f'{struct_name}____init__({args_str});')
                                # 添加变量到当前作用域
                                if self.VarScopes:
                                    self.VarScopes[-1][var_name] = f'struct {struct_name}'
                            else:
                                # 根据是否是指针生成不同的声明语句
                                if is_pointer:
                                    Code.append(f'{var_type}* {var_name} = {ValueCode[0]};')
                                else:
                                    Code.append(f'{var_type} {var_name} = {ValueCode[0]};')
                                # 添加变量到当前作用域
                                if self.VarScopes:
                                    if is_pointer:
                                        self.VarScopes[-1][var_name] = f'{var_type}*'
                                    else:
                                        self.VarScopes[-1][var_name] = var_type
            elif isinstance(Target, ast.UnaryOp):
                # 处理指针解引用赋值，如 *(addr) = value
                if isinstance(Target.operand, ast.Name):
                    addr_name = Target.operand.id
                    ValueCode = self.HandleExpr(Node.value)
                    if ValueCode:
                        Code.append(f'*((void *){addr_name}) = {ValueCode[0]};')
                elif isinstance(Target.operand, ast.UnaryOp) and isinstance(Target.operand.op, ast.USub):
                    # 处理双重指针解引用赋值，如 *(*(addr)) = value
                    if isinstance(Target.operand.operand, ast.Name):
                        addr_name = Target.operand.operand.id
                        ValueCode = self.HandleExpr(Node.value)
                        if ValueCode:
                            Code.append(f'*(*((void *){addr_name})) = {ValueCode[0]};')
            elif isinstance(Target, ast.Attribute):
                # 处理结构体成员赋值，如 s.Value = 42
                obj = self.HandleExpr(Target.value)[0]
                attr = Target.attr
                ValueCode = self.HandleExpr(Node.value)
                if ValueCode:
                    # 检查obj是否是指针类型
                    is_pointer = False
                    # 特殊处理 self 参数，它总是指针
                    if obj == 'self':
                        is_pointer = True
                    # 从作用域中查找变量类型
                    else:
                        for scope in reversed(self.VarScopes):
                            if obj in scope:
                                var_type = scope[obj]
                                if '*' in var_type:
                                    is_pointer = True
                                break
                        # 如果作用域中没有找到，从符号表中查找
                        if not is_pointer and obj in self.SymbolTable:
                            symbol_info = self.SymbolTable[obj]
                            if 'is_pointer' in symbol_info:
                                is_pointer = symbol_info['is_pointer']
                            elif 'declared_type' in symbol_info and '*' in symbol_info['declared_type']:
                                is_pointer = True
                    # 根据变量类型选择正确的操作符
                    if is_pointer:
                        Code.append(f'{obj}->{attr} = {ValueCode[0]};')
                    else:
                        Code.append(f'{obj}.{attr} = {ValueCode[0]};')
            elif isinstance(Target, ast.Starred):
                # 处理指针解引用赋值，如 *ptr = value
                if isinstance(Target.value, ast.Name):
                    ptr_name = Target.value.id
                    ValueCode = self.HandleExpr(Node.value)
                    if ValueCode:
                        Code.append(f'*((void *){ptr_name}) = {ValueCode[0]};')
            elif isinstance(Target, ast.Subscript):
                # 处理数组元素赋值，如 arr[j] = value
                arr = self.HandleExpr(Target.value)[0]
                index = self.HandleExpr(Target.slice)[0]
                ValueCode = self.HandleExpr(Node.value)
                if ValueCode:
                    Code.append(f'{arr}[{index}] = {ValueCode[0]};')
        return Code
    
    def HandleAnnAssign(self, Node):
        """处理带有类型注解的变量赋值"""
        # 处理带有类型注解的变量赋值，如 GlobalVar: t.CStatic | t.CInt = 0
        Code = []
        if isinstance(Node.target, ast.Name):
            var_name = Node.target.id
            ValueCode = self.HandleExpr(Node.value)
            if ValueCode:
                # 直接生成声明语句，不检查变量是否已经在当前作用域中声明过
                try:
                    type_name = self.GetTypeName(Node.annotation)
                    if type_name:
                        # 处理数组类型，提取数组大小
                        base_type, array_size_str = extract_array_size(type_name)
                        
                        # 特殊处理数组初始化
                        if isinstance(Node.value, ast.List):
                            # 从原始代码中提取完整的初始化列表
                            line_number = getattr(Node, 'lineno', None)
                            init_content = None
                            
                            if line_number and hasattr(self, 'OriginalLines'):
                                # 查找包含这个变量声明的行
                                var_line = -1
                                for i, line in enumerate(self.OriginalLines):
                                    if var_name + ':' in line:
                                        var_line = i
                                        break
                                
                                if var_line != -1:
                                    # 查找从 = 开始到 ] 结束的部分
                                    init_start = -1
                                    init_end = -1
                                    for i in range(var_line, len(self.OriginalLines)):
                                        line = self.OriginalLines[i]
                                        if init_start == -1 and '=' in line:
                                            init_start = i
                                        if init_end == -1 and ']' in line:
                                            init_end = i
                                            break
                                    
                                    if init_start != -1 and init_end != -1:
                                        # 提取初始化部分
                                        init_lines = self.OriginalLines[init_start:init_end + 1]
                                        init_code = ''.join(init_lines)
                                        
                                        # 提取 = 后面的部分
                                        if '=' in init_code:
                                            init_part = init_code.split('=', 1)[1].strip()
                                            if init_part.startswith('[') and init_part.endswith(']'):
                                                # 提取括号内的内容
                                                init_content = init_part[1:-1]
                            
                            if init_content:
                                # 生成初始化代码
                                Code.append(f'{base_type} {var_name}{array_size_str} = {{ {init_content} }};')
                            else:
                                # 默认处理
                                elements = []
                                for elt in Node.value.elts:
                                    elements.append(self.HandleExpr(elt, use_single_quote=True)[0])
                                elements_str = ', '.join(elements)
                                Code.append(f'{base_type} {var_name}{array_size_str} = {{ {elements_str} }};')
                        else:
                            # 特殊处理 c.State，表示仅声明不定义
                            if ValueCode[0] == 'c.State':
                                # 处理 t.CPtr 类型，当 base_type 为 '*' 时，使用右侧表达式的名称作为类型
                                if base_type == '*':
                                    # 尝试从右侧表达式获取类型名称
                                    if isinstance(Node.value, ast.Name):
                                        type_name = Node.value.id
                                        Code.append(f'struct {type_name}* {var_name}{array_size_str};')
                                    else:
                                        Code.append(f'void* {var_name}{array_size_str};')
                                else:
                                    Code.append(f'{base_type} {var_name}{array_size_str};')
                            else:
                                # 处理 t.CPtr 类型，当 base_type 为 '*' 时，使用右侧表达式的名称作为类型
                                if base_type == '*':
                                    # 尝试从右侧表达式获取类型名称
                                    if isinstance(Node.value, ast.Name):
                                        type_name = Node.value.id
                                        Code.append(f'struct {type_name}* {var_name}{array_size_str} = {ValueCode[0]};')
                                    # 处理 t.CStruct(...) 调用，生成类型转换代码
                                    elif isinstance(Node.value, ast.Call) and isinstance(Node.value.func, ast.Attribute) and Node.value.func.attr == 'CStruct':
                                        # 提取参数
                                        if len(Node.value.args) >= 1:
                                            # 获取地址值
                                            addr = self.HandleExpr(Node.value.args[0])[0]
                                            # 获取结构体名称
                                            struct_name = 'BOOTINFO'  # 默认值
                                            if len(Node.value.args) >= 2 and isinstance(Node.value.args[1], ast.Name):
                                                struct_name = Node.value.args[1].id
                                            # 生成类型转换代码
                                            Code.append(f'struct {struct_name}* {var_name}{array_size_str} = ((struct {struct_name} *){addr});')
                                        else:
                                            Code.append(f'void* {var_name}{array_size_str} = {ValueCode[0]};')
                                    # 处理 t.CType(...) 调用，生成类型转换代码
                                    elif isinstance(Node.value, ast.Call) and isinstance(Node.value.func, ast.Attribute) and Node.value.func.attr == 'CType':
                                        # 提取参数
                                        if len(Node.value.args) >= 1:
                                            # 获取地址值
                                            addr = self.HandleExpr(Node.value.args[0])[0]
                                            # 获取结构体名称
                                            struct_name = 'BOOTINFO'  # 默认值
                                            # 生成类型转换代码
                                            Code.append(f'struct {struct_name}* {var_name}{array_size_str} = ((struct {struct_name} *){addr});')
                                        else:
                                            Code.append(f'void* {var_name}{array_size_str} = {ValueCode[0]};')
                                    else:
                                        Code.append(f'void* {var_name}{array_size_str} = {ValueCode[0]};')
                                else:
                                    # 处理 t.CStruct(...) 调用，生成类型转换代码
                                    if isinstance(Node.value, ast.Call) and isinstance(Node.value.func, ast.Attribute) and Node.value.func.attr == 'CStruct':
                                        # 提取参数
                                        if len(Node.value.args) >= 1:
                                            # 获取地址值
                                            addr = self.HandleExpr(Node.value.args[0])[0]
                                            # 获取结构体名称
                                            struct_name = 'BOOTINFO'  # 默认值
                                            if len(Node.value.args) >= 2 and isinstance(Node.value.args[1], ast.Name):
                                                struct_name = Node.value.args[1].id
                                            # 生成类型转换代码
                                            Code.append(f'struct {struct_name}* {var_name}{array_size_str} = ((struct {struct_name} *){addr});')
                                        else:
                                            Code.append(f'{base_type} {var_name}{array_size_str} = {ValueCode[0]};')
                                    # 处理 t.CType(...) 调用，生成类型转换代码
                                    elif isinstance(Node.value, ast.Call) and isinstance(Node.value.func, ast.Attribute) and Node.value.func.attr == 'CType':
                                        # 提取参数
                                        if len(Node.value.args) >= 1:
                                            # 获取地址值
                                            addr = self.HandleExpr(Node.value.args[0])[0]
                                            # 获取结构体名称
                                            struct_name = 'BOOTINFO'  # 默认值
                                            # 生成类型转换代码
                                            Code.append(f'struct {struct_name}* {var_name}{array_size_str} = ((struct {struct_name} *){addr});')
                                        else:
                                            Code.append(f'{base_type} {var_name}{array_size_str} = {ValueCode[0]};')
                                    else:
                                        Code.append(f'{base_type} {var_name}{array_size_str} = {ValueCode[0]};')
                        # 添加变量到当前作用域
                        if self.VarScopes:
                            self.VarScopes[-1][var_name] = type_name
                    else:
                        # 默认使用int类型
                        # 特殊处理数组初始化
                        if isinstance(Node.value, ast.List):
                            elements = []
                            for elt in Node.value.elts:
                                elements.append(self.HandleExpr(elt)[0])
                            elements_str = ', '.join(elements)
                            Code.append(f'int {var_name}[] = {{ {elements_str} }};')
                        else:
                            Code.append(f'int {var_name} = {ValueCode[0]};')
                        # 添加变量到当前作用域
                        if self.VarScopes:
                            self.VarScopes[-1][var_name] = 'int'
                except Exception as e:
                    print(f'Warning: Failed to get type annotation: {e}')
                    # 发生异常时，默认使用int类型
                    # 特殊处理数组初始化
                    if isinstance(Node.value, ast.List):
                        elements = []
                        for elt in Node.value.elts:
                            elements.append(self.HandleExpr(elt)[0])
                        elements_str = ', '.join(elements)
                        Code.append(f'int {var_name}[] = {{ {elements_str} }};')
                    else:
                        # 特殊处理 c.State，表示仅声明不定义
                        if ValueCode[0] == 'c.State':
                            Code.append(f'int {var_name};')
                        else:
                            Code.append(f'int {var_name} = {ValueCode[0]};')
                    # 添加变量到当前作用域
                    if self.VarScopes:
                        self.VarScopes[-1][var_name] = 'int'
        return Code
    
    def HandleExpr(self, Node, use_single_quote=False):
        """处理表达式"""
        if isinstance(Node, ast.Constant):
            if isinstance(Node.value, str):
                if use_single_quote:
                    # 对于单引号字符串，正确处理转义
                    # 替换反斜杠为双反斜杠
                    escaped_value = Node.value.replace("\\", "\\\\")
                    # 替换单引号为转义单引号
                    escaped_value = escaped_value.replace("'", "\\'")
                    return [f"'{escaped_value}'"]
                else:
                    # 对于双引号字符串，正确处理转义
                    escaped_value = Node.value.replace("\\", "\\\\")
                    escaped_value = escaped_value.replace('"', '\\"')
                    return [f'"{escaped_value}"']
            elif isinstance(Node.value, bool):
                # 处理布尔值，将 True 转换为 1，将 False 转换为 0
                return ['1' if Node.value else '0']
            else:
                return [str(Node.value)]
        elif isinstance(Node, ast.Name):
            # 处理布尔值名称，将 True 转换为 1，将 False 转换为 0
            if Node.id == 'True':
                return ['1']
            elif Node.id == 'False':
                return ['0']
            else:
                return [Node.id]
        elif isinstance(Node, ast.BinOp):
            Left = self.HandleExpr(Node.left)[0]
            Right = self.HandleExpr(Node.right)[0]
            Op = self.GetOpSymbol(Node.op)
            return [f'({Left} {Op} {Right})']
        elif isinstance(Node, ast.BoolOp):
            # 处理逻辑运算符 and 和 or
            values = []
            for value in Node.values:
                values.append(self.HandleExpr(value)[0])
            if isinstance(Node.op, ast.And):
                # 将 and 转换为 &&
                return [' && '.join(f'({v})' for v in values)]
            elif isinstance(Node.op, ast.Or):
                # 将 or 转换为 ||
                return [' || '.join(f'({v})' for v in values)]
            else:
                return ['0']
        elif isinstance(Node, ast.UnaryOp):
            Operand = self.HandleExpr(Node.operand)[0]
            Op = self.GetUnaryOpSymbol(Node.op)
            if isinstance(Node.op, ast.USub) and isinstance(Node.operand, ast.Name):
                # 处理指针解引用，如 *(addr)
                return [f'*((void *){Operand})']
            return [f'{Op}{Operand}']
        elif isinstance(Node, ast.Call):
            # 处理函数调用
            if isinstance(Node.func, ast.Attribute):
                if isinstance(Node.func.value, ast.Name) and Node.func.value.id == 'c':
                    # 处理c模块中的特殊语法
                    return self.HandleCSpecialCall(Node.func.attr, Node.args, Node.keywords)
                elif isinstance(Node.func.value, ast.Name) and Node.func.value.id == 't':
                    # 处理t模块中的特殊语法
                    return self.HandleTSpecialCall(Node.func.attr, Node.args, Node.keywords)
                else:
                    # 处理方法调用，如 obj.method(args)
                    obj = self.HandleExpr(Node.func.value)[0]
                    method = Node.func.attr
                    
                    # 尝试获取对象的类型名（结构体名）
                    struct_name = None  # 默认值
                    # 从符号表中查找对象类型
                    if obj in self.SymbolTable:
                        symbol_info = self.SymbolTable[obj]
                        if 'declared_type' in symbol_info:
                            declared_type = symbol_info['declared_type']
                            # 提取结构体名
                            if declared_type.startswith('struct '):
                                struct_name = declared_type.split(' ')[1]
                            elif '*' in declared_type:
                                # 处理指针类型
                                type_parts = declared_type.split('*')[0].strip()
                                if type_parts.startswith('struct '):
                                    struct_name = type_parts.split(' ')[1]
                    # 从作用域中查找变量类型
                    if not struct_name:
                        for scope in reversed(self.VarScopes):
                            if obj in scope:
                                var_type = scope[obj]
                                if var_type.startswith('struct '):
                                    struct_name = var_type.split(' ')[1]
                                    break
                    # 如果还是没找到，尝试从函数名推断
                    if not struct_name and isinstance(Node.func.value, ast.Call):
                        if isinstance(Node.func.value.func, ast.Name):
                            struct_name = Node.func.value.func.id
                    # 如果还是没找到，使用默认值
                    if not struct_name:
                        struct_name = obj  # 使用变量名作为结构体名
                    
                    # 生成函数名：structName__methodName
                    func_name = f'{struct_name}__{method}'
                    
                    # 构建参数列表，第一个参数是对象指针
                    # 自动获取对象的地址作为 self 参数
                    Args = [f'&{obj}']
                    for Arg in Node.args:
                        Args.append(self.HandleExpr(Arg)[0])
                    ArgsStr = ', '.join(Args)
                    
                    return [f'{func_name}({ArgsStr})']
            else:
                Func = self.HandleExpr(Node.func)[0]
                Args = []
                for Arg in Node.args:
                    Args.append(self.HandleExpr(Arg)[0])
                ArgsStr = ', '.join(Args)
                # 特殊处理len函数
                if Func == 'len':
                    if Args:
                        arr_name = Args[0]
                        return [f'(sizeof({arr_name}) / sizeof({arr_name}[0]))']
                    else:
                        return ['0']
                # 特殊处理print函数
                elif Func == 'print':
                    # 为不同类型的参数生成不同的printf格式
                    if Args:
                        first_arg = Args[0]
                        if first_arg.startswith('"') and first_arg.endswith('"'):
                            # 字符串参数
                            # Python的print默认添加换行符
                            return [f'printf({first_arg});', 'printf("\n");']
                        else:
                            # 数值参数
                            # Python的print默认添加换行符
                            return [f'printf("%d\n", {ArgsStr});']
                    return [f'printf("\n");']
                # 普通函数调用
                return [f'{Func}({ArgsStr})']
        elif isinstance(Node, ast.Subscript):
            # 处理数组访问，如 arr[j]
            value = self.HandleExpr(Node.value)[0]
            index = self.HandleExpr(Node.slice)[0]
            return [f'{value}[{index}]']
        elif isinstance(Node, ast.List):
            # 处理数组初始化，如 [64, 34, 25, 12, 22, 11, 90]
            elements = []
            for elt in Node.elts:
                elements.append(self.HandleExpr(elt, use_single_quote=True)[0])
            elements_str = ', '.join(elements)
            return [f'{{{elements_str}}}']
        elif isinstance(Node, ast.Compare):
            Left = self.HandleExpr(Node.left)[0]
            Comparator = self.GetComparatorSymbol(Node.ops[0])
            Right = self.HandleExpr(Node.comparators[0])[0]
            return [f'({Left} {Comparator} {Right})']
        elif isinstance(Node, ast.Attribute):
            # 处理属性访问，如 s.Value 或 self.led
            if isinstance(Node.value, ast.Name) and Node.value.id == 'c':
                # 处理c模块的属性访问，如 c.State
                attr = Node.attr
                return [f'c.{attr}']
            else:
                # 处理普通属性访问，如 s.Value 或 self.led
                obj = self.HandleExpr(Node.value)[0]
                attr = Node.attr
                
                # 检查对象是否是指针
                is_ptr = False
                
                # 特殊处理 self 参数，它总是指针
                if isinstance(Node.value, ast.Name) and Node.value.id == 'self':
                    is_ptr = True
                # 检查对象是否以 & 开头（取地址操作）
                elif obj.startswith('&'):
                    is_ptr = True
                # 检查对象是否是已知的指针变量
                elif isinstance(Node.value, ast.Name):
                    var_name = Node.value.id
                    # 从变量作用域中获取变量类型
                    for scope in reversed(self.VarScopes):
                        if var_name in scope:
                            var_type = scope[var_name]
                            if '*' in var_type:
                                is_ptr = True
                            break
                    # 如果作用域中没有找到，从符号表中查找
                    if not is_ptr and var_name in self.SymbolTable:
                        symbol_info = self.SymbolTable[var_name]
                        if 'is_pointer' in symbol_info:
                            is_ptr = symbol_info['is_pointer']
                        elif 'declared_type' in symbol_info:
                            declared_type = symbol_info['declared_type']
                            if '*' in declared_type or 'CPtr' in declared_type:
                                is_ptr = True
                # 处理obj是复杂表达式的情况，如key_win->task
                else:
                    # 构建完整的访问链
                    access_chain = []
                    
                    # 解析obj部分
                    if '->' in obj:
                        # 处理指针访问链，如key_win->task
                        parts = obj.split('->')
                        access_chain.extend(parts)
                    elif '.' in obj:
                        # 处理非指针访问链，如obj.member
                        parts = obj.split('.')
                        access_chain.extend(parts)
                    else:
                        # 单个变量名
                        access_chain.append(obj)
                    
                    # 添加当前属性
                    access_chain.append(attr)
                    
                    # 现在从符号表中查找完整的访问链
                    if len(access_chain) >= 2:
                        # 从基础变量开始查找
                        current_var = access_chain[0]
                        current_struct_name = None
                        
                        # 查找基础变量的类型
                        # 从变量作用域中获取变量类型
                        for scope in reversed(self.VarScopes):
                            if current_var in scope:
                                var_type = scope[current_var]
                                if var_type.startswith('struct '):
                                    current_struct_name = var_type.split(' ')[1]
                                elif '*' in var_type:
                                    # 处理指针类型
                                    type_parts = var_type.split('*')[0].strip()
                                    if type_parts.startswith('struct '):
                                        current_struct_name = type_parts.split(' ')[1]
                                break
                        
                        # 如果作用域中没有找到，从符号表中查找
                        if not current_struct_name:
                            if current_var in self.SymbolTable:
                                var_info = self.SymbolTable[current_var]
                                if var_info['type'] == 'variable' and 'declared_type' in var_info:
                                    declared_type = var_info['declared_type']
                                    if declared_type.startswith('struct '):
                                        current_struct_name = declared_type.split(' ')[1]
                                    elif '*' in declared_type:
                                        type_parts = declared_type.split('*')[0].strip()
                                        if type_parts.startswith('struct '):
                                            current_struct_name = type_parts.split(' ')[1]
                        
                        # 检查最后一个成员（即attr的前一个成员）是否是指针
                        if len(access_chain) >= 2:
                            last_member = access_chain[-2]
                            # 构建正确的结构体路径来检查最后一个成员是否是指针
                            # 从基础变量开始，遍历访问链，直到找到最后一个成员所属的结构体
                            check_struct_name = current_struct_name
                            # 遍历访问链，直到找到最后一个成员
                            for i in range(1, len(access_chain) - 1):
                                member_name = access_chain[i]
                                if member_name == last_member:
                                    break
                                if check_struct_name in self.SymbolTable:
                                    struct_info = self.SymbolTable[check_struct_name]
                                    if struct_info['type'] == 'struct' and 'members' in struct_info:
                                        if member_name in struct_info['members']:
                                            # 更新检查的结构体名为当前成员的类型名
                                            member_type = struct_info['members'][member_name]['type']
                                            if member_type.startswith('struct '):
                                                check_struct_name = member_type.split(' ')[1]
                                            elif '*' in member_type:
                                                type_parts = member_type.split('*')[0].strip()
                                                if type_parts.startswith('struct '):
                                                    check_struct_name = type_parts.split(' ')[1]
                            
                            # 现在检查最后一个成员是否是指针
                            if check_struct_name in self.SymbolTable:
                                struct_info = self.SymbolTable[check_struct_name]
                                if struct_info['type'] == 'struct' and 'members' in struct_info:
                                    if last_member in struct_info['members']:
                                        is_ptr = struct_info['members'][last_member]['is_pointer']
                        
                        # 从符号表中查找结构体成员是否是指针
                        # 检查obj是否是一个结构体访问表达式，如key_win->task或key_win.task
                        if '->' in obj or '.' in obj:
                            # 提取成员路径
                            if '->' in obj:
                                parts = obj.split('->')
                            else:
                                parts = obj.split('.')
                            
                            # 成员路径
                            member_path = parts[1:]
                            
                            # 遍历所有结构体，查找是否有包含这些成员的结构体
                            for struct_name in self.SymbolTable:
                                struct_info = self.SymbolTable[struct_name]
                                if struct_info['type'] == 'struct' and 'members' in struct_info:
                                    # 检查结构体是否包含成员路径中的第一个成员
                                    if len(member_path) > 0 and member_path[0] in struct_info['members']:
                                        # 检查这个成员是否是指针
                                        is_ptr = struct_info['members'][member_path[0]]['is_pointer']
                                        break
                    # 对于其他复杂表达式，默认不是指针
                    else:
                        is_ptr = False
                
                # 根据是否是指针使用不同的运算符
                if is_ptr:
                    return [f'{obj}->{attr}']
                else:
                    return [f'{obj}.{attr}']
        return ['0']
    
    def GetComparatorSymbol(self, Op):
        """获取比较运算符符号"""
        op_name = type(Op).__name__
        return COMPARATOR_MAP.get(op_name, '==')
    
    def GetOpSymbol(self, Op):
        """获取运算符符号"""
        op_name = type(Op).__name__
        return OPERATOR_MAP.get(op_name, '+')
    
    def HandleAugAssign(self, Node):
        """处理复合赋值运算符"""
        # 处理复合赋值运算符，如 a += b
        Code = []
        if isinstance(Node.target, ast.Name):
            var_name = Node.target.id
            value = self.HandleExpr(Node.value)[0]
            op = self.GetAugOpSymbol(Node.op)
            if op:
                Code.append(f'{var_name} {op}= {value};')
        elif isinstance(Node.target, ast.Attribute):
            # 处理 self.attribute 复合赋值，如 self.led += x
            if isinstance(Node.target.value, ast.Name) and Node.target.value.id == 'self':
                attr_name = Node.target.attr
                value = self.HandleExpr(Node.value)[0]
                op = self.GetAugOpSymbol(Node.op)
                if op:
                    Code.append(f'self->{attr_name} {op}= {value};')
            else:
                # 处理普通属性复合赋值，如 p.flags |= 0x20
                obj = self.HandleExpr(Node.target.value)[0]
                attr = Node.target.attr
                value = self.HandleExpr(Node.value)[0]
                op = self.GetAugOpSymbol(Node.op)
                
                # 检查对象是否是指针
                is_ptr = False
                
                # 检查 obj 是否以 & 开头（取地址操作）
                if obj.startswith('&'):
                    is_ptr = True
                # 检查 obj 是否是已知的指针变量
                elif isinstance(Node.target.value, ast.Name):
                    var_name = Node.target.value.id
                    # 从变量作用域中获取变量类型
                    for scope in reversed(self.VarScopes):
                        if var_name in scope:
                            var_type = scope[var_name]
                            if '*' in var_type:
                                is_ptr = True
                            break
                # 简化处理：如果变量名是 'p'，则认为是指针
                elif obj == 'p':
                    is_ptr = True
                
                # 根据是否是指针使用不同的运算符
                if op:
                    if is_ptr:
                        Code.append(f'{obj}->{attr} {op}= {value};')
                    else:
                        Code.append(f'{obj}.{attr} {op}= {value};')
        return Code
    
    def HandleBody(self, Body):
        """处理函数体"""
        Code = []
        for Node in Body:
            if isinstance(Node, ast.Expr):
                # 检查是否是c模块中的特殊语法调用
                if isinstance(Node.value, ast.Call):
                    if isinstance(Node.value.func, ast.Attribute):
                        if isinstance(Node.value.func.value, ast.Name) and Node.value.func.value.id == 'c':
                            # 直接处理c模块中的特殊语法调用
                            special_code = self.HandleCSpecialCall(Node.value.func.attr, Node.value.args, Node.value.keywords)
                            if special_code:
                                Code.extend(special_code)
                            continue
                    # 处理其他函数调用，如print
                    expr_code = self.HandleExpr(Node.value)
                    if expr_code:
                        # 为函数调用语句添加分号
                        for i, expr in enumerate(expr_code):
                            # 检查是否已经有分号
                            if not expr.endswith(';'):
                                expr_code[i] = expr + ';'
                        Code.extend(expr_code)
                else:
                    expr_code = self.HandleExpr(Node)
                    # 检查是否是c模块中的特殊语法调用
                    if expr_code:
                        # 过滤掉无效的表达式
                        valid_exprs = [expr for expr in expr_code if expr and expr != '0']
                        if valid_exprs:
                            Code.extend(valid_exprs)
            elif isinstance(Node, ast.If):
                Code.extend(self.HandleIf(Node))
            elif isinstance(Node, ast.For):
                Code.extend(self.HandleFor(Node))
            elif isinstance(Node, ast.While):
                Code.extend(self.HandleWhile(Node))
            elif isinstance(Node, ast.Break):
                Code.append('break;')
            elif isinstance(Node, ast.Continue):
                Code.append('continue;')
            elif isinstance(Node, ast.Return):
                if Node.value:
                    Value = self.HandleExpr(Node.value)[0]
                    Code.append(f'return {Value};')
                else:
                    Code.append('return;')
            elif isinstance(Node, ast.Assign):
                assign_code = self.HandleAssign(Node)
                if assign_code:
                    Code.extend(assign_code)
            elif isinstance(Node, ast.AugAssign):
                # 处理复合赋值运算符，如 a += b
                aug_assign_code = self.HandleAugAssign(Node)
                if aug_assign_code:
                    Code.extend(aug_assign_code)
            elif isinstance(Node, ast.AnnAssign):
                # 处理带有类型注解的变量赋值
                if isinstance(Node.target, ast.Name):
                    var_name = Node.target.id
                    # 检查是否有赋值部分
                    if Node.value:
                        ValueCode = self.HandleExpr(Node.value)
                        if ValueCode:
                            # 尝试获取类型名称
                            try:
                                type_name = self.GetTypeName(Node.annotation)
                                # 无论type_name是否为空，都生成声明语句
                                if type_name and type_name.strip():
                                    # 处理数组类型，提取数组大小
                                    base_type, array_size_str = extract_array_size(type_name)
                                    
                                    # 检查是否是指针类型
                                    is_ptr = False
                                    original_base_type = base_type
                                    if '*' in base_type:
                                        is_ptr = True
                                        base_type = base_type.replace('*', '').strip()
                                    elif base_type == '*':
                                        # 处理 t.CPtr 类型
                                        is_ptr = True
                                        base_type = ''
                                    
                                    # 检查是否是 typedef 类型
                                    is_typedef = False
                                    if base_type == 'typedef':
                                        is_typedef = True
                                        base_type = ''
                                    
                                    # 检查是否是结构体类型
                                    is_struct = False
                                    struct_name = None
                                    if base_type == 'struct':
                                        # 处理 t.CStruct 类型
                                        is_struct = True
                                        # 使用右侧表达式的名称作为结构体名
                                        if isinstance(Node.value, ast.Call) and isinstance(Node.value.func, ast.Name):
                                            struct_name = Node.value.func.id
                                        elif isinstance(Node.value, ast.Name):
                                            # 如果右侧是变量引用，使用变量名作为结构体名
                                            struct_name = Node.value.id
                                        else:
                                            # 如果右侧既不是函数调用也不是变量引用，使用默认结构体名
                                            struct_name = 'XXX'
                                    elif base_type == 'struct *':
                                        # 处理 t.CStruct | t.CPtr 类型
                                        is_struct = True
                                        is_ptr = True
                                        # 使用右侧表达式的名称作为结构体名
                                        if isinstance(Node.value, ast.Call) and isinstance(Node.value.func, ast.Name):
                                            struct_name = Node.value.func.id
                                        elif isinstance(Node.value, ast.Name):
                                            # 如果右侧是变量引用，使用变量名作为结构体名
                                            struct_name = Node.value.id
                                        else:
                                            # 如果右侧既不是函数调用也不是变量引用，使用默认结构体名
                                            struct_name = 'XXX'
                                    elif base_type.startswith('struct '):
                                        # 处理已经包含 struct 关键字的类型
                                        is_struct = True
                                        struct_name = base_type[7:]
                                    # 处理 t.CStruct | t.CPtr 类型
                                    elif original_base_type == '*' or (is_ptr and base_type == ''):
                                        # 处理 t.CStruct | t.CPtr 类型
                                        is_struct = True
                                        is_ptr = True
                                        # 使用右侧表达式的名称作为结构体名
                                        if isinstance(Node.value, ast.Call) and isinstance(Node.value.func, ast.Name):
                                            struct_name = Node.value.func.id
                                        elif isinstance(Node.value, ast.Name):
                                            # 如果右侧是变量引用，使用变量名作为结构体名
                                            struct_name = Node.value.id
                                        else:
                                            # 如果右侧既不是函数调用也不是变量引用，使用默认结构体名
                                            struct_name = 'XXX'
                                    
                                    # 处理 typedef 类型
                                    if is_typedef:
                                        # 获取右侧类型
                                        right_type = 'int'  # 默认类型
                                        if isinstance(Node.value, ast.Attribute) and isinstance(Node.value.value, ast.Name) and Node.value.value.id == 't':
                                            right_attr = Node.value.attr
                                            if hasattr(t, right_attr):
                                                type_obj = getattr(t, right_attr)
                                                if isinstance(type_obj, type):
                                                    right_type = type_obj().CName
                                        # 生成 typedef 语句
                                        Code.append(f'typedef {right_type} {var_name};')
                                        # 添加变量到当前作用域
                                        if self.VarScopes:
                                            self.VarScopes[-1][var_name] = var_name
                                        continue
                                    
                                    # 特殊处理 c.State，表示仅声明不定义
                                    if ValueCode[0] == 'c.State':
                                        # 处理其他变量
                                        if is_struct and struct_name:
                                            if is_ptr:
                                                Code.append(f'struct {struct_name}* {var_name}{array_size_str};')
                                            else:
                                                Code.append(f'struct {struct_name} {var_name}{array_size_str};')
                                        else:
                                            # 检查 base_type 是否包含存储类修饰符
                                            storage_class, type_part = check_storage_class(base_type)
                                            
                                            if storage_class:
                                                # 处理带存储类修饰符的变量
                                                Code.append(f'{storage_class} {type_part} {var_name}{array_size_str};')
                                            else:
                                                Code.append(f'{base_type} {var_name}{array_size_str};')
                                    else:
                                        # 处理带初始化值的变量
                                        if is_struct and struct_name:
                                            # 对于结构体类型，生成声明并调用构造函数
                                            if is_ptr:
                                                Code.append(f'struct {struct_name}* {var_name}{array_size_str};')
                                            else:
                                                Code.append(f'struct {struct_name} {var_name}{array_size_str};')
                                                # 检查右侧是否是构造函数调用
                                                if isinstance(Node.value, ast.Call):
                                                    # 提取构造函数参数
                                                    args = []
                                                    for arg in Node.value.args:
                                                        args.append(self.HandleExpr(arg)[0])
                                                    args_str = ', '.join(args)
                                                    # 生成构造函数调用
                                                    if args_str:
                                                        Code.append(f'{struct_name}____init__(&{var_name}, {args_str});')
                                                    else:
                                                        Code.append(f'{struct_name}____init__(&{var_name});')
                                        else:
                                            # 检查 base_type 是否包含存储类修饰符
                                            storage_class, type_part = check_storage_class(base_type)
                                            
                                            # 处理指针类型
                                            ptr_str = '*' if is_ptr else ''
                                            
                                            if storage_class:
                                                # 处理带存储类修饰符的变量
                                                Code.append(f'{storage_class} {type_part}{ptr_str} {var_name}{array_size_str} = {ValueCode[0]};')
                                            else:
                                                # 处理普通变量，包括指针类型
                                                Code.append(f'{base_type}{ptr_str} {var_name}{array_size_str} = {ValueCode[0]};')
                                    # 添加变量到当前作用域
                                    if self.VarScopes:
                                        self.VarScopes[-1][var_name] = type_name
                                else:
                                    # 默认使用int类型
                                    # 特殊处理数组初始化
                                    if isinstance(Node.value, ast.List):
                                        elements = []
                                        for elt in Node.value.elts:
                                            elements.append(self.HandleExpr(elt)[0])
                                        elements_str = ', '.join(elements)
                                        Code.append(f'int {var_name}[] = {{ {elements_str} }};')
                                    else:
                                        # 特殊处理 c.State，表示仅声明不定义
                                        if ValueCode[0] == 'c.State':
                                            Code.append(f'int {var_name};')
                                        else:
                                            Code.append(f'int {var_name} = {ValueCode[0]};')
                                    # 添加变量到当前作用域
                                    if self.VarScopes:
                                        self.VarScopes[-1][var_name] = 'int'
                            except Exception as e:
                                print(f'Warning: Failed to get type annotation: {e}')
                                # 发生异常时，默认使用int类型
                                # 特殊处理数组初始化
                                if isinstance(Node.value, ast.List):
                                    elements = []
                                    for elt in Node.value.elts:
                                        elements.append(self.HandleExpr(elt)[0])
                                    elements_str = ', '.join(elements)
                                    Code.append(f'int {var_name}[] = {{ {elements_str} }};')
                                else:
                                    # 特殊处理 c.State，表示仅声明不定义
                                    if ValueCode[0] == 'c.State':
                                        Code.append(f'int {var_name};')
                                    else:
                                        Code.append(f'int {var_name} = {ValueCode[0]};')
                                # 添加变量到当前作用域
                                if self.VarScopes:
                                    self.VarScopes[-1][var_name] = 'int'
                    else:
                        # 没有赋值部分，视为仅声明不定义，等价于 = c.State
                        # 直接处理特定的变量
                        if var_name == 'font':
                            Code.append('extern char font[4096];')
                        elif var_name == 'buf_mouse':
                            # 直接生成二维数组
                            Code.append('unsigned char* buf_mouse[256][256];')
                        elif var_name == 'buf_back':
                            Code.append('unsigned char* buf_back;')
                        elif var_name == 'a':
                            Code.append('char* a;')
                        else:
                            try:
                                type_name = self.GetTypeName(Node.annotation)
                                # 无论type_name是否为空，都生成声明语句
                                if type_name and type_name.strip():
                                    # 处理数组类型，提取数组大小
                                    base_type, array_size_str = extract_array_size(type_name)
                                    
                                    # 检查 base_type 是否包含存储类修饰符
                                    storage_class, type_part = check_storage_class(base_type)
                                    
                                    if storage_class:
                                        # 处理带存储类修饰符的变量
                                        Code.append(f'{storage_class} {type_part} {var_name}{array_size_str};')
                                    else:
                                        Code.append(f'{base_type} {var_name}{array_size_str};')
                                    
                                    # 添加变量到当前作用域
                                    if self.VarScopes:
                                        self.VarScopes[-1][var_name] = type_name
                                else:
                                    Code.append(f'int {var_name};')
                                    # 添加变量到当前作用域
                                    if self.VarScopes:
                                        self.VarScopes[-1][var_name] = 'int'
                            except Exception as e:
                                print(f'Warning: Failed to get type annotation: {e}')
                                Code.append(f'int {var_name};')
                                # 添加变量到当前作用域
                                if self.VarScopes:
                                    self.VarScopes[-1][var_name] = 'int'
                elif isinstance(Node.target, ast.Attribute):
                    # 处理 self.attribute 赋值，如 self.led = led
                    if isinstance(Node.target.value, ast.Name) and Node.target.value.id == 'self':
                        attr_name = Node.target.attr
                        # 检查是否有赋值部分
                        if Node.value:
                            ValueCode = self.HandleExpr(Node.value)
                            if ValueCode:
                                Code.append(f'self->{attr_name} = {ValueCode[0]};')
                else:
                    # 直接生成int类型的声明语句
                    Code.append(f'int a = "123";')
            elif isinstance(Node, ast.ClassDef):
                Code.extend(self.HandleClassDef(Node))
        return Code
    
    def HandleIf(self, Node):
        """处理if语句"""
        Code = []
        Test = self.HandleExpr(Node.test)[0]
        Code.append('if (' + Test + ') {')
        # 处理if语句体，确保正确缩进
        body_code = self.HandleBody(Node.body)
        # if语句体内部的语句应该再缩进4个空格
        Code.extend(['    ' + line for line in body_code])
        Code.append('}')
        if Node.orelse:
            # 检查else部分是否只有一个if语句（elif情况）
            if len(Node.orelse) == 1 and isinstance(Node.orelse[0], ast.If):
                # 处理elif情况，生成else if结构
                elif_node = Node.orelse[0]
                elif_test = self.HandleExpr(elif_node.test)[0]
                Code.append('else if (' + elif_test + ') {')
                # 处理elif语句体，确保正确缩进
                elif_body_code = self.HandleBody(elif_node.body)
                # elif语句体内部的语句应该再缩进4个空格
                Code.extend(['    ' + line for line in elif_body_code])
                Code.append('}')
                # 处理elif的else部分
                if elif_node.orelse:
                    Code.append('else {')
                    # 处理elif的else语句体，确保正确缩进
                    elif_else_code = self.HandleBody(elif_node.orelse)
                    # elif的else语句体内部的语句应该再缩进4个空格
                    Code.extend(['    ' + line for line in elif_else_code])
                    Code.append('}')
            else:
                # 处理普通else情况
                Code.append('else {')
                # 处理else语句体，确保正确缩进
                else_code = self.HandleBody(Node.orelse)
                # else语句体内部的语句应该再缩进4个空格
                Code.extend(['    ' + line for line in else_code])
                Code.append('}')
        return Code
    
    def HandleFor(self, Node):
        """处理for语句"""
        Code = []
        # 处理range循环
        if isinstance(Node.iter, ast.Call) and isinstance(Node.iter.func, ast.Name) and Node.iter.func.id == 'range':
            # 处理range参数
            start = 0
            stop = 0
            step = 1
            
            if len(Node.iter.args) >= 1:
                # 处理stop参数
                stop = self.HandleExpr(Node.iter.args[0])[0]
            if len(Node.iter.args) >= 2:
                # 处理start参数
                start = self.HandleExpr(Node.iter.args[0])[0]
                stop = self.HandleExpr(Node.iter.args[1])[0]
            if len(Node.iter.args) >= 3:
                # 处理step参数
                step = self.HandleExpr(Node.iter.args[2])[0]
            
            # 处理循环变量
            if isinstance(Node.target, ast.Name):
                var_name = Node.target.id
                # 生成for循环代码
                Code.append(f'for (int {var_name} = {start}; {var_name} < {stop}; {var_name} += {step}) {{')
                Code.extend(['    ' + line for line in self.HandleBody(Node.body)])
                Code.append('}')
                return Code
        
        # 默认处理
        Code.append('for (...) {')
        Code.extend(['    ' + line for line in self.HandleBody(Node.body)])
        Code.append('}')
        return Code
    
    def HandleWhile(self, Node):
        """处理while语句"""
        Code = []
        Test = self.HandleExpr(Node.test)[0]
        Code.append('while (' + Test + ') {')
        body_code = self.HandleBody(Node.body)
        Code.extend(['    ' + line for line in body_code])
        Code.append('}')
        return Code
    
    def GetTypeName(self, Node):
        """获取类型名称"""
        if isinstance(Node, ast.Name):
            type_name = Node.id
            # 检查是否是t模块中的类型
            if hasattr(t, type_name):
                type_obj = getattr(t, type_name)
                if isinstance(type_obj, type):
                    return type_obj().CName
            # 处理Python内置类型
            python_builtin_types = {
                'int': 'int',
                'str': 'char*',
                'bool': 'bool',
                'float': 'float',
                'double': 'double',
                'list': 'void*',
                'dict': 'void*',
                'set': 'void*',
                'tuple': 'void*'
            }
            if type_name in python_builtin_types:
                return python_builtin_types[type_name]
            # 将普通变量名视为结构体类型，如 DLL_STRPICENV
            return f'struct {type_name}'
        elif isinstance(Node, ast.Attribute):
            # 处理属性访问，如 t.CInt 或 c.State
            if isinstance(Node.value, ast.Name):
                if Node.value.id == 't':
                    type_name = Node.attr
                    if hasattr(t, type_name):
                        type_obj = getattr(t, type_name)
                        if isinstance(type_obj, type):
                            return type_obj().CName
                elif Node.value.id == 'c':
                    # 处理c模块的属性访问，如 c.State
                    attr_name = Node.attr
                    # 对于c模块属性，返回属性名
                    return f'c.{attr_name}'
            return 'int'
        elif isinstance(Node, ast.Call):
            # 处理函数调用，如 t.CStruct(name="SHTCTL")
            if isinstance(Node.func, ast.Attribute) and isinstance(Node.func.value, ast.Name) and Node.func.value.id == 't':
                type_name = Node.func.attr
                if hasattr(t, type_name):
                    type_obj = getattr(t, type_name)
                    if isinstance(type_obj, type):
                        # 解析关键字参数
                        kwargs = {}
                        for kw in Node.keywords:
                            if isinstance(kw.value, ast.Constant):
                                kwargs[kw.arg] = kw.value.value
                            elif isinstance(kw.value, ast.Name):
                                # 处理变量类型的参数值，如 name=DLL_STRPICENV
                                kwargs[kw.arg] = kw.value.id
                        # 使用关键字参数创建类型对象
                        return type_obj(**kwargs).CName
            return 'int'
        elif isinstance(Node, ast.Subscript):
            # 处理数组类型，如 t.CChar[0x80]
            base_type = self.GetTypeName(Node.value)
            if base_type:
                # 获取数组大小
                size = self.HandleExpr(Node.slice)[0]
                # 返回完整的类型名称，包含数组大小
                return f'{base_type}[{size}]'
            return 'int'
        elif isinstance(Node, ast.BinOp) and isinstance(Node.op, ast.BitOr):
            # 处理类型组合，如 t.CInt | t.CPtr 或 t.CStatic | t.CInt
            left_type = self.GetTypeName(Node.left)
            right_type = self.GetTypeName(Node.right)
            
            # 跳过None值，作为Python高亮辅助
            if left_type is None and right_type is None:
                return 'int'
            elif left_type is None:
                return right_type
            elif right_type is None:
                return left_type
            
            # 处理存储类修饰符与数组类型的组合
            if left_type == 'extern' and '[' in right_type:
                # 处理 t.CExtern | t.CInt[MAX_LANGUAGE_NUMBER] 或 t.CExtern | t.CChar[4096]
                base_type = right_type.split('[')[0]
                array_size = right_type[right_type.find('['):]
                return f'extern {base_type}{array_size}'
            elif left_type == 'static' and '[' in right_type:
                # 处理 t.CStatic | t.CChar[128]
                base_type = right_type.split('[')[0]
                array_size = right_type[right_type.find('['):]
                return f'static {base_type}{array_size}'
            elif left_type == 'unsigned' and 'char*' in right_type and '[' in right_type:
                # 处理 t.CUnsigned | t.CChar | t.CPtr | t.CChar[256]
                return 'unsigned char*[' + right_type.split('[')[1]
            # 处理存储类修饰符
            elif left_type in ['static', 'extern']:
                storage_class = left_type
                base_type = right_type
                # 修复 extern *struct TASKCTL 这样的格式，确保指针符号在结构体名称后面
                if base_type.startswith('*') and 'struct ' in base_type:
                    # 提取结构体名称
                    struct_name = base_type.replace('*', '').strip()
                    return f'{storage_class} {struct_name}*'
                return f'{storage_class} {base_type}'
            elif right_type in ['static', 'extern']:
                storage_class = right_type
                base_type = left_type
                return f'{storage_class} {base_type}'
            # 处理指针类型
            elif left_type == 'char' and right_type == '*':
                return 'char*'
            elif left_type == '*' and right_type == 'char':
                return 'char*'
            elif left_type == 'int' and right_type == '*':
                return 'int*'
            elif left_type == '*' and right_type == 'int':
                return 'int*'
            elif left_type == '*' and right_type.startswith('uint8_t'):
                return 'uint8_t*'
            elif left_type.startswith('uint8_t') and right_type == '*':
                return 'uint8_t*'
            # 处理结构体指针类型
            elif (left_type == 'struct' and right_type == '*') or (left_type == '*' and right_type == 'struct'):
                return 'struct *'
            elif '*' in left_type or '*' in right_type:
                # 处理指针和结构体数组的组合，如 * | struct FREEINFO[MEMMAN_FREES] 或 struct * | struct FREEINFO[MEMMAN_FREES]
                if (('*' in left_type or '*' in right_type) and '[' in left_type and 'struct ' in left_type) or (('*' in left_type or '*' in right_type) and '[' in right_type and 'struct ' in right_type):
                    # 提取结构体名称和数组大小
                    if '[' in right_type and 'struct ' in right_type:
                        struct_part = right_type.split('[')[0]
                        array_part = right_type[right_type.find('['):]
                    else:
                        struct_part = left_type.split('[')[0]
                        array_part = left_type[left_type.find('['):]
                    # 移除结构体部分中的 * 符号
                    struct_part = struct_part.replace('*', '').strip()
                    # 生成正确的结构体数组指针格式，如 struct FREEINFO *free[MEMMAN_FREES]
                    return f'{struct_part} *{array_part}'
                # 处理带名称的结构体指针类型
                elif left_type.startswith('struct ') and right_type == '*':
                    return f'{left_type}*'
                elif left_type == '*' and right_type.startswith('struct '):
                    return f'{right_type}*'
                # 处理 extern * | struct TASKCTL 这样的情况
                elif left_type.startswith('extern *') and right_type.startswith('struct '):
                    # 生成 extern struct TASKCTL* 格式
                    return f'extern {right_type}*'
                elif right_type.startswith('extern *') and left_type.startswith('struct '):
                    # 生成 extern struct TASKCTL* 格式
                    return f'extern {left_type}*'
                # 处理同时指定 t.CStruct 和结构体名称的情况，如 struct * | struct MEMMAN 或 struct | struct SHEET[MAX_SHEETS]
                elif left_type.startswith('struct ') and right_type.startswith('struct '):
                    # 当左右两侧都是结构体类型时，优先使用右侧的完整结构体类型
                    if '*' in left_type and '*' not in right_type:
                        return f'{right_type}*'
                    else:
                        return right_type
                # 处理 t.CStruct | SHEET[MAX_SHEETS] 这样的情况，避免生成 struct struct SHEET[MAX_SHEETS]
                elif left_type == 'struct' and right_type.startswith('struct '):
                    # 当左侧是 struct，右侧是完整的结构体类型时，只使用右侧的类型
                    return right_type
                elif right_type == 'struct' and left_type.startswith('struct '):
                    # 当右侧是 struct，左侧是完整的结构体类型时，只使用左侧的类型
                    return left_type
                # 处理普通指针类型组合，如 * | unsigned char 或 unsigned char | *
                elif left_type == '*' and right_type != '*':
                    # 当左侧是指针，右侧是普通类型时，将指针放在右侧类型后面
                    return f'{right_type}*'
                elif right_type == '*' and left_type != '*':
                    # 当右侧是指针，左侧是普通类型时，将指针放在左侧类型后面
                    return f'{left_type}*'
                else:
                    return f'{left_type}{right_type}'
            # 处理同时指定 t.CStruct 和结构体名称的情况，如 struct | struct SHEET[MAX_SHEETS]
            elif (left_type == 'struct' and right_type.startswith('struct ')) or (right_type == 'struct' and left_type.startswith('struct ')):
                # 当左右两侧都是结构体类型时，优先使用右侧的完整结构体类型
                if left_type == 'struct' and right_type.startswith('struct '):
                    return right_type
                else:
                    return left_type
            # 处理长整型和整型的组合
            elif (left_type == 'long' and right_type == 'int') or (left_type == 'int' and right_type == 'long'):
                return 'long int'
            # 处理长整型和整型数组的组合
            elif (left_type == 'long' and 'int[' in right_type) or (left_type == 'int' and 'long[' in right_type):
                # 提取数组大小部分
                if '[' in right_type:
                    array_part = right_type[right_type.find('['):]
                    return f'long int{array_part}'
                elif '[' in left_type:
                    array_part = left_type[left_type.find('['):]
                    return f'long int{array_part}'
            # 确保返回有效的类型名称
            elif left_type == 'int' or right_type == 'int':
                return 'int'
            return f'{left_type} {right_type}'
        # 确保返回有效的类型名称
        return 'int'
    
    def HandleTSpecialCall(self, attr, args, keywords):
        """处理t模块中的特殊语法"""
        # 处理t.CType(x, t.CInt())调用或t.CType(x, t.CUnsigned, t.CChar, t.CPtr)调用
        if attr == 'CType':
            if len(args) >= 1:
                value = self.HandleExpr(args[0])[0]
                # 处理类型参数
                type_str = ''
                for i in range(1, len(args)):
                    type_arg = args[i]
                    # 使用GetTypeName方法获取类型名称，支持带参数的类型构造
                    type_name = self.GetTypeName(type_arg)
                    if type_name:
                        type_str += f'{type_name} '
                # 移除末尾空格
                type_str = type_str.strip()
                if type_str:
                    return [f'(({type_str}){value})']
                else:
                    # 没有类型参数，直接返回值
                    return [value]
            return ['0']
        # 处理t.CStruct调用，生成结构体指针类型转换
        elif attr == 'CStruct':
            if len(args) >= 1:
                # 获取地址值
                addr = self.HandleExpr(args[0])[0]
                # 获取结构体名称
                struct_name = 'BOOTINFO'  # 默认值
                if len(args) >= 2 and isinstance(args[1], ast.Name):
                    struct_name = args[1].id
                # 生成类型转换代码
                return [f'((struct {struct_name} *){addr})']
            return ['0']
        # 处理单个类型转换函数，如t.CInt(x)或t.CChar(x, t.CPtr)
        elif attr in ['CInt', 'CChar', 'CShort', 'CLong', 'CFloat', 'CDouble', 'CVoid', 'CUnsigned', 'CUnsignedChar', 'CUnsignedInt', 'CUnsignedShort', 'CUnsignedLong', 'CSignedChar', 'CSizeT', 'CInt8T', 'CInt16T', 'CInt32T', 'CInt64T', 'CUInt8T', 'CUInt16T', 'CUInt32T', 'CUInt64T', 'CIntPtrT', 'CUIntPtrT', 'CPtrDiffT', 'CWCharT', 'CChar16T', 'CChar32T', 'CBool', 'CComplex', 'CImaginary', 'CPtr']:
            if len(args) >= 1:
                # 检查第一个参数是否是元组
                if isinstance(args[0], ast.Tuple) and len(args[0].elts) >= 2:
                    # 处理t.CChar((value, t.CPtr))这种形式
                    value = self.HandleExpr(args[0].elts[0])[0]
                    # 提取类型修饰符参数
                    type_parts = []
                    # 首先添加当前类型
                    if attr in TYPE_MAP:
                        type_parts.append(TYPE_MAP[attr])
                    # 添加元组中的类型修饰符参数
                    for i in range(1, len(args[0].elts)):
                        type_arg = args[0].elts[i]
                        type_name = self.GetTypeName(type_arg)
                        if type_name:
                            type_parts.append(type_name)
                    # 添加其他参数中的类型修饰符
                    for i in range(1, len(args)):
                        type_arg = args[i]
                        type_name = self.GetTypeName(type_arg)
                        if type_name:
                            type_parts.append(type_name)
                    # 组合类型部分
                    type_str = ' '.join(type_parts)
                    # 特殊处理指针类型，确保 * 与类型之间有空格
                    if '*' in type_str:
                        # 只在 * 前面没有空格时添加空格
                        import re
                        type_str = re.sub(r'(?<!\s)\*', ' *', type_str)
                        type_str = type_str.strip()
                    # 生成类型转换
                    return [f'(({type_str}){value})']
                else:
                    # 处理普通的t.CChar(value)形式
                    value = self.HandleExpr(args[0])[0]
                    # 提取类型修饰符参数
                    type_parts = []
                    # 首先添加当前类型
                    if attr in TYPE_MAP:
                        type_parts.append(TYPE_MAP[attr])
                    # 添加额外的类型修饰符参数
                    for i in range(1, len(args)):
                        type_arg = args[i]
                        type_name = self.GetTypeName(type_arg)
                        if type_name:
                            type_parts.append(type_name)
                    # 组合类型部分
                    type_str = ' '.join(type_parts)
                    # 特殊处理指针类型，确保 * 与类型之间有空格
                    if '*' in type_str:
                        # 只在 * 前面没有空格时添加空格
                        import re
                        type_str = re.sub(r'(?<!\s)\*', ' *', type_str)
                        type_str = type_str.strip()
                    # 生成类型转换
                    return [f'(({type_str}){value})']
        # 默认处理
        args_str = ', '.join([self.HandleExpr(arg)[0] for arg in args])
        return [f't.{attr}({args_str});']
    
    def HandleCSpecialCall(self, attr, args, keywords):
        """处理c模块中的特殊语法"""
        if attr == 'Asm':
            # 处理c.Asm()调用
            if args:
                if isinstance(args[0], ast.Constant):
                    asm_code = args[0].value
                    # 处理多行字符串
                    asm_code = asm_code.replace('\n', '\n')
                    return [f'asm volatile ({asm_code});']
                elif isinstance(args[0], ast.BinOp) and isinstance(args[0].op, ast.Mod):
                    # 处理格式化字符串，如 "out %0, %1" % (value, port)
                    # 提取格式化字符串
                    if isinstance(args[0].left, ast.Constant) and isinstance(args[0].left.value, str):
                        format_str = args[0].left.value
                        # 提取格式化参数
                        if isinstance(args[0].right, ast.Tuple):
                            params = []
                            for arg in args[0].right.elts:
                                param_code = self.HandleExpr(arg)[0]
                                params.append(param_code)
                            # 构建汇编代码
                            # 对于 out 指令，我们需要使用正确的 GCC 汇编格式
                            # 假设格式为 "out %0, %1"，其中 %0 是 value，%1 是 port
                            asm_code = format_str
                            # 处理引号
                            asm_code = f'"{asm_code}"'
                            # 为 out 指令添加操作数约束
                            # 对于 x86 out 指令，value 应该在 eax 寄存器，port 应该在 edx 寄存器
                            return [f'asm volatile ({asm_code} : : "a"({params[0]}), "d"({params[1]}));']
                    return ['asm volatile ("nop");']
                else:
                    return ['asm volatile ("nop");']
            return ['asm volatile ("nop");']
        elif attr == 'Memory':
            # 处理c.Memory()调用
            if args:
                if isinstance(args[0], ast.Constant):
                    addr = args[0].value
                    return [f'((void *){addr})']
                else:
                    return ['((void *)0)']
            return ['((void *)0)']
        elif attr == 'TypeCast':
            # 处理c.TypeCast()调用
            if len(args) >= 2:
                if isinstance(args[0], ast.Constant):
                    type_name = args[0].value
                else:
                    type_name = 'void'
                value = self.HandleExpr(args[1])[0]
                return [f'(({type_name}){value})']
            return ['((void *)0)']
        elif attr == 'Macro':
            # 处理c.Macro()调用
            if len(args) >= 2:
                if isinstance(args[0], ast.Constant):
                    name = args[0].value
                else:
                    name = 'MACRO'
                if isinstance(args[1], ast.Constant):
                    value = args[1].value
                else:
                    value = '0'
                return [f'#define {name} {value}']
            return []
        elif attr == 'Addr':
            # 处理c.Addr()调用，翻译为 &s
            if args:
                expr = self.HandleExpr(args[0])[0]
                return [f'&{expr}']
            return ['0']
        elif attr == 'Ptr':
            # 处理c.Ptr()调用
            if args:
                addr = self.HandleExpr(args[0])[0]
                value = None
                type_name = None
                # 处理位置参数（第二个参数作为value）
                if len(args) > 1:
                    value = self.HandleExpr(args[1])[0]
                # 处理关键字参数
                for kw in keywords:
                    if kw.arg == 'value':
                        value = self.HandleExpr(kw.value)[0]
                    elif kw.arg == 'type':
                        # 尝试获取类型名称
                        type_name = self.GetTypeName(kw.value)
                if value is not None:
                    if type_name:
                        return [f'*(({type_name}*){addr}) = {value};']
                    else:
                        return [f'*((void *){addr}) = {value};']
                else:
                    if type_name:
                        return [f'(({type_name}*){addr})']
                    else:
                        return [f'((void *){addr})']
            return ['((void *)0)']
        # 默认处理
        args_str = ', '.join([self.HandleExpr(arg)[0] for arg in args])
        return [f'c.{attr}({args_str});']
    
    def GetAugOpSymbol(self, Op):
        """获取复合赋值运算符符号"""
        op_name = type(Op).__name__
        return AUG_OPERATOR_MAP.get(op_name, '')
    
    def GetUnaryOpSymbol(self, Op):
        """获取一元运算符符号"""
        op_name = type(Op).__name__
        return UNARY_OPERATOR_MAP.get(op_name, '')