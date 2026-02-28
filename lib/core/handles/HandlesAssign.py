import ast
from lib.core.Handles.HandlesBase import BaseHandle, debug_handle


class AssignHandle(BaseHandle):
    def __init__(self, translator):
        super().__init__(translator)

    @debug_handle
    def HandleAssign(self, Node):
        Code = []
        if isinstance(Node.targets[0], ast.Tuple) and isinstance(Node.value, ast.Tuple):
            targets = Node.targets[0].elts
            values = Node.value.elts
            if len(targets) == 2 and len(values) == 2:
                temp_var = "temp"
                Code.append(f'int {temp_var};')
                target1_code = self.HandleExpr(targets[0])[0]
                target2_code = self.HandleExpr(targets[1])[0]
                Code.append(f'{temp_var} = {target1_code};')
                Code.append(f'{target1_code} = {target2_code};')
                Code.append(f'{target2_code} = {temp_var};')
                return Code

        for Target in Node.targets:
            if isinstance(Target, ast.Name):
                ValueCode = self.HandleExpr(Node.value)
                if ValueCode:
                    var_name = Target.id
                    var_declared = False
                    for scope in reversed(self.Trans.VarScopes):
                        if var_name in scope:
                            var_declared = True
                            break

                    if not var_declared and var_name in self.Trans.SymbolTable:
                        symbol_info = self.Trans.SymbolTable[var_name]
                        if symbol_info['type'] == 'variable':
                            var_declared = True

                    if var_declared:
                        Code.append(f'{var_name} = {ValueCode[0]};')
                    else:
                        var_type = 'int'
                        if hasattr(Node, 'annotation') and Node.annotation:
                            var_type = self.GetTypeName(Node.annotation)

                        struct_name = None
                        is_pointer = False
                        if isinstance(Node.value, ast.Attribute):
                            access_chain = []
                            current_node = Node.value
                            while isinstance(current_node, ast.Attribute):
                                access_chain.insert(0, current_node.attr)
                                current_node = current_node.value
                            if isinstance(current_node, ast.Name):
                                access_chain.insert(0, current_node.id)

                            if len(access_chain) >= 2:
                                current_type = access_chain[0]
                                if current_type in self.Trans.SymbolTable:
                                    base_info = self.Trans.SymbolTable[current_type]
                                    if base_info['type'] == 'variable' and 'is_pointer' in base_info:
                                        is_pointer = base_info['is_pointer']
                                    for i in range(1, len(access_chain)):
                                        member_name = access_chain[i]
                                        if current_type in self.Trans.SymbolTable:
                                            struct_info = self.Trans.SymbolTable[current_type]
                                            if struct_info['type'] == 'struct' and 'members' in struct_info:
                                                members = struct_info['members']
                                                if member_name in members:
                                                    member_is_ptr = members[member_name]['is_pointer']
                                                    if i == len(access_chain) - 1:
                                                        is_pointer = member_is_ptr
                                                    current_type = members[member_name]['type']
                                                    if current_type.startswith('struct '):
                                                        current_type = current_type.split(' ')[1]
                                                    elif '*' in current_type:
                                                        type_parts = current_type.split('*')[0].strip()
                                                        if type_parts.startswith('struct '):
                                                            current_type = type_parts.split(' ')[1]
                        elif isinstance(Node.value, ast.Call):
                            if isinstance(Node.value.func, ast.Name):
                                func_name = Node.value.func.id
                                if func_name in ['len', 'print', 'range']:
                                    var_type = 'int'
                                elif func_name in self.Trans.FunctionReturnTypes:
                                    var_type = self.Trans.FunctionReturnTypes[func_name]
                                    if '*' in var_type:
                                        is_pointer = True
                                elif func_name in self.Trans.SymbolTable:
                                    symbol_info = self.Trans.SymbolTable[func_name]
                                    if symbol_info['type'] == 'struct':
                                        struct_name = func_name
                                    else:
                                        var_type = 'int'
                                else:
                                    var_type = 'int'

                        if isinstance(Node.value, ast.List):
                            elements = []
                            for elt in Node.value.elts:
                                elements.append(self.HandleExpr(elt)[0])
                            elements_str = ', '.join(elements)
                            Code.append(f'{var_type} {var_name}[] = {{ {elements_str} }};')
                            if self.Trans.VarScopes:
                                self.Trans.VarScopes[-1][var_name] = var_type
                        else:
                            if struct_name:
                                Code.append(f'struct {struct_name} {var_name};')
                                if isinstance(Node.value, ast.Call):
                                    args = ['&' + var_name]
                                    for arg in Node.value.args:
                                        args.append(self.HandleExpr(arg)[0])
                                    args_str = ', '.join(args)
                                    Code.append(f'{struct_name}____init__({args_str});')
                                if self.Trans.VarScopes:
                                    self.Trans.VarScopes[-1][var_name] = f'struct {struct_name}'
                            else:
                                if is_pointer:
                                    Code.append(f'{var_type}* {var_name} = {ValueCode[0]};')
                                else:
                                    Code.append(f'{var_type} {var_name} = {ValueCode[0]};')
                                if self.Trans.VarScopes:
                                    if is_pointer:
                                        self.Trans.VarScopes[-1][var_name] = f'{var_type}*'
                                    else:
                                        self.Trans.VarScopes[-1][var_name] = var_type
            elif isinstance(Target, ast.Attribute):
                obj_expr = Target.value
                obj_name = None
                last_member_name = None

                current = obj_expr
                while isinstance(current, ast.Attribute):
                    last_member_name = current.attr
                    current = current.value
                if isinstance(current, ast.Name):
                    obj_name = current.id

                obj = self.HandleExpr(obj_expr)[0]
                attr = Target.attr
                ValueCode = self.HandleExpr(Node.value)
                if ValueCode:
                    is_pointer = False
                    if obj == 'self':
                        is_pointer = True

                    if last_member_name and obj_name:
                        var_type = None
                        for scope in reversed(self.Trans.VarScopes):
                            if obj_name in scope:
                                var_type = scope[obj_name]
                                break

                        if not var_type and obj_name in self.Trans.SymbolTable:
                            base_info = self.Trans.SymbolTable[obj_name]
                            if base_info['type'] == 'variable' and 'declared_type' in base_info:
                                var_type = base_info['declared_type']

                        if var_type and var_type.startswith('struct '):
                            struct_name = var_type.split(' ')[1].rstrip('*')
                            if struct_name in self.Trans.SymbolTable:
                                struct_info = self.Trans.SymbolTable[struct_name]
                                if struct_info['type'] == 'struct' and 'members' in struct_info:
                                    if last_member_name in struct_info['members']:
                                        member_info = struct_info['members'][last_member_name]
                                        if isinstance(obj_expr, ast.Attribute):
                                            if not member_info.get('is_pointer'):
                                                is_pointer = False

                    if is_pointer:
                        Code.append(f'{obj}->{attr} = {ValueCode[0]};')
                    else:
                        Code.append(f'{obj}.{attr} = {ValueCode[0]};')
            elif isinstance(Target, ast.Subscript):
                arr = self.HandleExpr(Target.value)[0]
                index = self.HandleExpr(Target.slice)[0]
                ValueCode = self.HandleExpr(Node.value)
                if ValueCode:
                    Code.append(f'{arr}[{index}] = {ValueCode[0]};')
        return Code
