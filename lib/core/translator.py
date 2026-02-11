# 核心转换逻辑

import ast
import re
import sys
import os
import functools
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


def debug_handle(func):
    """装饰器：记录 Handle 方法的进入和退出"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        func_name = func.__name__
        # 获取节点类型信息
        node_info = ""
        if args and hasattr(args[0], '__class__'):
            node = args[0]
            node_type = type(node).__name__
            node_info = f"[{node_type}]"
            # 尝试获取节点详情
            if hasattr(node, 'id'):
                node_info += f" id={node.id}"
            elif hasattr(node, 'attr'):
                node_info += f" attr={node.attr}"
            elif hasattr(node, 'name'):
                node_info += f" name={node.name}"
        
        self.debug_print(f"[ENTER] {func_name} {node_info}")
        try:
            result = func(self, *args, **kwargs)
            result_summary = ""
            if isinstance(result, list):
                result_summary = f" -> {len(result)} lines"
            elif isinstance(result, str):
                result_summary = f" -> '{result[:50]}...'" if len(result) > 50 else f" -> '{result}'"
            self.debug_print(f"[EXIT] {func_name} {node_info}{result_summary}")
            return result
        except Exception as e:
            self.debug_print(f"[ERROR] {func_name} {node_info}: {e}")
            raise
    return wrapper


class Translator:
    """代码转换器"""
    
    def __init__(self):
        self.VarScopes = []  # 跟踪变量作用域
        self.FunctionReturnTypes = {}  # 记录函数名和其返回类型
        self.SymbolTable = {}  # 符号表
        self.OriginalLines = []  # 原始代码行
        self.Content = ''
        self.debug_file = None  # 调试输出文件路径
    
    def set_debug_file(self, file_path):
        """设置调试输出文件"""
        self.debug_file = file_path
    
    def debug_print(self, *args, **kwargs):
        """输出调试信息到文件"""
        if self.debug_file:
            with open(self.debug_file, 'a', encoding='utf-8') as f:
                print(*args, file=f, **kwargs)
    
    def ParseHelperFiles(self, helper_files, encoding='utf-8'):
        """解析辅助文件，提取符号信息
        
        支持 .py, .c, .h 和 .symbin 文件
        """
        for file_path in helper_files:
            ext = detect_file_type(file_path)
            if ext == '.py':
                self.ParsePythonFile(file_path, encoding)
            elif ext == '.c':
                self.ParseCFile(file_path, encoding)
            elif file_path.endswith('.symbin'):
                self.LoadSymbinFile(file_path)
    
    def LoadSymbinFile(self, file_path):
        """从.symbin文件加载符号表
        
        Args:
            file_path: .symbin文件路径
        """
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # 导入序列化函数（避免循环导入）
            import sys
            import os
            import json
            import struct
            
            # 解析二进制格式
            if len(data) < 4:
                print(f"Warning: Invalid symbin file (too short): {file_path}")
                return
            
            # 解析4字节长度头（小端序）
            length = struct.unpack('<I', data[:4])[0]
            json_data = data[4:4+length]
            symbols = json.loads(json_data.decode('utf-8'))
            
            # 合并到当前符号表
            self.SymbolTable.update(symbols)
            self.debug_print(f"[SYMBIN] Loaded {len(symbols)} symbols from {file_path}")
            
        except Exception as e:
            print(f"Warning: Failed to load symbin file {file_path}: {e}")
    
    def ParsePythonFile(self, file_path, encoding='utf-8'):
        """解析Python文件，提取类、函数、变量信息"""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
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
                                # 检查原始注解是否包含CPtr
                                if not is_pointer:
                                    # 直接检查AST节点是否包含CPtr
                                    if isinstance(item.annotation, ast.BinOp) and isinstance(item.annotation.op, ast.BitOr):
                                        # 检查左右两侧是否有CPtr
                                        left_str = ast.dump(item.annotation.left)
                                        right_str = ast.dump(item.annotation.right)
                                        if 'CPtr' in left_str or 'CPtr' in right_str:
                                            is_pointer = True
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
    
    def ParseCFile(self, file_path, encoding='utf-8'):
        """解析C文件，提取结构体、函数、变量信息"""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
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
        # 首先解析主文件中的类定义、函数定义和变量定义，填充符号表
        for Node in ast.iter_child_nodes(Tree):
            if isinstance(Node, ast.ClassDef):
                class_name = Node.name
                # 提取结构体成员信息
                members = {}
                for item in Node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        var_name = item.target.id
                        try:
                            var_type = self.GetTypeName(item.annotation)
                            # 检查是否是指针类型
                            is_pointer = '*' in var_type or 'CPtr' in var_type
                            # 检查原始注解是否包含CPtr
                            if not is_pointer:
                                # 直接检查AST节点是否包含CPtr
                                if isinstance(item.annotation, ast.BinOp) and isinstance(item.annotation.op, ast.BitOr):
                                    # 检查左右两侧是否有CPtr
                                    left_str = ast.dump(item.annotation.left)
                                    right_str = ast.dump(item.annotation.right)
                                    if 'CPtr' in left_str or 'CPtr' in right_str:
                                        is_pointer = True
                            members[var_name] = {'type': var_type, 'is_pointer': is_pointer}
                        except:
                            pass
                self.SymbolTable[class_name] = {'type': 'struct', 'members': members}
            elif isinstance(Node, ast.FunctionDef):
                func_name = Node.name
                self.SymbolTable[func_name] = {'type': 'function'}
            elif isinstance(Node, ast.AnnAssign):
                if isinstance(Node.target, ast.Name):
                    var_name = Node.target.id
                    # 尝试获取类型信息
                    var_type = 'unknown'
                    is_pointer = False
                    if Node.annotation:
                        try:
                            var_type = self.GetTypeName(Node.annotation)
                            is_pointer = '*' in var_type or 'CPtr' in var_type
                        except:
                            pass
                    self.SymbolTable[var_name] = {'type': 'variable', 'declared_type': var_type, 'is_pointer': is_pointer}
        
        Code = []
        # 打印符号表（用于调试）
        self.debug_print("=== Symbol Table ===")
        for key, value in self.SymbolTable.items():
            self.debug_print(f"{key}: {value}")
        self.debug_print("===================")
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
            # 检查原始代码行是否包含 #include 注释
            include_directive = None
            if hasattr(Node, 'lineno') and hasattr(self, 'OriginalLines'):
                line_number = Node.lineno - 1  # 转换为0-based索引
                if 0 <= line_number < len(self.OriginalLines):
                    original_line = self.OriginalLines[line_number]
                    # 查找 #include 注释
                    if '#include' in original_line:
                        # 提取从 #include 开始的部分
                        include_part = original_line.split('#include', 1)[1].strip()
                        include_directive = f'#include {include_part}'
            
            # 如果找到 #include 注释，直接使用它
            if include_directive:
                return [include_directive]
            
            # 构建完整的模块路径，包括相对导入的点
            full_module_path = '.' * Node.level
            if Node.module:
                full_module_path += Node.module
            # 生成包含原始导入语句的注释
            import_comment = f'from {full_module_path} import '
            if Node.names:
                if len(Node.names) == 1 and Node.names[0].name == '*':
                    import_comment += '*'
                else:
                    import_comment += ', '.join([alias.name for alias in Node.names])
            else:
                import_comment += '...'
            # 将模块路径中的点替换为斜杠，并添加.h扩展名
            # 处理相对路径的情况
            if full_module_path.startswith('.'):
                # 对于相对路径，先移除开头的点，然后替换剩余的点为斜杠
                # 注意：这里需要特殊处理，因为我们需要保留相对路径的结构
                # 例如：..core.kernel 应该变成 ../core/kernel.h
                parts = full_module_path.split('.')
                # 计算相对路径的层级
                level = 0
                while level < len(parts) and parts[level] == '':
                    level += 1
                # 构建相对路径
                relative_path = '../' * (level - 1)
                # 添加模块路径
                if level < len(parts):
                    relative_path += '/'.join(parts[level:])
                header_path = relative_path + '.h'
            else:
                # 对于绝对路径，直接替换点为斜杠
                header_path = full_module_path.replace('.', '/') + '.h'
            return [f'#include "{header_path}" // {import_comment}']
        return []
    
    @debug_handle
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
        self.debug_print(f"[SCOPE] Enter function '{Node.name}', new scope created, depth={len(self.VarScopes)}")
        
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
        self.debug_print(f"[SCOPE] Exit function '{Node.name}', scope popped, depth={len(self.VarScopes)}")
        
        # 记录函数返回类型
        self.FunctionReturnTypes[Node.name] = ReturnType
        
        return Code
    
    def HandleClassDef(self, Node):
        """处理类定义"""
        Code = []
        # 检查类是否已经在符号表中
        if Node.name not in self.SymbolTable:
            # 如果不在，添加到符号表中
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
    
    @debug_handle
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
                obj_expr = Target.value
                obj_name = None
                last_member_name = None
                
                # 提取对象名称（递归处理嵌套属性访问）
                current = obj_expr
                while isinstance(current, ast.Attribute):
                    last_member_name = current.attr
                    current = current.value
                if isinstance(current, ast.Name):
                    obj_name = current.id
                elif isinstance(current, ast.Attribute):
                    last_member_name = current.attr
                elif isinstance(current, ast.Subscript):
                    # 处理数组访问后的成员赋值，如 ctl.sheets[h].height = h
                    # 需要获取数组基础表达式（如 ctl.sheets）
                    subscript_base = current.value
                    if isinstance(subscript_base, ast.Attribute):
                        obj_name = subscript_base.value.id if isinstance(subscript_base.value, ast.Name) else None
                        last_member_name = subscript_base.attr
                
                # 处理对象表达式
                obj = self.HandleExpr(obj_expr)[0]
                attr = Target.attr
                ValueCode = self.HandleExpr(Node.value)
                if ValueCode:
                    # 检查obj是否是指针类型
                    is_pointer = False
                    # 特殊处理 self 参数，它总是指针
                    if obj == 'self':
                        is_pointer = True
                    # 检查obj是否是类型转换表达式（如 ((struct TIMER *)reg[7])）
                    # 类型转换表达式通常包含指针类型
                    elif obj.startswith('((struct') and '*)' in obj:
                        is_pointer = True
                    # 从作用域中查找变量类型
                    elif obj_name:
                        # 首先检查局部作用域（优先级高）
                        found_in_scope = False
                        is_function_param = False
                        for i, scope in enumerate(reversed(self.VarScopes)):
                            if obj_name in scope:
                                var_type = scope[obj_name]
                                if '*' in var_type:
                                    is_pointer = True
                                found_in_scope = True
                                # 检查是否是函数参数（通常在第一个作用域中）
                                if i == len(self.VarScopes) - 1:
                                    is_function_param = True
                                break
                        
                        # 特殊处理：如果变量名是 cons 且是函数参数，它总是指针
                        if not found_in_scope and obj_name == 'cons':
                            # 检查是否在符号表中且是指针类型
                            if obj_name in self.SymbolTable:
                                symbol_info = self.SymbolTable[obj_name]
                                if 'is_pointer' in symbol_info:
                                    is_pointer = symbol_info['is_pointer']
                                elif 'declared_type' in symbol_info and '*' in symbol_info['declared_type']:
                                    is_pointer = True
                        # 如果作用域中没有找到，从符号表中查找（全局变量）
                        elif not found_in_scope and obj_name in self.SymbolTable:
                            symbol_info = self.SymbolTable[obj_name]
                            if 'is_pointer' in symbol_info:
                                is_pointer = symbol_info['is_pointer']
                            elif 'declared_type' in symbol_info and '*' in symbol_info['declared_type']:
                                is_pointer = True
                    
                    # 如果有最后一个成员名，检查该成员是否是指针类型
                    if last_member_name and obj_name:
                        # 先从VarScopes中查找变量类型
                        var_type = None
                        for scope in reversed(self.VarScopes):
                            if obj_name in scope:
                                var_type = scope[obj_name]
                                break
                        
                        # 如果VarScopes中没有找到，从SymbolTable中查找
                        if not var_type and obj_name in self.SymbolTable:
                            base_info = self.SymbolTable[obj_name]
                            if base_info['type'] == 'variable' and 'declared_type' in base_info:
                                var_type = base_info['declared_type']
                        
                        # 如果找到了变量类型，解析结构体名称并查找成员
                        if var_type and var_type.startswith('struct '):
                            struct_name = var_type.split(' ')[1].rstrip('*')
                            if struct_name in self.SymbolTable:
                                struct_info = self.SymbolTable[struct_name]
                                if struct_info['type'] == 'struct' and 'members' in struct_info:
                                    if last_member_name in struct_info['members']:
                                        member_info = struct_info['members'][last_member_name]
                                        member_type = member_info.get('type', '')
                                        # 特殊处理：如果赋值目标的基础表达式是数组访问（如 ctl.sheets[h].height）
                                        # 且数组成员是指针数组类型，则数组元素也是指针
                                        # 注意：只有数组类型的成员（如 TYPE* arr[N]）才需要特殊处理
                                        # 非数组类型的指针成员（如 TYPE* ptr）不需要特殊处理
                                        if isinstance(obj_expr, ast.Subscript):
                                            if '[' in member_type:
                                                # 是数组类型，检查元素是否是指针
                                                if member_info.get('is_pointer'):
                                                    is_pointer = True
                                                else:
                                                    is_pointer = False
                                            else:
                                                # 不是数组类型（如 FILEHANDLE* fhandle）
                                                # fhandle[i] 不是指针，使用 . 而不是 ->
                                                is_pointer = False
                                        elif isinstance(obj_expr, ast.Attribute):
                                            # 处理嵌套属性访问，如 task.fhandle2.buf
                                            # 检查 obj_expr（fhandle2）是否是指针类型
                                            if not member_info.get('is_pointer'):
                                                # fhandle2 不是指针，使用 . 而不是 ->
                                                is_pointer = False
                        
                        # 特殊处理：即使找不到变量类型，也检查是否是已知的结构体成员
                        # 这对于全局变量或未声明的变量（如 ctl）很有用
                        elif not var_type:
                            # 尝试在所有结构体中查找成员名
                            for struct_name, struct_info in self.SymbolTable.items():
                                if struct_info['type'] == 'struct' and 'members' in struct_info:
                                    if last_member_name in struct_info['members']:
                                        member_info = struct_info['members'][last_member_name]
                                        # 特殊处理数组访问
                                        if isinstance(obj_expr, ast.Subscript):
                                            member_type = member_info.get('type', '')
                                            if '[' in member_type and member_info.get('is_pointer'):
                                                # 是指针数组，元素是指针
                                                is_pointer = True
                                            else:
                                                # 不是数组类型，fhandle[i] 不是指针
                                                is_pointer = False
                                        elif isinstance(obj_expr, ast.Attribute):
                                            # 处理嵌套属性访问，如 task.fhandle2.buf
                                            if not member_info.get('is_pointer'):
                                                # fhandle2 不是指针，使用 . 而不是 ->
                                                is_pointer = False
                                        break
                    
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
                # 检查变量是否已经在当前作用域中声明过
                if self.VarScopes and var_name in self.VarScopes[-1]:
                    # 变量已存在，生成赋值语句而不是声明语句
                    self.debug_print(f'[VAR] Variable {var_name} already declared, generating assignment')
                    Code.append(f'{var_name} = {ValueCode[0]};')
                    return Code
                try:
                    type_name = self.GetTypeName(Node.annotation)
                    if type_name:
                        # 调试输出
                        self.debug_print(f'Debug: var_name={var_name}, type_name={type_name}')
                        # 处理数组类型，提取数组大小
                        base_type, array_size_str = extract_array_size(type_name)
                        self.debug_print(f'Debug: base_type={base_type}, array_size_str={array_size_str}')
                        
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
                                # 优先检查是否是 t.CType 调用
                                if isinstance(Node.value, ast.Call) and isinstance(Node.value.func, ast.Attribute):
                                    # 检查是否是 t.CType 调用
                                    if (isinstance(Node.value.func.value, ast.Name) and Node.value.func.value.id == 't' and 
                                        Node.value.func.attr == 'CType'):
                                        # 提取参数
                                        if len(Node.value.args) >= 1:
                                            # 获取地址值
                                            addr = self.HandleExpr(Node.value.args[0])[0]
                                            # 获取结构体名称
                                            struct_name = 'BOOTINFO'  # 默认值
                                            # 尝试从第二个参数获取结构体名称
                                            if len(Node.value.args) >= 2:
                                                # 处理不同类型的第二个参数
                                                if isinstance(Node.value.args[1], ast.Name):
                                                    # 变量名或类名
                                                    struct_name = Node.value.args[1].id
                                                elif isinstance(Node.value.args[1], ast.Attribute):
                                                    # 处理属性访问，如 t.MEMMAN
                                                    struct_name = Node.value.args[1].attr
                                            # 生成类型转换代码
                                            Code.append(f'struct {struct_name}* {var_name}{array_size_str} = ((struct {struct_name} *){addr});')
                                        else:
                                            Code.append(f'void* {var_name}{array_size_str} = {ValueCode[0]};')
                                    # 处理 t.CStruct(...) 调用，生成类型转换代码
                                    elif (isinstance(Node.value.func.value, ast.Name) and Node.value.func.value.id == 't' and 
                                          Node.value.func.attr == 'CStruct'):
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
                                # 检查右侧是否是结构体名称（非执行格式，无括号）
                                elif isinstance(Node.value, ast.Name):
                                    # 右侧是结构体名称，视为结构体声明
                                    struct_name = Node.value.id
                                    # 检查结构体是否在符号表中
                                    if struct_name in self.SymbolTable and self.SymbolTable[struct_name]['type'] == 'struct':
                                        # 生成结构体声明
                                        Code.append(f'struct {struct_name}* {var_name}{array_size_str};')
                                    else:
                                        # 生成普通声明
                                        Code.append(f'{base_type} {var_name}{array_size_str} = {ValueCode[0]};')
                                # 检查右侧是否是执行格式（带括号）
                                elif isinstance(Node.value, ast.Call):
                                    # 检查是否是结构体构造函数调用
                                    is_struct_constructor = False
                                    struct_name = None
                                    
                                    # 检查类型注解是否是结构体
                                    is_struct_annotation = False
                                    if base_type in self.SymbolTable and self.SymbolTable[base_type]['type'] == 'struct':
                                        is_struct_annotation = True
                                        struct_name = base_type
                                    elif 'struct ' in base_type:
                                        # 处理类型注解中直接包含struct关键字的情况
                                        is_struct_annotation = True
                                        struct_name = base_type.replace('struct ', '')
                                    
                                    # 检查是否是真正的结构体构造函数
                                    # 1. 只有当被调用的函数不是c模块的函数时，才可能是构造函数
                                    # 2. 只有当函数名与结构体名相同时，才视为构造函数
                                    # 3. 只有当结构体在符号表中明确标记为结构体时，才调用__init__
                                    if struct_name:
                                        # 检查是否是c模块的函数调用
                                        is_c_function = False
                                        if isinstance(Node.value.func, ast.Attribute):
                                            if isinstance(Node.value.func.value, ast.Name) and Node.value.func.value.id == 'c':
                                                is_c_function = True
                                        
                                        # 只有不是c模块的函数，才可能是构造函数
                                        if not is_c_function:
                                            # 获取被调用的函数名
                                            called_func_name = None
                                            if isinstance(Node.value.func, ast.Name):
                                                called_func_name = Node.value.func.id
                                            elif isinstance(Node.value.func, ast.Attribute):
                                                called_func_name = Node.value.func.attr
                                            
                                            # 检查函数名是否与结构体名相同
                                            if called_func_name == struct_name:
                                                # 检查函数是否在符号表中是结构体
                                                if called_func_name in self.SymbolTable and self.SymbolTable[called_func_name]['type'] == 'struct':
                                                    is_struct_constructor = True
                                    
                                    if is_struct_constructor:
                                        # 是结构体构造函数，生成结构体声明并调用构造函数
                                        Code.append(f'struct {struct_name} {var_name}{array_size_str};')
                                        # 生成构造函数调用
                                        args = ['&' + var_name]
                                        for arg in Node.value.args:
                                            args.append(self.HandleExpr(arg)[0])
                                        args_str = ', '.join(args)
                                        Code.append(f'{struct_name}____init__({args_str});')
                                    elif is_struct_annotation:
                                        # 类型注解是结构体，但右侧不是结构体构造函数，直接赋值
                                        Code.append(f'struct {struct_name} {var_name}{array_size_str} = {ValueCode[0]};')
                                    else:
                                        # 生成普通声明
                                        Code.append(f'{base_type} {var_name}{array_size_str} = {ValueCode[0]};')
                                # 处理其他情况
                                elif '*' in base_type:
                                    # 尝试从右侧表达式获取类型名称
                                    if isinstance(Node.value, ast.Name):
                                        type_name = Node.value.id
                                        Code.append(f'struct {type_name}* {var_name}{array_size_str} = {ValueCode[0]};')
                                    else:
                                        Code.append(f'void* {var_name}{array_size_str} = {ValueCode[0]};')
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
    

    def GetStringQuoteType(self, code: str, node: ast.Constant) -> str:
        """获取整个字符串字面量，包括引号"""
        if not isinstance(node.value, str):
            raise ValueError("节点必须是字符串类型的ast.Constant")
        line_num = node.lineno
        col = node.col_offset
        
        # 直接从原始代码中提取字符串字面量
        # 找到包含当前位置的行
        lines = code.splitlines(keepends=True)
        if line_num - 1 >= len(lines):
            raise IndexError("AST节点行号超出原始代码行范围")
        
        target_line = lines[line_num - 1]
        if col >= len(target_line):
            raise IndexError("AST节点列偏移超出该行字符范围")
        
        # 从当前列开始查找字符串的起始引号
        start_idx = col
        while start_idx < len(target_line):
            char = target_line[start_idx]
            if char in ('"', "'"):
                # 找到起始引号
                quote_char = char
                # 检查是否是三引号
                if start_idx + 2 < len(target_line) and target_line[start_idx:start_idx+3] == quote_char * 3:
                    quote_len = 3
                    start_idx += 3
                else:
                    quote_len = 1
                    start_idx += 1
                
                # 查找结束引号
                end_idx = start_idx
                while end_idx < len(target_line):
                    if target_line[end_idx] == '\\':
                        # 转义字符，跳过下一个字符
                        end_idx += 2
                    elif target_line[end_idx:end_idx+quote_len] == quote_char * quote_len:
                        # 找到结束引号
                        end_idx += quote_len
                        break
                    else:
                        end_idx += 1
                else:
                    # 没有找到结束引号，使用行尾
                    end_idx = len(target_line)
                
                # 提取字符串字面量
                string_literal = target_line[col:end_idx]
                return string_literal
            start_idx += 1
        
        # 如果没有找到引号，使用默认的双引号字符串
        escaped_value = node.value.replace("\\", "\\\\")
        escaped_value = escaped_value.replace('"', '\\"')
        return f'"{escaped_value}"'
    
    def GetNumericLiteral(self, code: str, node: ast.Constant) -> str:
        """获取数字的原始字面量表示"""
        if not isinstance(node.value, (int, float, complex)):
            raise ValueError("节点必须是数字类型的ast.Constant")
        line_num = node.lineno
        col = node.col_offset
        code_lines = code.splitlines(keepends=False)
        if line_num - 1 >= len(code_lines):
            raise IndexError("AST节点行号超出原始代码行范围")
        target_line = code_lines[line_num - 1]
        if col >= len(target_line):
            raise IndexError("AST节点列偏移超出该行字符范围")
        
        # 提取数字字面量
        # 数字字面量的模式：[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?|0[xX][0-9a-fA-F]+|0[oO][0-7]+|0[bB][01]+
        import re
        # 从当前位置开始查找数字字面量
        # 首先找到当前位置的字符
        start_char = target_line[col]
        # 构建正则表达式匹配数字字面量
        num_pattern = r'\b(?:0[xX][0-9a-fA-F]+|0[oO][0-7]+|0[bB][01]+|\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)\b'
        # 查找所有匹配的数字字面量
        matches = list(re.finditer(num_pattern, target_line))
        # 找到包含当前列的匹配
        for match in matches:
            if match.start() <= col <= match.end():
                return match.group()
        # 如果没有找到，返回默认的字符串表示
        return str(node.value)

    @debug_handle
    def HandleExpr(self, Node, use_single_quote=False):
        """处理表达式"""
        if isinstance(Node, ast.Constant):
            if isinstance(Node.value, str):
                # 使用 GetStringQuoteType 函数获取原始的字符串字面量
                string_literal = self.GetStringQuoteType(self.Content, Node)
                # 直接返回原始字符串字面量
                return [string_literal]
            elif isinstance(Node.value, bool):
                # 处理布尔值，将 True 转换为 1，将 False 转换为 0
                return ['1' if Node.value else '0']
            else:
                # 检查是否是数字
                if isinstance(Node.value, (int, float, complex)):
                    # 尝试获取原始字面量表示
                    try:
                        literal = self.GetNumericLiteral(self.Content, Node)
                        return [literal]
                    except:
                        # 如果获取失败，返回默认的字符串表示
                        return [str(Node.value)]
                # 默认处理
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
            return [f'{Left} {Op} {Right}']
        elif isinstance(Node, ast.BoolOp):
            # 处理逻辑运算符 and 和 or
            values = []
            for value in Node.values:
                values.append(self.HandleExpr(value)[0])
            if isinstance(Node.op, ast.And):
                # 将 and 转换为 &&
                return [' && '.join(values)]
            elif isinstance(Node.op, ast.Or):
                # 将 or 转换为 ||
                return [' || '.join(values)]
            else:
                return ['0']
        elif isinstance(Node, ast.UnaryOp):
            Operand = self.HandleExpr(Node.operand)[0]
            Op = self.GetUnaryOpSymbol(Node.op)
            # 直接返回一元运算符表达式，不做特殊处理
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
                # 特殊处理sizeof函数
                elif Func == 'sizeof':
                    if Args:
                        # 检查参数是否是t.CStruct调用
                        if Node.args and isinstance(Node.args[0], ast.Call):
                            arg_call = Node.args[0]
                            if isinstance(arg_call.func, ast.Attribute):
                                if isinstance(arg_call.func.value, ast.Name) and arg_call.func.value.id == 't':
                                    if arg_call.func.attr == 'CStruct':
                                        # 处理 sizeof(t.CStruct(NAME))
                                        if arg_call.args and isinstance(arg_call.args[0], ast.Name):
                                            struct_name = arg_call.args[0].id
                                            return [f'sizeof(struct {struct_name})']
                        # 普通sizeof处理
                        return [f'sizeof({Args[0]})']
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
                            return [f'printf({first_arg});', 'printf("\\n");']
                        else:
                            # 数值参数
                            # Python的print默认添加换行符
                            return [f'printf("%d\\n", {ArgsStr});']
                    return [f'printf("\\n");']
                # 普通函数调用
                return [f'{Func}({ArgsStr})']
        elif isinstance(Node, ast.Subscript):
            # 检查是否是后置自增模式: (k, k:=k+1)[0]
            if isinstance(Node.value, ast.Tuple) and len(Node.value.elts) == 2:
                elt0 = Node.value.elts[0]
                elt1 = Node.value.elts[1]
                if isinstance(elt0, ast.Name) and isinstance(elt1, ast.NamedExpr):
                    if elt0.id == elt1.target.id:
                        if isinstance(elt1.value, ast.BinOp) and isinstance(elt1.value.op, ast.Add):
                            if isinstance(elt1.value.left, ast.Name) and elt1.value.left.id == elt1.target.id:
                                if isinstance(elt1.value.right, ast.Constant) and elt1.value.right.value == 1:
                                    # 检查索引是否是0
                                    if isinstance(Node.slice, ast.Constant) and Node.slice.value == 0:
                                        # 优化为后置自增: k++
                                        return [f'{self.HandleExpr(elt0)[0]}++']
            
            # 处理普通数组访问，如 arr[j] 或 ctl.sheets[h]
            value = self.HandleExpr(Node.value)[0]
            index = self.HandleExpr(Node.slice)[0]
            
            # 检查是否是数组访问后的成员访问（如 ctl.sheets[h].height）
            # 如果是，需要检查数组元素类型是否是指针
            result = f'{value}[{index}]'
            return [result]
        elif isinstance(Node, ast.Tuple):
            # 处理逗号表达式，如 (a, b)
            elements = []
            for elt in Node.elts:
                elements.append(self.HandleExpr(elt)[0])
            elements_str = ', '.join(elements)
            return [f'({elements_str})']
        elif isinstance(Node, ast.List):
            # 处理数组初始化，如 [64, 34, 25, 12, 22, 11, 90]
            elements = []
            for elt in Node.elts:
                elements.append(self.HandleExpr(elt, use_single_quote=True)[0])
            elements_str = ', '.join(elements)
            return [f'{{{elements_str}}}']
        elif isinstance(Node, ast.Set):
            # 处理集合初始化，如 {3, 1, 0, 2}，转换为数组初始化
            elements = []
            for elt in Node.elts:
                elements.append(self.HandleExpr(elt, use_single_quote=True)[0])
            elements_str = ', '.join(elements)
            return [f'{{{elements_str}}}']
        elif isinstance(Node, ast.Compare):
            # 处理链式比较，如 a <= b <= c 转换为 (a <= b) && (b <= c)
            Comparisons = []
            Left = self.HandleExpr(Node.left)[0]
            for i, Op in enumerate(Node.ops):
                Comparator = self.GetComparatorSymbol(Op)
                Right = self.HandleExpr(Node.comparators[i])[0]
                Comparisons.append(f'{Left} {Comparator} {Right}')
                Left = Right  # 下一个比较的左操作数是当前的右操作数
            if len(Comparisons) == 1:
                return [Comparisons[0]]
            else:
                return [' && '.join(Comparisons)]
        elif isinstance(Node, ast.Attribute):
            # 处理属性访问，如 s.Value 或 self.led
            if isinstance(Node.value, ast.Name) and Node.value.id == 'c':
                # 处理c模块的属性访问，如 c.State
                attr = Node.attr
                return [f'c.{attr}']
            else:
                # 构建完整的属性访问链
                access_chain = []
                current_node = Node
                
                # 遍历属性访问链，获取完整的访问路径
                while isinstance(current_node, ast.Attribute):
                    access_chain.insert(0, current_node.attr)
                    current_node = current_node.value
                
                # 处理基础表达式
                if isinstance(current_node, ast.Name):
                    # 基础表达式是名称节点
                    base_var = current_node.id
                    
                    # 从符号表中查找基础变量的类型
                    current_struct_name = None
                    is_ptr = False
                    
                    # 特殊处理：如果基础变量是函数参数中的 self，它总是指针
                    if base_var == 'self':
                        is_ptr = True
                    # 从变量作用域中获取变量类型
                    else:
                        # 遍历所有作用域，查找变量类型
                        found = False
                        for scope in reversed(self.VarScopes):
                            if base_var in scope:
                                var_type = scope[base_var]
                                if var_type.startswith('struct '):
                                    # 提取结构体名称，去掉可能的指针符号
                                    struct_part = var_type.split(' ')[1]
                                    current_struct_name = struct_part.rstrip('*')
                                    # 检查是否是指针类型
                                    if '*' in var_type:
                                        is_ptr = True
                                elif '*' in var_type:
                                    # 处理指针类型
                                    type_parts = var_type.split('*')[0].strip()
                                    if type_parts.startswith('struct '):
                                        current_struct_name = type_parts.split(' ')[1]
                                    is_ptr = True
                                found = True
                                break
                        
                        # 如果作用域中没有找到，从符号表中查找
                        if not found:
                            if base_var in self.SymbolTable:
                                symbol_info = self.SymbolTable[base_var]
                                if symbol_info['type'] == 'variable':
                                    if 'is_pointer' in symbol_info:
                                        is_ptr = symbol_info['is_pointer']
                                    if 'declared_type' in symbol_info:
                                        declared_type = symbol_info['declared_type']
                                        if declared_type.startswith('struct '):
                                            # 提取结构体名称，去掉可能的指针符号
                                            struct_part = declared_type.split(' ')[1]
                                            current_struct_name = struct_part.rstrip('*')
                                            # 检查是否是指针类型
                                            if '*' in declared_type:
                                                is_ptr = True
                                        elif '*' in declared_type:
                                            type_parts = declared_type.split('*')[0].strip()
                                            if type_parts.startswith('struct '):
                                                current_struct_name = type_parts.split(' ')[1]
                                            is_ptr = True
                        
                        # 特殊处理：如果变量名是 cons 且在函数参数中，它总是指针
                        # 检查是否在函数参数作用域中
                        if base_var == 'cons':
                            # 检查当前作用域是否是函数作用域
                            if self.VarScopes:
                                # 函数参数通常在最内层作用域中
                                for scope in self.VarScopes:
                                    if base_var in scope:
                                        # 检查变量类型是否是指针
                                        var_type = scope[base_var]
                                        if '*' in var_type:
                                            is_ptr = True
                                        else:
                                            is_ptr = False
                                        break
                        
                        # 特殊处理：如果变量名是常见的指针变量名，默认视为指针
                        """if not is_ptr:
                            # 检查变量名是否在常见的指针变量名列表中（这是不合规的，暂且这么处理吧，也没啥问题）
                            if base_var in ['task', 'p', 'ptr', 'buf', 'memman', 'nihongo']:
                                is_ptr = True
                            # 检查变量名是否以 _ptr 结尾
                            elif base_var.endswith('_ptr'):
                                is_ptr = True
                            # 检查变量名是否包含 ptr
                            elif 'ptr' in base_var:
                                is_ptr = True"""
                    
                    # 构建完整的访问表达式
                    expr_parts = [base_var]
                    current_check_struct = current_struct_name
                    current_is_ptr = is_ptr  # 保存当前的指针状态
                    
                    # 遍历访问链，检查每一步的类型
                    for i in range(len(access_chain)):
                        member_name = access_chain[i]
                        
                        # 更新指针状态和结构体名
                        # 首先，尝试根据成员名推断类型
                        # 特殊处理常见的指针成员名
                        next_is_ptr = current_is_ptr  # 默认保持当前指针状态
                        is_member_pointer = False
                        
                        # 然后，从符号表中查找更准确的类型信息
                        if current_check_struct in self.SymbolTable:
                            struct_info = self.SymbolTable[current_check_struct]
                            if struct_info['type'] == 'struct' and 'members' in struct_info:
                                if member_name in struct_info['members']:
                                    # 检查当前成员是否是指针
                                    if struct_info['members'][member_name]['is_pointer']:
                                        next_is_ptr = True
                                        is_member_pointer = True
                                    else:
                                        next_is_ptr = False
                                        is_member_pointer = False
                                    # 更新检查的结构体名为当前成员的类型名
                                    member_type = struct_info['members'][member_name]['type']
                                    if member_type.startswith('struct '):
                                        # 提取结构体名称，去掉可能的指针符号
                                        struct_part = member_type.split(' ')[1]
                                        current_check_struct = struct_part.rstrip('*')
                                    elif '*' in member_type:
                                        type_parts = member_type.split('*')[0].strip()
                                        if type_parts.startswith('struct '):
                                            # 提取结构体名称，去掉可能的指针符号
                                            struct_part = type_parts.split(' ')[1]
                                            current_check_struct = struct_part.rstrip('*')
                        """# 如果结构体不在符号表中，但我们知道它是一个结构体类型
                        elif current_check_struct:
                            # 假设结构体成员的类型与成员名相关
                            # 例如，next 成员通常是指针
                            if member_name in ['next', 'prev', 'head', 'tail', 'ptr', 'buf', 'data', 'task', 'timer']:
                                next_is_ptr = True
                                is_member_pointer = True
                            else:
                                is_member_pointer = False
                            # 更新当前检查的结构体名
                            # 对于嵌套的结构体，我们假设成员类型是同名的结构体
                            if member_name in ['next', 'prev']:
                                current_check_struct = current_check_struct
                            else:
                                current_check_struct = member_name"""
                        
                        # 更新当前的指针状态，用于处理下一个成员
                        # 如果当前成员是指针类型，后续访问也使用指针运算符
                        # next_current_is_ptr 应该只基于成员是否是指针，而不是当前变量是否是指针
                        next_current_is_ptr = is_member_pointer
                        
                        # 特殊处理：根据符号表中的信息确定是否使用指针运算符
                        # 检查当前成员是否在符号表中定义为指针类型
                        if current_check_struct in self.SymbolTable:
                            struct_info = self.SymbolTable[current_check_struct]
                            if struct_info['type'] == 'struct' and 'members' in struct_info:
                                if member_name in struct_info['members']:
                                    if struct_info['members'][member_name]['is_pointer']:
                                        next_current_is_ptr = True
                        
                        # 根据当前成员是否是指针选择运算符
                        # 使用当前变量的指针状态来决定是否使用 -> 或 .
                        # is_member_pointer 只影响下一轮循环的 current_is_ptr，不影响当前运算符选择
                        if current_is_ptr:
                            expr_parts.append('->')
                        else:
                            expr_parts.append('.')
                        expr_parts.append(member_name)
                        
                        # 更新当前的指针状态，用于处理下一个成员
                        # 对于指针成员，后续访问也应该使用指针运算符
                        if is_member_pointer:
                            current_is_ptr = True
                        else:
                            current_is_ptr = next_current_is_ptr
                    
                    # 构建完整的表达式字符串
                    return [''.join(expr_parts)]
                else:
                    # 基础表达式不是名称节点，递归处理
                    base_expr = self.HandleExpr(current_node)[0]
                    
                    # 检查基础表达式是否是指针
                    is_ptr = False
                    # 检查 base_expr 是否以 & 开头（取地址操作）
                    if base_expr.startswith('&'):
                        is_ptr = True
                    # 检查 base_expr 是否以 * 开头（解引用操作）
                    elif base_expr.startswith('*'):
                        is_ptr = False
                    # 检查 base_expr 是否包含指针类型的特征
                    elif '*' in base_expr:
                        # 简单判断：如果包含 * 且不是乘法运算符，视为指针
                        if not (' * ' in base_expr or ' *(' in base_expr or ')* ' in base_expr):
                            is_ptr = True
                    
                    # 特殊处理：如果基础表达式是数组访问（如 sheets[x]）
                    # 需要检查数组元素类型是否是指针
                    if isinstance(current_node, ast.Subscript):
                        # 获取数组基础表达式（如 sheets）
                        array_base = current_node.value
                        if isinstance(array_base, ast.Attribute):
                            array_name = array_base.attr
                            struct_name = None
                            
                            # 从符号表中查找结构体信息
                            if array_base.value.id in self.SymbolTable:
                                symbol_info = self.SymbolTable[array_base.value.id]
                                if symbol_info['type'] == 'variable' and 'declared_type' in symbol_info:
                                    declared_type = symbol_info['declared_type']
                                    # 提取结构体名称
                                    if declared_type.startswith('struct '):
                                        struct_name = declared_type.split(' ')[1].rstrip('*')
                            
                            # 在变量作用域中查找
                            if not struct_name:
                                for scope in reversed(self.VarScopes):
                                    if array_base.value.id in scope:
                                        var_type = scope[array_base.value.id]
                                        if var_type.startswith('struct '):
                                            # 处理 'struct SHTCTL*' 或 'struct SHTCTL' 格式
                                            type_parts = var_type.split(' ')
                                            if len(type_parts) >= 2:
                                                struct_name = type_parts[1].rstrip('*')
                                        break
                            
                            # 从结构体定义中查找数组成员类型
                            if struct_name and struct_name in self.SymbolTable:
                                struct_info = self.SymbolTable[struct_name]
                                if struct_info['type'] == 'struct' and 'members' in struct_info:
                                    members = struct_info['members']
                                    if array_name in members:
                                        member = members[array_name]
                                        # 检查数组成员类型：
                                        # 1. 如果是数组（包含 '['）且元素是指针，则 array[i] 是指针
                                        # 2. 如果不是数组（如 FILEHANDLE* fhandle），则 ptr[i] 不是指针
                                        if 'type' in member and '[' in member['type']:
                                            # 是数组类型，检查元素是否是指针
                                            if 'is_pointer' in member and member['is_pointer']:
                                                is_ptr = True
                                            elif '*' in member['type']:
                                                is_ptr = True
                            
                            # 特殊处理：即使找不到变量类型，也检查是否是已知的结构体成员
                            # 这对于全局变量或未声明的变量（如 ctl）很有用
                            elif not struct_name:
                                # 尝试在所有结构体中查找成员名
                                for struct_name_iter, struct_info in self.SymbolTable.items():
                                    if struct_info['type'] == 'struct' and 'members' in struct_info:
                                        if array_name in struct_info['members']:
                                            member = struct_info['members'][array_name]
                                            # 检查数组成员类型
                                            if 'type' in member and '[' in member['type']:
                                                if 'is_pointer' in member and member['is_pointer']:
                                                    is_ptr = True
                                                elif '*' in member['type']:
                                                    is_ptr = True
                                            break
                    
                    # 处理访问链
                    result = base_expr
                    for attr in access_chain:
                        if is_ptr:
                            result += f'->{attr}'
                        else:
                            result += f'.{attr}'
                        
                        # 特殊处理：如果当前成员是常见的指针成员名，后续访问也使用指针运算符
                        if attr in ['next', 'prev', 'head', 'tail', 'ptr', 'buf', 'data', 'task', 'timer']:
                            is_ptr = True
                    
                    return [result]
        elif isinstance(Node, ast.IfExp):
            # 处理条件表达式（三目运算符），如 1 if eax else 2
            test = self.HandleExpr(Node.test)[0]
            body = self.HandleExpr(Node.body)[0]
            orelse = self.HandleExpr(Node.orelse)[0]
            return [f'({test} ? {body} : {orelse})']
        elif isinstance(Node, ast.NamedExpr):
            # 处理海象运算符（赋值表达式），如 (n := len(data))
            target = self.HandleExpr(Node.target)[0]
            value = self.HandleExpr(Node.value)[0]
            
            # 检查是否是前置自增模式: k := k + 1
            if isinstance(Node.value, ast.BinOp) and isinstance(Node.value.op, ast.Add):
                if isinstance(Node.value.left, ast.Name) and Node.value.left.id == Node.target.id:
                    if isinstance(Node.value.right, ast.Constant) and Node.value.right.value == 1:
                        # 优化为前置自增: ++k
                        return [f'++{target}']
            
            # 转换为C语言的逗号运算符：((target = value), target)
            return [f'(({target} = {value}), {target})']
        return ['0']
    
    def GetComparatorSymbol(self, Op):
        """获取比较运算符符号"""
        op_name = type(Op).__name__
        return COMPARATOR_MAP.get(op_name, '==')
    
    def GetOpSymbol(self, Op):
        """获取运算符符号"""
        op_name = type(Op).__name__
        return OPERATOR_MAP.get(op_name, '+')
    
    @debug_handle
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
        elif isinstance(Node.target, ast.Subscript):
            # 处理数组元素复合赋值，如 s[j] -= 0x20
            arr = self.HandleExpr(Node.target.value)[0]
            index = self.HandleExpr(Node.target.slice)[0]
            value = self.HandleExpr(Node.value)[0]
            op = self.GetAugOpSymbol(Node.op)
            if op:
                Code.append(f'{arr}[{index}] {op}= {value};')
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
                    found_in_scope = False
                    for scope in reversed(self.VarScopes):
                        if var_name in scope:
                            var_type = scope[var_name]
                            if '*' in var_type:
                                is_ptr = True
                            found_in_scope = True
                            break
                    # 如果作用域中没有找到，从符号表中查找
                    if not found_in_scope and var_name in self.SymbolTable:
                        symbol_info = self.SymbolTable[var_name]
                        if 'is_pointer' in symbol_info:
                            is_ptr = symbol_info['is_pointer']
                        elif 'declared_type' in symbol_info and '*' in symbol_info['declared_type']:
                            is_ptr = True
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
    
    def HandleBody(self, Body, in_block=False):
        """处理函数体
        
        Args:
            Body: 代码块节点列表
            in_block: 是否在块级作用域中（如if、for、while等块内）
        """
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
                            # 在非块级作用域中，检查变量是否已声明
                            if not in_block and self.VarScopes and var_name in self.VarScopes[-1]:
                                # 变量已存在，生成赋值语句而不是声明语句
                                Code.append(f'{var_name} = {ValueCode[0]};')
                                continue
                            # 在块级作用域中，每个块中的变量是独立的
                            # 所以直接生成声明语句
                            # 尝试获取类型名称
                            try:
                                type_name = self.GetTypeName(Node.annotation)
                                # 无论type_name是否为空，都生成声明语句
                                if type_name and type_name.strip():
                                    # 处理数组类型，提取数组大小
                                    base_type, array_size_str = extract_array_size(type_name)
                                    
                                    # 检查是否是数组指针类型，如 'const char (*)[16]'
                                    is_array_ptr = '(*)' in base_type
                                    
                                    # 检查是否是指针类型
                                    is_ptr = False
                                    original_base_type = base_type
                                    if '*' in base_type and not is_array_ptr:
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
                                    
                                    # 检查是否是基本类型
                                    is_basic_type = False
                                    basic_type_name = ''
                                    
                                    # 尝试从类型注解中获取类型信息
                                    annotation_str = ast.dump(Node.annotation)
                                    import re
                                    
                                    # 首先根据 type_name 检查是否是基本类型
                                    basic_types_map = {
                                        'int': 'int',
                                        'char': 'char',
                                        'float': 'float',
                                        'double': 'double',
                                        'void': 'void',
                                        'long': 'long',
                                        'short': 'short',
                                        'unsigned int': 'unsigned int',
                                        'unsigned char': 'unsigned char',
                                        'unsigned long': 'unsigned long',
                                        'unsigned short': 'unsigned short',
                                    }
                                    if type_name in basic_types_map:
                                        is_basic_type = True
                                        basic_type_name = basic_types_map[type_name]
                                    # 检查是否是基本类型组合（如 t.CUnsignedChar | t.CPtr）
                                    elif 'CUnsignedChar' in annotation_str:
                                        is_basic_type = True
                                        basic_type_name = 'unsigned char'
                                    elif 'CChar' in annotation_str:
                                        is_basic_type = True
                                        basic_type_name = 'char'
                                    elif 'CInt' in annotation_str:
                                        is_basic_type = True
                                        basic_type_name = 'int'
                                    elif 'CUnsignedInt' in annotation_str:
                                        is_basic_type = True
                                        basic_type_name = 'unsigned int'
                                    elif 'CLong' in annotation_str:
                                        is_basic_type = True
                                        basic_type_name = 'long'
                                    elif 'CUnsignedLong' in annotation_str:
                                        is_basic_type = True
                                        basic_type_name = 'unsigned long'
                                    elif 'CFloat' in annotation_str:
                                        is_basic_type = True
                                        basic_type_name = 'float'
                                    elif 'CDouble' in annotation_str:
                                        is_basic_type = True
                                        basic_type_name = 'double'
                                    elif 'CVoid' in annotation_str:
                                        is_basic_type = True
                                        basic_type_name = 'void'
                                    
                                    # 检查是否需要添加指针
                                    if is_basic_type and 'CPtr' in annotation_str:
                                        is_ptr = True
                                    
                                    # 如果不是基本类型，尝试从类型注解中获取结构体名称
                                    if not is_basic_type:
                                        # 检查是否是结构体类型（CStruct 或 CStruct | CPtr）
                                        if 'CStruct' in annotation_str:
                                            is_struct = True
                                            # 尝试提取结构体名称
                                            match = re.search(r'Name\(id=\"([A-Za-z0-9_]+)\"', annotation_str)
                                            if match:
                                                struct_name = match.group(1)
                                        elif base_type == 'struct':
                                            # 处理 t.CStruct 类型
                                            is_struct = True
                                            # 使用右侧表达式的名称作为结构体名（仅当是函数调用时）
                                            if isinstance(Node.value, ast.Call) and isinstance(Node.value.func, ast.Name):
                                                struct_name = Node.value.func.id
                                            else:
                                                # 如果右侧不是函数调用，使用默认结构体名
                                                struct_name = 'XXX'
                                        elif base_type == 'struct *':
                                            # 处理 t.CStruct | t.CPtr 类型
                                            is_struct = True
                                            is_ptr = True
                                            # 使用右侧表达式的名称作为结构体名（仅当是函数调用时）
                                            if isinstance(Node.value, ast.Call) and isinstance(Node.value.func, ast.Name):
                                                struct_name = Node.value.func.id
                                            else:
                                                # 如果右侧不是函数调用，使用默认结构体名
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
                                            # 使用右侧表达式的名称作为结构体名（仅当是函数调用时）
                                            if isinstance(Node.value, ast.Call) and isinstance(Node.value.func, ast.Name):
                                                struct_name = Node.value.func.id
                                            else:
                                                # 如果右侧不是函数调用，使用默认结构体名
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
                                        if is_basic_type:
                                            # 处理基本类型
                                            ptr_str = '*' if is_ptr else ''
                                            Code.append(f'{basic_type_name}{ptr_str} {var_name}{array_size_str};')
                                        elif is_struct and struct_name:
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
                                        self.debug_print(f"DEBUG ELSE: ValueCode[0]='{ValueCode[0]}', Node.value type={type(Node.value)}")
                                        # 优先检查是否是 t.CType 调用
                                        if isinstance(Node.value, ast.Call) and isinstance(Node.value.func, ast.Attribute):
                                            # 检查是否是 t.CType 调用
                                            if (isinstance(Node.value.func.value, ast.Name) and Node.value.func.value.id == 't' and 
                                                Node.value.func.attr == 'CType'):
                                                # 提取参数
                                                if len(Node.value.args) >= 1:
                                                    # 获取地址值
                                                    addr = self.HandleExpr(Node.value.args[0])[0]
                                                    # 生成类型转换代码
                                                    if is_basic_type:
                                                        # 处理基本类型
                                                        ptr_str = '*' if is_ptr else ''
                                                        Code.append(f'{basic_type_name}{ptr_str} {var_name}{array_size_str} = (({basic_type_name}{ptr_str}){addr});')
                                                    else:
                                                        # 获取结构体名称
                                                        struct_name = 'BOOTINFO'  # 默认值
                                                        # 尝试从第二个参数获取结构体名称
                                                        if len(Node.value.args) >= 2:
                                                            # 处理不同类型的第二个参数
                                                            if isinstance(Node.value.args[1], ast.Name):
                                                                # 变量名或类名
                                                                struct_name = Node.value.args[1].id
                                                            elif isinstance(Node.value.args[1], ast.Attribute):
                                                                # 处理属性访问，如 t.MEMMAN
                                                                struct_name = Node.value.args[1].attr
                                                        # 生成类型转换代码
                                                        Code.append(f'struct {struct_name}* {var_name}{array_size_str} = ((struct {struct_name} *){addr});')
                                                else:
                                                    # 生成普通指针声明
                                                    if is_basic_type:
                                                        # 处理基本类型
                                                        ptr_str = '*' if is_ptr else ''
                                                        Code.append(f'{basic_type_name}{ptr_str} {var_name}{array_size_str} = {ValueCode[0]};')
                                                    else:
                                                        Code.append(f'void* {var_name}{array_size_str} = {ValueCode[0]};')
                                            else:
                                                # 处理结构体类型，生成声明并调用构造函数
                                                if is_basic_type:
                                                    # 处理基本类型
                                                    ptr_str = '*' if is_ptr else ''
                                                    Code.append(f'{basic_type_name}{ptr_str} {var_name}{array_size_str} = {ValueCode[0]};')
                                                elif is_struct and struct_name:
                                                    if is_ptr:
                                                        # 直接生成带赋值的指针声明
                                                        Code.append(f'struct {struct_name}* {var_name}{array_size_str} = {ValueCode[0]};')
                                                    else:
                                                        # 检查右侧是否是c模块的函数调用
                                                        is_c_function = False
                                                        if isinstance(Node.value, ast.Call) and isinstance(Node.value.func, ast.Attribute):
                                                            if isinstance(Node.value.func.value, ast.Name) and Node.value.func.value.id == 'c':
                                                                is_c_function = True
                                                        
                                                        if is_c_function:
                                                            # 如果是c模块的函数调用，直接生成带赋值的声明
                                                            Code.append(f'struct {struct_name} {var_name}{array_size_str} = {ValueCode[0]};')
                                                        else:
                                                            Code.append(f'struct {struct_name} {var_name}{array_size_str};')
                                                            # 检查右侧是否是构造函数调用
                                                            if isinstance(Node.value, ast.Call):
                                                                # 检查是否是真正的结构体构造函数
                                                                # 只有当被调用的函数不是c模块的函数时，才可能是构造函数
                                                                is_c_function = False
                                                                if isinstance(Node.value.func, ast.Attribute):
                                                                    if isinstance(Node.value.func.value, ast.Name) and Node.value.func.value.id == 'c':
                                                                        is_c_function = True
                                                                
                                                                # 只有不是c模块的函数，才可能是构造函数
                                                                if not is_c_function:
                                                                    # 获取被调用的函数名
                                                                    called_func_name = None
                                                                    if isinstance(Node.value.func, ast.Name):
                                                                        called_func_name = Node.value.func.id
                                                                    elif isinstance(Node.value.func, ast.Attribute):
                                                                        called_func_name = Node.value.func.attr
                                                                     
                                                                    # 检查函数名是否与结构体名相同，并且结构体在符号表中明确标记为结构体
                                                                    if called_func_name == struct_name and struct_name in self.SymbolTable and self.SymbolTable[struct_name]['type'] == 'struct':
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
                                                    
                                                    # 处理数组指针类型，如 const char (*)[16] → const char (*var)[16]
                                                    if is_array_ptr:
                                                        # 对于数组指针，数组大小应该放在 ) 之后，变量名放在 (* 和 ) 之间
                                                        self.debug_print(f"DEBUG: is_array_ptr=True, base_type='{base_type}', type_part='{type_part}', array_size_str='{array_size_str}'")
                                                        if storage_class:
                                                            self.debug_print(type_part)
                                                            type_with_var = type_part.replace('(*)', f'(*{var_name})')
                                                            self.debug_print(f"DEBUG: storage_class='{storage_class}', type_with_var='{type_with_var}'")
                                                            Code.append(f'{storage_class} {type_with_var}{array_size_str} = {ValueCode[0]};')
                                                        else:
                                                            type_with_var = base_type.replace('(*)', f'(*{var_name})')
                                                            self.debug_print(f"DEBUG: no storage_class, type_with_var='{type_with_var}'")
                                                            Code.append(f'{type_with_var}{array_size_str} = {ValueCode[0]};')
                                                    elif storage_class:
                                                        # 处理带存储类修饰符的变量
                                                        Code.append(f'{storage_class} {type_part}{ptr_str} {var_name}{array_size_str} = {ValueCode[0]};')
                                                    else:
                                                        # 处理普通变量，包括指针类型
                                                        Code.append(f'{base_type}{ptr_str} {var_name}{array_size_str} = {ValueCode[0]};')
                                        # 检查是否已经识别为结构体类型
                                        elif is_struct and struct_name:
                                            # 处理结构体类型，生成声明并调用构造函数
                                            if is_ptr:
                                                # 直接生成带赋值的指针声明
                                                Code.append(f'struct {struct_name}* {var_name}{array_size_str} = {ValueCode[0]};')
                                            else:
                                                Code.append(f'struct {struct_name} {var_name}{array_size_str};')
                                                # 检查右侧是否是构造函数调用
                                                if isinstance(Node.value, ast.Call):
                                                    # 检查是否是真正的结构体构造函数
                                                    # 只有当被调用的函数不是c模块的函数时，才可能是构造函数
                                                    is_c_function = False
                                                    if isinstance(Node.value.func, ast.Attribute):
                                                        if isinstance(Node.value.func.value, ast.Name) and Node.value.func.value.id == 'c':
                                                            is_c_function = True
                                                    
                                                    # 只有不是c模块的函数，才可能是构造函数
                                                    if not is_c_function:
                                                        # 获取被调用的函数名
                                                        called_func_name = None
                                                        if isinstance(Node.value.func, ast.Name):
                                                            called_func_name = Node.value.func.id
                                                        elif isinstance(Node.value.func, ast.Attribute):
                                                            called_func_name = Node.value.func.attr
                                                        
                                                        # 检查函数名是否与结构体名相同，并且结构体在符号表中明确标记为结构体
                                                        if called_func_name == struct_name and struct_name in self.SymbolTable and self.SymbolTable[struct_name]['type'] == 'struct':
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
                                        # 检查右侧是否是执行格式（带括号）且类型注解包含自定义结构体或t.Struct
                                        elif isinstance(Node.value, ast.Call):
                                            # 检查是否是结构体构造函数调用
                                            struct_name = None
                                            if isinstance(Node.value.func, ast.Name):
                                                # 函数名作为结构体名
                                                struct_name = Node.value.func.id
                                            elif isinstance(Node.value.func, ast.Attribute):
                                                # 属性访问作为结构体名
                                                struct_name = Node.value.func.attr
                                            
                                            # 检查是否是结构体
                                            is_struct_call = False
                                            # 尝试从类型注解中获取结构体名称
                                            annotation_str = ast.dump(Node.annotation)
                                            struct_name_from_annotation = None
                                            
                                            # 查找类型注解中的结构体名称
                                            if 'Name(id=' in annotation_str:
                                                # 提取结构体名称
                                                import re
                                                match = re.search(r'Name\(id=\"([A-Za-z0-9_]+)\"', annotation_str)
                                                if match:
                                                    struct_name_from_annotation = match.group(1)
                                                    if struct_name_from_annotation:
                                                        struct_name = struct_name_from_annotation
                                            
                                            if struct_name:
                                                # 检查结构体是否在符号表中且明确记录为结构体类型
                                                if struct_name in self.SymbolTable and self.SymbolTable[struct_name]['type'] == 'struct':
                                                    is_struct_call = True
                                                # 如果结构体不在符号表中，但左侧是指针类型，也视为结构体
                                                elif is_ptr and base_type == '':
                                                    is_struct_call = True
                                            
                                            if is_struct_call:
                                                # 视为结构体声明且赋值
                                                if is_ptr:
                                                    Code.append(f'struct {struct_name}* {var_name}{array_size_str} = {ValueCode[0]};')
                                                else:
                                                    Code.append(f'struct {struct_name} {var_name}{array_size_str};')
                                                    # 检查是否是真正的结构体构造函数
                                                    # 只有当被调用的函数不是c模块的函数时，才可能是构造函数
                                                    is_c_function = False
                                                    if isinstance(Node.value.func, ast.Attribute):
                                                        if isinstance(Node.value.func.value, ast.Name) and Node.value.func.value.id == 'c':
                                                            is_c_function = True
                                                    
                                                    # 只有不是c模块的函数，才可能是构造函数
                                                    if not is_c_function:
                                                        # 获取被调用的函数名
                                                        called_func_name = None
                                                        if isinstance(Node.value.func, ast.Name):
                                                            called_func_name = Node.value.func.id
                                                        elif isinstance(Node.value.func, ast.Attribute):
                                                            called_func_name = Node.value.func.attr
                                                        
                                                        # 检查函数名是否与结构体名相同，并且结构体在符号表中明确标记为结构体
                                                        if called_func_name == struct_name and struct_name in self.SymbolTable and self.SymbolTable[struct_name]['type'] == 'struct':
                                                            # 生成构造函数调用
                                                            args = ['&' + var_name]
                                                            for arg in Node.value.args:
                                                                args.append(self.HandleExpr(arg)[0])
                                                            args_str = ', '.join(args)
                                                            Code.append(f'{struct_name}____init__({args_str});')
                                            else:
                                                # 生成普通声明
                                                # 检查 base_type 是否包含存储类修饰符
                                                storage_class, type_part = check_storage_class(base_type)
                                                
                                                # 处理指针类型
                                                ptr_str = '*' if is_ptr else ''
                                                
                                                if storage_class:
                                                    # 处理带存储类修饰符的变量
                                                    Code.append(f'{storage_class} {type_part}{ptr_str} {var_name}{array_size_str} = {ValueCode[0]};')
                                                else:
                                                    # 处理普通变量，包括指针类型
                                                    # 检查base_type是否是一个结构体名
                                                    if base_type in self.SymbolTable and self.SymbolTable[base_type]['type'] == 'struct':
                                                        # 如果是结构体名，在前面加上struct关键字
                                                        Code.append(f'struct {base_type}{ptr_str} {var_name}{array_size_str} = {ValueCode[0]};')
                                                    else:
                                                        # 否则，直接使用base_type
                                                        Code.append(f'{base_type}{ptr_str} {var_name}{array_size_str} = {ValueCode[0]};')
                                        else:
                                            # 生成普通声明
                                            # 检查 base_type 是否包含存储类修饰符
                                            storage_class, type_part = check_storage_class(base_type)
                                            
                                            # 处理指针类型
                                            ptr_str = '*' if is_ptr else ''
                                            
                                            if storage_class:
                                                # 处理带存储类修饰符的变量
                                                Code.append(f'{storage_class} {type_part}{ptr_str} {var_name}{array_size_str} = {ValueCode[0]};')
                                            else:
                                                # 处理普通变量，包括指针类型
                                                # 检查base_type是否是一个结构体名
                                                if base_type in self.SymbolTable and self.SymbolTable[base_type]['type'] == 'struct':
                                                    # 如果是结构体名，在前面加上struct关键字
                                                    Code.append(f'struct {base_type}{ptr_str} {var_name}{array_size_str} = {ValueCode[0]};')
                                                else:
                                                    # 否则，直接使用base_type
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
                        else:
                            try:
                                type_name = self.GetTypeName(Node.annotation)
                                # 无论type_name是否为空，都生成声明语句
                                if type_name and type_name.strip():
                                    # 处理数组类型，提取数组大小
                                    base_type, array_size_str = extract_array_size(type_name)
                                    
                                    # 检查是否是数组指针类型，如 'const char (*)[16]'
                                    is_array_ptr = '(*)' in base_type
                                    
                                    # 检查 base_type 是否包含存储类修饰符
                                    storage_class, type_part = check_storage_class(base_type)
                                    
                                    # 处理数组指针类型，如 const char (*)[16] → const char (*var)[16]
                                    if is_array_ptr:
                                        if storage_class:
                                            type_with_var = type_part.replace('(*)', f'(*{var_name})')
                                            Code.append(f'{storage_class} {type_with_var}{array_size_str};')
                                        else:
                                            type_with_var = base_type.replace('(*)', f'(*{var_name})')
                                            Code.append(f'{type_with_var}{array_size_str};')
                                    elif storage_class:
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
            elif hasattr(ast, 'Match') and isinstance(Node, ast.Match):
                # 处理 Python 3.10+ 的 match 语句
                Code.extend(self.HandleMatch(Node))
        return Code
    
    @debug_handle
    def HandleMatch(self, Node):
        """处理 match 语句，转换为 C 的 switch 语句"""
        Code = []
        
        # 获取 match 的表达式
        subject = self.HandleExpr(Node.subject)[0]
        
        # 生成 switch 语句
        Code.append(f'switch ({subject}) {{')
        
        # 跟踪是否已经生成了 default
        has_default = False
        # 收集所有不支持的模式，最后统一生成一个 default
        unsupported_patterns = []
        
        # 第一遍：处理所有支持的 case
        for case in Node.cases:
            # 获取 case 的模式
            pattern = case.pattern
            
            # 处理不同的 pattern 类型
            case_generated = False
            
            if isinstance(pattern, ast.MatchValue):
                # 简单的值匹配，如 case 2:
                value = self.HandleExpr(pattern.value)[0]
                Code.append(f'    case {value}:')
                case_generated = True
            elif isinstance(pattern, ast.MatchOr):
                # 或模式，如 case 3 | 4:
                for i, sub_pattern in enumerate(pattern.patterns):
                    if isinstance(sub_pattern, ast.MatchValue):
                        value = self.HandleExpr(sub_pattern.value)[0]
                        Code.append(f'    case {value}:')
                case_generated = True
            elif isinstance(pattern, ast.MatchSingleton):
                # 单例模式，如 case None:
                if pattern.value is None:
                    Code.append('    case 0:  /* None */')
                elif pattern.value is True:
                    Code.append('    case 1:  /* True */')
                elif pattern.value is False:
                    Code.append('    case 0:  /* False */')
                case_generated = True
            elif isinstance(pattern, ast.MatchSequence):
                # 序列模式（列表或元组），如 case [6, 7, 8]:
                # 在 C 语言中，为每个元素生成一个 case 标签
                for sub_pattern in pattern.patterns:
                    if isinstance(sub_pattern, ast.MatchValue):
                        value = self.HandleExpr(sub_pattern.value)[0]
                        Code.append(f'    case {value}:')
                    elif isinstance(sub_pattern, ast.MatchSingleton):
                        # 处理 None, True, False
                        if sub_pattern.value is None:
                            Code.append('    case 0:  /* None */')
                        elif sub_pattern.value is True:
                            Code.append('    case 1:  /* True */')
                        elif sub_pattern.value is False:
                            Code.append('    case 0:  /* False */')
                case_generated = True
            elif isinstance(pattern, ast.MatchAs):
                # 命名模式或通配符模式
                if pattern.pattern is None:
                    # 通配符模式，如 case _: 或 case (k):
                    # 检查是否有变量名
                    if pattern.name and pattern.name != '_':
                        # 命名模式，如 case (k):
                        # 在 C 中不支持变量捕获，最后统一生成 default
                        unsupported_patterns.append((pattern.name, case.body))
                    else:
                        # 真正的通配符模式，如 case _:
                        has_default = True
                        Code.append('    default:')
                        case_generated = True
                else:
                    # 命名模式带值，如 case 1 as k:
                    if isinstance(pattern.pattern, ast.MatchValue):
                        value = self.HandleExpr(pattern.pattern.value)[0]
                        Code.append(f'    case {value}:')
                        # 如果有变量名，添加赋值
                        if pattern.name:
                            Code.append(f'        {pattern.name} = {subject};')
                        case_generated = True
                    else:
                        # 不支持的命名模式
                        unsupported_patterns.append((pattern.name, case.body))
            else:
                # 其他不支持的 pattern 类型，如 MatchList, MatchMapping 等
                unsupported_patterns.append((None, case.body))
            
            # 处理 case 的 body（只处理已生成的 case）
            if case_generated and case.body:
                # 在 C 语言中，case 标签后如果有变量声明，需要用花括号包裹
                # 为了安全起见，总是添加花括号
                Code.append('        {')
                body_code = self.HandleBody(case.body, in_block=True)
                # 缩进 body 代码
                for line in body_code:
                    Code.append('            ' + line)
                
                # 如果没有 break，添加 break（C 语言 switch 需要）
                # 检查最后一个语句是否已经是 break
                if not (len(case.body) == 1 and isinstance(case.body[0], ast.Break)):
                    Code.append('            break;')
                Code.append('        }')
        
        # 第二遍：处理所有不支持的 pattern，统一生成一个 default
        if unsupported_patterns and not has_default:
            Code.append('    default:')
            Code.append('        {')
            for var_name, body in unsupported_patterns:
                if var_name:
                    Code.append(f'            {var_name} = {subject};')
                if body:
                    body_code = self.HandleBody(body, in_block=True)
                    for line in body_code:
                        Code.append('            ' + line)
            Code.append('            break;')
            Code.append('        }')
        
        Code.append('}')
        return Code
    
    @debug_handle
    def HandleIf(self, Node):
        """处理if语句"""
        Code = []
        Test = self.HandleExpr(Node.test)[0]
        # C语言中if条件必须加括号
        Code.append('if (' + Test + ') {')
        # 处理if语句体，确保正确缩进，传入in_block=True表示在块级作用域中
        body_code = self.HandleBody(Node.body, in_block=True)
        # if语句体内部的语句应该再缩进4个空格
        Code.extend(['    ' + line for line in body_code])
        Code.append('}')
        if Node.orelse:
            # 处理else部分
            current_else = Node.orelse
            while len(current_else) == 1 and isinstance(current_else[0], ast.If):
                # 这是一个elif情况
                elif_node = current_else[0]
                elif_test = self.HandleExpr(elif_node.test)[0]
                # C语言中if条件必须加括号
                Code.append('else if (' + elif_test + ') {')
                # 处理elif语句体，传入in_block=True表示在块级作用域中
                elif_body_code = self.HandleBody(elif_node.body, in_block=True)
                Code.extend(['    ' + line for line in elif_body_code])
                Code.append('}')
                # 移到下一个else部分，可能是另一个elif或最后的else
                current_else = elif_node.orelse
            
            # 处理最后的else部分（如果有）
            if current_else:
                Code.append('else {')
                else_code = self.HandleBody(current_else, in_block=True)
                Code.extend(['    ' + line for line in else_code])
                Code.append('}')
        return Code
    
    @debug_handle
    def HandleFor(self, Node):
        """处理for语句"""
        Code = []
        
        # 检查是否是字符串切片遍历模式: for char in cmdline[6:]
        is_string_slice = False
        var_name = None
        base_var = None
        start_index = 0
        
        if isinstance(Node.target, ast.Name):
            var_name = Node.target.id
            # 检查是否是字符串切片表达式
            if isinstance(Node.iter, ast.Subscript):
                # 检查是否是简单的字符串切片，如 cmdline[6:]
                if isinstance(Node.iter.value, ast.Name) and isinstance(Node.iter.slice, ast.Slice):
                    base_var = Node.iter.value.id
                    # 检查是否有起始索引
                    if Node.iter.slice.lower:
                        start_index = self.HandleExpr(Node.iter.slice.lower)[0]
                    else:
                        start_index = '0'
                    is_string_slice = True
        
        if is_string_slice and var_name and base_var:
            # 生成字符串切片遍历的for循环
            Code.append(f'for (int __for_i = {start_index}; {base_var}[__for_i] != \'\\0\'; __for_i++) {{')
            # 添加字符变量声明
            Code.append(f'    char {var_name} = {base_var}[__for_i];')
            # 处理循环体，传入in_block=True表示在块级作用域中
            Code.extend(['    ' + line for line in self.HandleBody(Node.body, in_block=True)])
            Code.append('}')
            return Code
        
        # 检查是否是直接字符串遍历模式: for c in name
        is_string_iter = False
        var_name = None
        base_var = None
        
        if isinstance(Node.target, ast.Name):
            var_name = Node.target.id
            # 检查是否是简单的变量名（字符串）
            if isinstance(Node.iter, ast.Name):
                base_var = Node.iter.id
                is_string_iter = True
        
        if is_string_iter and var_name and base_var:
            # 生成字符串遍历的for循环
            Code.append(f'for (int __for_i = 0; {base_var}[__for_i] != 0; __for_i++) {{')
            # 添加字符变量声明
            Code.append(f'    char {var_name} = {base_var}[__for_i];')
            # 处理循环体，传入in_block=True表示在块级作用域中
            Code.extend(['    ' + line for line in self.HandleBody(Node.body, in_block=True)])
            Code.append('}')
            return Code
        
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
                # 确定循环条件运算符
                if step == '-1' or step == '-1L' or step == '-1l' or step == '-1LL' or step == '-1ll' or step == '-1.0':
                    # 负步长，使用大于运算符
                    condition_op = '>'
                else:
                    # 正步长，使用小于运算符
                    condition_op = '<'
                # 检查start是否与var_name相同（例如 for i in range(i, ...)
                if start == var_name:
                    # start与循环变量相同，省略初始化部分
                    Code.append(f'for (; {var_name} {condition_op} {stop}; {var_name} += {step}) {{')
                # 检查循环变量是否已经在作用域中声明
                elif self.VarScopes and var_name in self.VarScopes[-1]:
                    # 变量已存在，在for循环头中赋值（不重新定义类型）
                    Code.append(f'for ({var_name} = {start}; {var_name} {condition_op} {stop}; {var_name} += {step}) {{')
                else:
                    # 变量未声明，在for循环头中定义
                    Code.append(f'for (int {var_name} = {start}; {var_name} {condition_op} {stop}; {var_name} += {step}) {{')
                Code.extend(['    ' + line for line in self.HandleBody(Node.body, in_block=True)])
                Code.append('}')
                return Code
        
        # 默认处理
        Code.append('for (...) {')
        Code.extend(['    ' + line for line in self.HandleBody(Node.body, in_block=True)])
        Code.append('}')
        return Code
    
    @debug_handle
    def HandleWhile(self, Node):
        """处理while语句"""
        Code = []
        
        # 检查是否是do-while模式: while True: ... if not condition: break
        is_do_while = False
        condition = None
        
        if isinstance(Node.test, ast.Constant) and Node.test.value is True:
            # 检查循环体最后是否有一个if语句，并且if语句中有break
            if Node.body:
                last_stmt = Node.body[-1]
                if isinstance(last_stmt, ast.If):
                    # 检查if语句是否有else分支
                    if not last_stmt.orelse:
                        # 检查if语句体是否只有一个break语句
                        if len(last_stmt.body) == 1 and isinstance(last_stmt.body[0], ast.Break):
                            # 提取条件
                            condition = last_stmt.test
                            is_do_while = True
        
        if is_do_while and condition:
            # 生成do-while循环
            Code.append('do {')
            # 处理循环体（除了最后的if-break语句），传入in_block=True表示在块级作用域中
            body_code = []
            for stmt in Node.body[:-1]:  # 排除最后的if语句
                body_code.extend(self.HandleBody([stmt], in_block=True))
            # 处理if语句之前的部分（如果有的话）
            if body_code:
                Code.extend(['    ' + line for line in body_code])
            # 生成while条件 - 取反条件，因为原代码是"if条件则break"，所以循环应继续当条件为假
            condition_code = self.HandleExpr(condition)[0]
            # 只有对于已经整体带括号的表达式，不再添加外层括号
            # C语言中while条件必须加括号
            Code.append('} while (!(' + condition_code + '));')
        else:
            # 生成普通while循环
            Test = self.HandleExpr(Node.test)[0]
            # C语言中while条件必须加括号
            Code.append('while (' + Test + ') {')
            body_code = self.HandleBody(Node.body, in_block=True)
            Code.extend(['    ' + line for line in body_code])
            Code.append('}')
        
        return Code
    
    @debug_handle
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
            # 检查是否是基本类型名称（如CChar, CInt等）
            basic_types = ['CChar', 'CUnsignedChar', 'CInt', 'CUnsignedInt', 'CShort', 'CUnsignedShort', 'CLong', 'CUnsignedLong', 'CFloat', 'CDouble', 'CVoid', 'CPtr']
            if type_name in basic_types:
                from lib.constants.config import TYPE_MAP
                if type_name in TYPE_MAP:
                    return TYPE_MAP[type_name]
                elif type_name == 'CPtr':
                    return '*'
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
            # 处理 const 修饰符
            elif left_type == 'const':
                return f'const {right_type}'
            elif right_type == 'const':
                return f'const {left_type}'
            # 处理 volatile 修饰符
            elif left_type == 'volatile':
                return f'volatile {right_type}'
            elif right_type == 'volatile':
                return f'volatile {left_type}'
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
            # 处理数组指针类型，如 t.CConst | t.CChar[16] | t.CArrayPtr
            elif right_type == '(*)':
                # 数组指针：将数组大小移到括号外，如 const char[16] | (*) → const char (*)[16]
                if '[' in left_type:
                    type_part = left_type.split('[')[0]
                    array_part = left_type[left_type.find('['):]
                    return f'{type_part} (*){array_part}'
                return f'{left_type} (*)'
            elif left_type == '(*)':
                if '[' in right_type:
                    type_part = right_type.split('[')[0]
                    array_part = right_type[right_type.find('['):]
                    return f'{type_part} (*){array_part}'
                return f'{right_type} (*)'
            # 处理自定义类型与指针类型的组合，如 CONSOLE | t.CPtr
            elif right_type == '*' and left_type != 'int':
                if left_type.startswith('struct '):
                    return left_type + '*'
                # 检查是否是基本类型（char, int, etc.）或包含基本类型（如 const char）
                basic_types = ['char', 'int', 'short', 'long', 'float', 'double', 'unsigned char', 'unsigned int', 'unsigned short', 'unsigned long']
                if any(left_type.startswith(bt) for bt in basic_types) or any(bt in left_type for bt in basic_types):
                    # 处理数组类型与指针的组合，如 const char[16] | t.CPtr
                    if '[' in left_type:
                        type_part = left_type.split('[')[0]
                        array_part = left_type[left_type.find('['):]
                        return f'{type_part}*{array_part}'
                    return f'{left_type}*'
                else:
                    # 检查是否已经包含 'struct '（如 'extern struct TASKCTL'）
                    if 'struct ' in left_type:
                        return f'{left_type}*'
                    return f'struct {left_type}*'
            elif left_type == '*' and right_type != 'int':
                if right_type.startswith('struct '):
                    # 处理数组类型与指针的组合，如 struct SHEET[MAX_SHEETS] | t.CPtr
                    if '[' in right_type:
                        # 提取结构体名称和数组大小
                        struct_name = right_type.split('[')[0]  # 'struct SHEET'
                        array_part = right_type[right_type.find('['):]  # '[MAX_SHEETS]'
                        return f'{struct_name} *{array_part}'
                    return right_type + '*'
                # 检查是否是基本类型（char, int, etc.）或包含基本类型（如 const char）
                basic_types = ['char', 'int', 'short', 'long', 'float', 'double', 'unsigned char', 'unsigned int', 'unsigned short', 'unsigned long']
                if any(right_type.startswith(bt) for bt in basic_types) or any(bt in right_type for bt in basic_types):
                    # 处理数组类型与指针的组合
                    if '[' in right_type:
                        type_part = right_type.split('[')[0]
                        array_part = right_type[right_type.find('['):]
                        return f'{type_part}*{array_part}'
                    return f'{right_type}*'
                else:
                    # 处理数组类型与指针的组合
                    if '[' in right_type:
                        type_part = right_type.split('[')[0]
                        array_part = right_type[right_type.find('['):]
                        return f'struct {type_part} *{array_part}'
                    return f'struct {right_type}*'
            # 处理结构体指针类型
            elif (left_type == 'struct' and right_type == '*') or (left_type == '*' and right_type == 'struct'):
                return 'struct *'
            # 处理结构体名称与指针类型的组合，如 NODE | t.CPtr
            elif left_type.startswith('struct ') and right_type == '*':
                return left_type + '*'
            elif right_type.startswith('struct ') and left_type == '*':
                return right_type + '*'
            # 处理自定义类型与指针类型的组合，如 CONSOLE | t.CPtr
            elif right_type == '*' and not left_type.startswith('struct ') and left_type != 'int':
                return f'struct {left_type}*'
            elif left_type == '*' and not right_type.startswith('struct ') and right_type != 'int':
                return f'struct {right_type}*'
            # 处理自定义类型与指针类型的组合，如 SHEET | t.CPtr
            elif right_type == '*':
                # 自定义类型与指针的组合，返回结构体指针
                # 检查是否是基本类型（char, int, etc.）
                basic_types = ['char', 'int', 'short', 'long', 'float', 'double', 'unsigned char', 'unsigned int', 'unsigned short', 'unsigned long']
                if any(left_type.startswith(bt) for bt in basic_types) or '[' in left_type:
                    # 对于基本类型或数组类型，添加指针
                    if '[' in left_type:
                        # 处理数组类型与指针的组合，如 t.CChar[60] | t.CPtr
                        type_part = left_type.split('[')[0]
                        array_part = left_type[left_type.find('['):]
                        return f'{type_part}*{array_part}'
                    # 对于基本类型，添加指针
                    return f'{left_type}*'
                return f'struct {left_type}*'
            elif left_type == '*':
                # 指针与自定义类型的组合，返回结构体指针
                # 检查是否是基本类型（char, int, etc.）
                basic_types = ['char', 'int', 'short', 'long', 'float', 'double', 'unsigned char', 'unsigned int', 'unsigned short', 'unsigned long']
                if any(right_type.startswith(bt) for bt in basic_types) or '[' in right_type:
                    # 对于基本类型或数组类型，添加指针
                    if '[' in right_type:
                        # 处理指针与数组类型的组合，如 t.CPtr | t.CChar[60]
                        type_part = right_type.split('[')[0]
                        array_part = right_type[right_type.find('['):]
                        return f'{type_part}*{array_part}'
                    # 对于基本类型，添加指针
                    return f'{right_type}*'
                return f'struct {right_type}*'
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
            # 处理无符号长整型的组合
            elif (left_type == 'unsigned int' and right_type == 'long') or (left_type == 'long' and right_type == 'unsigned int'):
                return 'unsigned long'
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
        # 导入TYPE_MAP
        from lib.constants.config import TYPE_MAP
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
                # 特殊处理：如果类型字符串包含'struct'但实际上是基本类型，移除'struct'
                if type_str.startswith('struct '):
                    # 检查是否是基本类型
                    basic_types = ['CChar', 'CUnsignedChar', 'CInt', 'CUnsignedInt', 'CShort', 'CUnsignedShort', 'CLong', 'CUnsignedLong', 'CFloat', 'CDouble', 'CVoid']
                    type_name = type_str[7:]  # 移除'struct '
                    if any(basic_type in type_name for basic_type in basic_types):
                        # 如果是基本类型，使用正确的C类型
                        for basic_type in basic_types:
                            if basic_type in type_name:
                                if basic_type in TYPE_MAP:
                                    type_str = TYPE_MAP[basic_type]
                                    # 检查是否需要添加指针
                                    if 'CPtr' in type_name:
                                        type_str += '*'
                                    break
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
                    # 处理多行字符串，将每行用 "\n\t" 连接起来
                    lines = asm_code.strip().split('\n')
                    if len(lines) > 1:
                        # 多行汇编代码，生成期望的格式
                        # 每行后面添加 \n\t，最后一行不加
                        formatted_lines = '\\n\\t"\n        "'.join(lines)
                        return [f'__asm__ volatile (\n        "{formatted_lines}"\n    );']
                    else:
                        # 单行汇编代码
                        return [f'__asm__ volatile ("{asm_code}");']
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
                            return [f'__asm__ volatile ({asm_code} : : "a"({params[0]}), "d"({params[1]}));']
                    return ['__asm__ volatile ("nop");']
                else:
                    return ['__asm__ volatile ("nop");']
            return ['__asm__ volatile ("nop");']
        elif attr == 'Memory':
            # 处理c.Memory()调用
            if args:
                if isinstance(args[0], ast.Constant):
                    addr = args[0].value
                    return [f'((void *){addr})']
        elif attr == 'Set':
            # 处理c.Set(a, b)调用，等价于a = b
            if len(args) >= 2:
                target = self.HandleExpr(args[0])[0]
                value = self.HandleExpr(args[1])[0]
                return [f'{target} = {value};']
            return []
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
        elif attr == 'Cast':
            # 处理c.Cast()调用，翻译为解引用指针
            if args:
                expr = self.HandleExpr(args[0])[0]
                return [f'*({expr})']
            return ['0']
        elif attr == 'Set':
            # 处理c.Set()调用，翻译为指针解引用赋值
            if len(args) >= 2:
                address = self.HandleExpr(args[0])[0]
                value = self.HandleExpr(args[1])[0]
                return [f'*((void*){address}) = {value};']
            return ['0']
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