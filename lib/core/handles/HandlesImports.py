import ast
from lib.core.Handles.HandlesBase import BaseHandle, debug_handle


class ImportHandle(BaseHandle):
    def __init__(self, translator):
        super().__init__(translator)

    @debug_handle
    def HandleImport(self, Node):
        Code = []
        line_number = getattr(Node, 'lineno', None)
        
        if line_number and hasattr(self.Trans, 'OriginalLines') and 0 <= line_number - 1 < len(self.Trans.OriginalLines):
            original_line = self.Trans.OriginalLines[line_number - 1]
            if '# skip' in original_line:
                return Code
            if '#include' in original_line:
                include_part = original_line.split('#include', 1)[1].strip()
                return [f'#include {include_part}']
            if '# std: annotation' in original_line:
                for Alias in Node.names:
                    if Alias.name not in ['c', 't']:
                        self.Trans._LoadAnnotationModule(Alias.name)
                return Code
        
        for Alias in Node.names:
            if Alias.name not in ['c', 't']:
                is_standard = False
                is_annotation = False
                if line_number and hasattr(self.Trans, 'OriginalLines') and 0 <= line_number - 1 < len(self.Trans.OriginalLines):
                    original_line = self.Trans.OriginalLines[line_number - 1]
                    if '# std: standard' in original_line:
                        is_standard = True
                    if '# std: annotation' in original_line:
                        is_annotation = True
                
                if is_annotation:
                    self.Trans.AnnotationModules.add(Alias.name)
                
                if Alias.name == 'stdio' or is_standard:
                    Code.append(f'#include <{Alias.name.replace(".", "/")}.h>')
                else:
                    Code.append(f'#include "{Alias.name.replace(".", "/")}.h"')
        return Code

    @debug_handle
    def HandleImportFrom(self, Node):
        if Node.module not in ['c', 't']:
            if hasattr(Node, 'lineno') and hasattr(self.Trans, 'OriginalLines'):
                line_number = Node.lineno - 1
                if 0 <= line_number < len(self.Trans.OriginalLines):
                    original_line = self.Trans.OriginalLines[line_number]
                    if '# skip' in original_line:
                        return []
                    if '# std: annotation' in original_line and Node.module:
                        self.Trans.AnnotationModules.add(Node.module)
                        self.Trans._LoadAnnotationModule(Node.module)
                        return []
            
            include_directive = None
            if hasattr(Node, 'lineno') and hasattr(self.Trans, 'OriginalLines'):
                line_number = Node.lineno - 1
                if 0 <= line_number < len(self.Trans.OriginalLines):
                    original_line = self.Trans.OriginalLines[line_number]
                    if '#include' in original_line:
                        include_part = original_line.split('#include', 1)[1].strip()
                        include_directive = f'#include {include_part}'
            
            if include_directive:
                return [include_directive]
            
            full_module_path = '.' * Node.level
            if Node.module:
                full_module_path += Node.module
            
            import_comment = f'from {full_module_path} import '
            if Node.names:
                if len(Node.names) == 1 and Node.names[0].name == '*':
                    import_comment += '*'
                else:
                    import_comment += ', '.join([alias.name for alias in Node.names])
            else:
                import_comment += '...'
            
            if full_module_path.startswith('.'):
                parts = full_module_path.split('.')
                level = 0
                while level < len(parts) and parts[level] == '':
                    level += 1
                relative_path = '../' * (level - 1)
                if level < len(parts):
                    relative_path += '/'.join(parts[level:])
                header_path = relative_path + '.h'
            else:
                header_path = full_module_path.replace('.', '/') + '.h'
            return [f'#include "{header_path}" // {import_comment}']
        return []
