"""
导入处理 Mixin
"""

from .base import HandleMixin


class ImportMixin(HandleMixin):
    """导入处理 Mixin"""
    
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
