# TransPyC 入口程序

import sys
import os
import ast
import json
import struct
# 添加lib目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib', 'includes'))
import c
import t
from lib.constants.config import (
    DEFAULT_INPUT_FILE, DEFAULT_OUTPUT_FILE,
    SUPPORTED_FILE_TYPES, DEFAULT_COMPILE_COMMAND,
    DEFAULT_COMPILE_FLAGS, ERROR_MESSAGES,
    HELP_MESSAGE, GENERATE_Copyright
)
from lib.utils.helpers import (
    detect_file_type, execute_command,
    get_file_content, write_file_content,
    append_file_content, validate_args
)
from lib.core.translator import Translator


def serialize_symbol_table(symbol_table: dict) -> bytes:
    """将符号表序列化为二进制格式
    
    格式: 
    - 4字节: JSON数据长度（小端序）
    - N字节: JSON数据（UTF-8编码）
    
    Args:
        symbol_table: 符号表字典
        
    Returns:
        二进制字节数据
    """
    json_data = json.dumps(symbol_table, ensure_ascii=False).encode('utf-8')
    length = len(json_data)
    # 使用4字节小端序整数表示长度
    header = struct.pack('<I', length)
    return header + json_data


def deserialize_symbol_table(data: bytes) -> dict:
    """从二进制数据反序列化符号表
    
    Args:
        data: 二进制字节数据
        
    Returns:
        符号表字典
    """
    if len(data) < 4:
        raise ValueError("Invalid symbin file: data too short")
    # 解析4字节长度头（小端序）
    length = struct.unpack('<I', data[:4])[0]
    json_data = data[4:4+length]
    return json.loads(json_data.decode('utf-8'))


class SymbolFile:
    """符号文件类，用于解析和存储符号信息"""
    
    def __init__(self, file=None, string=None, type=None, encoding='utf-8'):
        """初始化SymbolFile对象
        
        Args:
            file: 文件路径
            string: 代码字符串
            type: 文件类型，支持"c"或"py"
            encoding: 文件编码
        """
        self.file_path = file
        self.code_string = string
        self.file_type = type
        self.encoding = encoding
        self.symbols = {}



class Config:
    """配置类"""
    def __init__(self):
        self.debug = False


