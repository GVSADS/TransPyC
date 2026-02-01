# TransPyC 入口程序

import sys
import os
import ast
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


class TransPyC:
    """TransPyC 主类"""
    
    def __init__(self):
        self.Args = {}
        self.HeaderFiles = []
        self.HelperFiles = []  # 辅助文件列表，用于解析符号信息
        self.translator = Translator()  # 代码转换器
    
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
            else:
                print(f'Error: Unknown argument {sys.argv[I]}')
                sys.exit(1)
        
        if 'Input' not in self.Args or 'Output' not in self.Args:
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
        if 'Debug' in self.Args:
            debug_file = self.Args['Debug']
            append_file_content(debug_file, content)
    
    def PythonToC(self, InputFile, OutputFile):
        """Python到C的转换"""
        # 解析辅助文件，提取符号信息
        if self.HelperFiles:
            self.translator.ParseHelperFiles(self.HelperFiles)
            # 写入调试信息
            if 'Debug' in self.Args:
                debug_file = self.Args['Debug']
                # 先清空调试文件
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write('=== Symbol Table ===\n')
                    f.write(str(self.translator.SymbolTable) + '\n\n')
        
        with open(InputFile, 'r', encoding='utf-8') as F:
            Content = F.read()
        
        # 保存原始代码行
        self.translator.OriginalLines = Content.split('\n')
        
        # 写入调试信息
        self.WriteDebugInfo(f'=== TransPyC Debug Info ===')
        self.WriteDebugInfo(f'Input File: {InputFile}')
        self.WriteDebugInfo(f'Output File: {OutputFile}')
        self.WriteDebugInfo(f'File Content:\n{Content}')
        
        # 解析Python代码为AST
        Tree = ast.parse(Content)
        
        # 写入AST树信息
        self.WriteDebugInfo(f'=== AST Tree ===')
        self.WriteDebugInfo(ast.dump(Tree, indent=2))
        
        CCode = self.translator.GenerateCCode(Tree)
        
        # 写入生成的代码
        self.WriteDebugInfo(f'=== Generated Code ===')
        self.WriteDebugInfo(CCode)
        
        with open(OutputFile, 'w', encoding='utf-8') as F:
            F.write(f'{GENERATE_Copyright}\n')
            F.write(CCode)
    
    def CToPython(self, InputFile, OutputFile, HeaderFiles):
        """C到Python的转换（暂时禁用）"""
        print("C到Python的转换功能暂时禁用，请使用Python到C的转换功能。")
    
    def Run(self):
        """主运行函数"""
        # 检查是否有命令行参数
        if len(sys.argv) > 1:
            # 有命令行参数，使用 ParseArgs 方法解析
            self.ParseArgs()
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
