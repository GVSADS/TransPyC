import ast
from lib.core.Handles.HandlesBase import BaseHandle, debug_handle


class AnnAssignHandle(BaseHandle):
    def __init__(self, translator):
        super().__init__(translator)

    @debug_handle
    def HandleAnnAssign(self, Node):
        Code = []
        if isinstance(Node.target, ast.Name):
            var_name = Node.target.id
            ValueCode = self.HandleExpr(Node.value)
            if ValueCode:
                if self.Trans.VarScopes and var_name in self.Trans.VarScopes[-1]:
                    Code.append(f'{var_name} = {ValueCode[0]};')
                    return Code
                try:
                    type_name = self.GetTypeName(Node.annotation)
                    if type_name:
                        base_type, array_size_str = self.Trans.extract_array_size(type_name)

                        if isinstance(Node.value, ast.List):
                            elements = []
                            for elt in Node.value.elts:
                                elements.append(self.HandleExpr(elt, use_single_quote=True)[0])
                            elements_str = ', '.join(elements)
                            Code.append(f'{base_type} {var_name}{array_size_str} = {{ {elements_str} }};')
                        else:
                            if ValueCode[0] == 'c.State':
                                if base_type == '*':
                                    if isinstance(Node.value, ast.Name):
                                        type_name = Node.value.id
                                        Code.append(f'struct {type_name}* {var_name}{array_size_str};')
                                    else:
                                        Code.append(f'void* {var_name}{array_size_str};')
                                else:
                                    Code.append(f'{base_type} {var_name}{array_size_str};')
                            else:
                                Code.append(f'{base_type} {var_name}{array_size_str} = {ValueCode[0]};')

                        if self.Trans.VarScopes:
                            self.Trans.VarScopes[-1][var_name] = type_name
                    else:
                        if isinstance(Node.value, ast.List):
                            elements = []
                            for elt in Node.value.elts:
                                elements.append(self.HandleExpr(elt)[0])
                            elements_str = ', '.join(elements)
                            Code.append(f'int {var_name}[] = {{ {elements_str} }};')
                        else:
                            Code.append(f'int {var_name} = {ValueCode[0]};')
                        if self.Trans.VarScopes:
                            self.Trans.VarScopes[-1][var_name] = 'int'
                except Exception as e:
                    print(f'Warning: Failed to get type annotation: {e}')
                    if isinstance(Node.value, ast.List):
                        elements = []
                        for elt in Node.value.elts:
                            elements.append(self.HandleExpr(elt)[0])
                        elements_str = ', '.join(elements)
                        Code.append(f'int {var_name}[] = {{ {elements_str} }};')
                    else:
                        Code.append(f'int {var_name} = {ValueCode[0]};')
                    if self.Trans.VarScopes:
                        self.Trans.VarScopes[-1][var_name] = 'int'
        return Code