class TransPyC:
    """TransPyC 主类"""
    
    def __init__(self, code=None, debug=False):
        """初始化TransPyC对象
        
        Args:
            code: 代码字符串
            debug: 调试模式
        """
        self.Args = {}
        self.HeaderFiles = []
        self.HelperFiles = []  # 辅助文件列表，用于解析符号信息
        self.translator = Translator()  # 代码转换器
        self.code = code
        self.translator.Content = code
        self.config = Config()
        self.config.debug = debug
        self.symbol_files = []  # 符号文件列表
    
    @staticmethod
    def PreProcessSymbol(symbol_file, debug=False):
        """预处理符号文件，提取符号表并返回二进制数据
        
        Args:
            symbol_file: SymbolFile对象，包含文件路径和类型信息
            debug: 是否启用调试模式，如果为True，返回 (bytes, debug_info)
                  对于Python文件，debug_info包含p2c日志
                  对于C文件，debug_info包含基本处理信息
                  
        Returns:
            如果debug为False: bytes - 序列化后的符号表二进制数据
            如果debug为True: (bytes, str) - (二进制数据, 调试日志)
        """
        translator = Translator()
        debug_logs = []
        
        try:
            # 读取文件内容
            if symbol_file.file_path:
                with open(symbol_file.file_path, 'r', encoding=symbol_file.encoding) as f:
                    content = f.read()
            elif symbol_file.code_string:
                content = symbol_file.code_string
            else:
                raise ValueError("SymbolFile must have either file_path or code_string")
            
            # 根据文件类型处理
            file_type = symbol_file.file_type
            if not file_type and symbol_file.file_path:
                # 从文件路径推断类型
                if symbol_file.file_path.endswith('.py'):
                    file_type = 'py'
                elif symbol_file.file_path.endswith('.c') or symbol_file.file_path.endswith('.h'):
                    file_type = 'c'
            
            if file_type == 'py':
                # Python文件处理
                translator.OriginalLines = content.split('\n')
                translator.Content = content
                
                # 设置调试文件（如果需要）
                if debug:
                    debug_file = symbol_file.file_path.replace('.py', '.p2c') if symbol_file.file_path else 'debug.p2c'
                    translator.set_debug_file(debug_file)
                    # 清空调试文件
                    with open(debug_file, 'w', encoding=symbol_file.encoding) as f:
                        f.write('')
                
                # 解析AST并提取符号
                tree = ast.parse(content)
                
                if debug:
                    with open(debug_file, 'a', encoding=symbol_file.encoding) as f:
                        f.write('=== AST Tree (Compact) ===\n')
                        f.write(ast.dump(tree))
                        f.write('\n\n')
                
                # 遍历AST提取符号
                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.ClassDef):
                        translator.SymbolTable[node.name] = {'type': 'struct', 'members': {}}
                        for item in node.body:
                            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                                var_name = item.target.id
                                var_type = translator.GetTypeName(item.annotation) if item.annotation else 'unknown'
                                is_pointer = '*' in var_type or 'CPtr' in var_type
                                translator.SymbolTable[node.name]['members'][var_name] = {
                                    'type': var_type,
                                    'is_pointer': is_pointer
                                }
                    elif isinstance(node, ast.FunctionDef):
                        translator.SymbolTable[node.name] = {'type': 'function'}
                    elif isinstance(node, ast.AnnAssign):
                        if isinstance(node.target, ast.Name):
                            var_name = node.target.id
                            var_type = 'unknown'
                            is_pointer = False
                            if node.annotation:
                                try:
                                    var_type = translator.GetTypeName(node.annotation)
                                    is_pointer = '*' in var_type or 'CPtr' in var_type
                                except:
                                    pass
                            translator.SymbolTable[var_name] = {
                                'type': 'variable', 
                                'declared_type': var_type, 
                                'is_pointer': is_pointer
                            }
                
                if debug:
                    with open(debug_file, 'a', encoding=symbol_file.encoding) as f:
                        f.write('=== Symbol Table ===\n')
                        f.write(str(translator.SymbolTable))
                        f.write('\n\n')
                    # 读取调试日志
                    with open(debug_file, 'r', encoding=symbol_file.encoding) as f:
                        debug_logs = f.read()
                
            elif file_type == 'c':
                # C文件处理 - 使用现有的ParseHelperFiles逻辑
                translator.ParseHelperFiles([symbol_file.file_path], symbol_file.encoding)
                
                if debug:
                    debug_logs = f"=== C File Symbol Extraction ===\n"
                    debug_logs += f"File: {symbol_file.file_path}\n"
                    debug_logs += f"=== Symbol Table ===\n"
                    debug_logs += str(translator.SymbolTable)
                    debug_logs += "\n\n"
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # 序列化符号表
            binary_data = serialize_symbol_table(translator.SymbolTable)
            
            if debug:
                return binary_data, debug_logs
            return binary_data
            
        except Exception as e:
            error_msg = f"Error processing symbol file: {e}"
            if debug:
                return b'', error_msg
            raise RuntimeError(error_msg)
    
    def ParseArgs(self):
        """解析命令行参数"""
        I = 1
        while I < len(sys.argv):
            if sys.argv[I] == '-f':
                if I + 1 < len(sys.argv):
                    self.Args['Input'] = sys.argv[I + 1]
                    I += 2
                else:
                    print(f'Error: -f requires an argument')
                    sys.exit(1)
            elif sys.argv[I] == '-o':
                if I + 1 < len(sys.argv):
                    self.Args['Output'] = sys.argv[I + 1]
                    I += 2
                else:
                    print(f'Error: -o requires an argument')
                    sys.exit(1)
            elif sys.argv[I] == '-wh':
                if I + 1 < len(sys.argv):
                    self.HeaderFiles = sys.argv[I + 1:]
                    break
                else:
                    print(f'Error: -wh requires arguments')
                    sys.exit(1)
            elif sys.argv[I] == '-debug':
                if I + 1 < len(sys.argv):
                    self.Args['Debug'] = sys.argv[I + 1]
                    I += 2
                else:
                    print(f'Error: -debug requires an argument')
                    sys.exit(1)
            elif sys.argv[I] == '-cc':
                # 编译命令
                if I + 1 < len(sys.argv):
                    self.Args['CompileCommand'] = sys.argv[I + 1]
                    I += 2
                else:
                    print(f'Error: -cc requires an argument')
                    sys.exit(1)
            elif sys.argv[I] == '-cflags':
                # 编译标志
                if I + 1 < len(sys.argv):
                    self.Args['CompileFlags'] = sys.argv[I + 1]
                    I += 2
                else:
                    print(f'Error: -cflags requires an argument')
                    sys.exit(1)
            elif sys.argv[I] == '-run':
                # 是否运行生成的程序
                self.Args['Run'] = True
                I += 1
            elif sys.argv[I] == '-args':
                # 运行时参数
                if I + 1 < len(sys.argv):
                    self.Args['RunArgs'] = sys.argv[I + 1]
                    I += 2
                else:
                    print(f'Error: -args requires an argument')
                    sys.exit(1)
            elif sys.argv[I] == '-h':
                # 辅助文件，用于解析符号信息
                if I + 1 < len(sys.argv):
                    # 收集所有后续参数作为辅助文件，直到遇到下一个以-开头的参数
                    while I + 1 < len(sys.argv) and not sys.argv[I + 1].startswith('-'):
                        self.HelperFiles.append(sys.argv[I + 1])
                        I += 1
                    I += 1
                else:
                    print(f'Error: -h requires arguments')
                    sys.exit(1)
            elif sys.argv[I] == '-presym':
                # 预处理符号文件，生成.symbin文件
                # 格式: -presym <input_file> -o <output_file> [-debug <debug_file>]
                if I + 1 < len(sys.argv):
                    input_file = sys.argv[I + 1]
                    I += 2
                    
                    # 解析可选参数
                    output_file = None
                    debug_file = None
                    while I < len(sys.argv) and sys.argv[I].startswith('-'):
                        if sys.argv[I] == '-o':
                            if I + 1 < len(sys.argv):
                                output_file = sys.argv[I + 1]
                                I += 2
                            else:
                                print(f'Error: -o requires an argument')
                                sys.exit(1)
                        elif sys.argv[I] == '-debug':
                            if I + 1 < len(sys.argv):
                                debug_file = sys.argv[I + 1]
                                I += 2
                            else:
                                print(f'Error: -debug requires an argument')
                                sys.exit(1)
                        else:
                            break
                    
                    # 如果没有指定输出文件，使用默认名称
                    if not output_file:
                        output_file = input_file.replace('.py', '.symbin').replace('.c', '.symbin')
                    
                    # 执行预处理
                    self.Args['PreSym'] = {
                        'input': input_file,
                        'output': output_file,
                        'debug': debug_file
                    }
                else:
                    print(f'Error: -presym requires an argument')
                    sys.exit(1)
            elif sys.argv[I] == '-e' or sys.argv[I] == '--encoding':
                # 编码参数
                if I + 1 < len(sys.argv):
                    self.Args['Encoding'] = sys.argv[I + 1]
                    I += 2
                else:
                    print(f'Error: -e/--encoding requires an argument')
                    sys.exit(1)
            else:
                print(f'Error: Unknown argument {sys.argv[I]}')
                sys.exit(1)
        
        # 检查是否有预处理符号文件的请求，如果有则跳过输入输出检查
        if 'PreSym' not in self.Args and ('Input' not in self.Args or 'Output' not in self.Args):
            print(ERROR_MESSAGES['MISSING_ARGS'])
            print(HELP_MESSAGE)
            sys.exit(1)
    
    def CompileAndRun(self, OutputFile):
        """编译并运行生成的C代码"""
        # 获取编译命令
        compile_cmd = self.Args.get('CompileCommand', DEFAULT_COMPILE_COMMAND)
        compile_flags = self.Args.get('CompileFlags', DEFAULT_COMPILE_FLAGS)
        
        # 构建编译命令
        full_compile_cmd = f'{compile_cmd} {compile_flags} {OutputFile} -o {OutputFile}.exe'
        print(f'Compiling: {full_compile_cmd}')
        
        # 执行编译命令
        try:
            compile_result = execute_command(full_compile_cmd)
            if compile_result:
                print('Compilation successful!')
                
                # 检查是否需要运行
                if self.Args.get('Run', False):
                    run_args = self.Args.get('RunArgs', '')
                    run_cmd = f'{OutputFile}.exe {run_args}'.strip()
                    print(f'Running: {run_cmd}')
                    
                    # 执行运行命令
                    run_result = execute_command(run_cmd)
                    if run_result:
                        print('Execution output:')
                        print(run_result.stdout)
                        if run_result.stderr:
                            print('Execution errors:')
                            print(run_result.stderr)
        except Exception as e:
            print(f'{ERROR_MESSAGES["COMPILE_FAILED"]}: {e}')
    
    def WriteDebugInfo(self, content):
        """写入调试信息到指定文件"""
        # 获取调试文件路径
        if 'Debug' in self.Args:
            debug_file = self.Args['Debug']
        else:
            debug_file = self.Args.get('Output', '').replace('.c', '.p2c')
        
        if debug_file:
            append_file_content(debug_file, content)
    
    def PythonToC(self, InputFile, OutputFile):
        """Python到C的转换"""
        # 获取编码参数
        encoding = self.Args.get('Encoding', 'utf-8')
        
        # 设置调试文件路径（使用 .p2c 扩展名）
        if 'Debug' in self.Args:
            debug_file = self.Args['Debug']
        else:
            # 默认使用 .p2c 文件
            debug_file = OutputFile.replace('.c', '.p2c')
        
        # 设置翻译器的调试文件
        self.translator.set_debug_file(debug_file)
        
        # 先清空调试文件
        with open(debug_file, 'w', encoding=encoding) as f:
            f.write('')
        
        # 解析辅助文件，提取符号信息
        if self.HelperFiles:
            self.translator.ParseHelperFiles(self.HelperFiles, encoding)
        
        # 获取编码参数
        encoding = self.Args.get('Encoding', 'utf-8')
        with open(InputFile, 'r', encoding=encoding) as F:
            Content = F.read()
        
        # 保存原始代码行
        self.translator.OriginalLines = Content.split('\n')
        self.translator.Content = Content
        
        # 解析Python代码为AST
        Tree = ast.parse(Content)
        
        # 写入AST树信息（压缩格式）
        with open(debug_file, 'a', encoding=encoding) as f:
            f.write('=== AST Tree (Compact) ===\n')
            f.write(ast.dump(Tree))
            f.write('\n\n')
        
        CCode = self.translator.GenerateCCode(Tree)
        
        encoding = self.Args.get('Encoding', 'utf-8')
        with open(OutputFile, 'w', encoding=encoding) as F:
            F.write(f'{GENERATE_Copyright}\n')
            F.write(CCode)
            F.write('\n')
    
    def CToPython(self, InputFile, OutputFile, HeaderFiles):
        """C到Python的转换（暂时禁用）"""
        print("C到Python的转换功能暂时禁用，请使用Python到C的转换功能。")
    
    def AddSymbol(self, symbol_files):
        """添加符号文件
        
        Args:
            symbol_files: 符号文件或符号文件列表
        """
        if isinstance(symbol_files, list):
            self.symbol_files.extend(symbol_files)
        else:
            self.symbol_files.append(symbol_files)
        
        # 收集文件路径和编码
        helper_files = []
        encodings = []
        for symbol_file in self.symbol_files:
            file_path = symbol_file.file_path
            encoding = symbol_file.encoding
            if file_path:
                helper_files.append(file_path)
                encodings.append(encoding)
        
        # 解析辅助文件
        if helper_files:
            # 暂时使用第一个文件的编码
            encoding = encodings[0] if encodings else 'utf-8'
            self.translator.ParseHelperFiles(helper_files, encoding)
    
    def Convert(self):
        """转换代码
        
        Returns:
            如果debug是字符串，则返回生成的C代码
            如果debug是True，则返回生成的C代码和调试信息
        """
        if not self.code:
            print('Error: No code provided')
            return None
        
        # 保存原始代码行
        self.translator.OriginalLines = self.code.split('\n')
        
        # 解析Python代码为AST
        Tree = ast.parse(self.code)
        
        # 生成C代码
        CCode = self.translator.GenerateCCode(Tree)
        CCode = f'{GENERATE_Copyright}\n{CCode}\n'
        
        # 处理调试信息
        if isinstance(self.config.debug, str):
            # 如果debug是字符串，写入调试信息到文件
            with open(self.config.debug, 'w', encoding='utf-8') as f:
                f.write('=== Symbol Table ===\n')
                f.write(str(self.translator.SymbolTable) + '\n\n')
                f.write('=== AST Tree ===\n')
                f.write(ast.dump(Tree, indent=2) + '\n\n')
                f.write('=== Generated Code ===\n')
                f.write(CCode + '\n')
            return CCode
        elif self.config.debug:
            # 如果debug是True，返回生成的C代码和调试信息
            debug_info = {
                'symbol_table': self.translator.SymbolTable,
                'ast_tree': ast.dump(Tree, indent=2),
                'generated_code': CCode
            }
            return CCode, debug_info
        else:
            # 如果debug是False，只返回生成的C代码
            return CCode
    
    def Run(self):
        """主运行函数"""
        # 检查是否有命令行参数
        if len(sys.argv) > 1:
            # 有命令行参数，使用 ParseArgs 方法解析
            self.ParseArgs()
            
            # 检查是否有预处理符号文件的请求
            if 'PreSym' in self.Args:
                presym_config = self.Args['PreSym']
                input_file = presym_config['input']
                output_file = presym_config['output']
                debug_file = presym_config['debug']
                
                # 获取编码参数
                encoding = self.Args.get('Encoding', 'utf-8')
                
                # 推断文件类型
                file_type = 'py' if input_file.endswith('.py') else 'c' if input_file.endswith('.c') else None
                
                # 创建 SymbolFile 对象，传入编码参数
                symbol_file = SymbolFile(file=input_file, type=file_type, encoding=encoding)
                
                # 调用 PreProcessSymbol
                if debug_file:
                    binary_data, debug_info = TransPyC.PreProcessSymbol(symbol_file, debug=True)
                    # 写入调试文件
                    with open(debug_file, 'w', encoding=encoding) as f:
                        f.write(debug_info)
                    print(f"Debug info written to: {debug_file}")
                else:
                    binary_data = TransPyC.PreProcessSymbol(symbol_file, debug=False)
                
                # 写入二进制符号文件
                with open(output_file, 'wb') as f:
                    f.write(binary_data)
                
                print(f"Symbol file generated: {output_file}")
                return
            
            input_file = self.Args['Input']
            output_file = self.Args['Output']
        else:
            # 没有命令行参数，使用默认的测试文件名称
            input_file = DEFAULT_INPUT_FILE
            output_file = DEFAULT_OUTPUT_FILE
            print('Using default test files: test.py -> test.c')
        
        file_type = detect_file_type(input_file)

        if file_type == '.py':
            self.PythonToC(input_file, output_file)
            # 检查是否需要编译和运行
            if 'CompileCommand' in self.Args or self.Args.get('Run', False):
                self.CompileAndRun(output_file)
        elif file_type == '.c':
            self.CToPython(input_file, output_file, self.HeaderFiles)
        else:
            print(f'Error: Unsupported file type {file_type}')
            sys.exit(1)


if __name__ == '__main__':
    trans = TransPyC()
    trans.Run()
