import ast
from lib.core.Handles.HandlesBase import BaseHandle, debug_handle


class ClassHandle(BaseHandle):
    def __init__(self, translator):
        super().__init__(translator)

    @debug_handle
    def HandleClassDef(self, Node):
        Code = []
        
        is_typedef = False
        typedef_name = None
        
        if hasattr(Node, 'annotation') and Node.annotation:
            try:
                annotation_str = ast.dump(Node.annotation)
                if 'CTypedef' in annotation_str:
                    is_typedef = True
                    if isinstance(Node.annotation, ast.Call):
                        if Node.annotation.args:
                            if isinstance(Node.annotation.args[0], ast.Constant):
                                typedef_name = Node.annotation.args[0].value
            except Exception as e:
                print(f'Warning: Failed to parse class annotation: {e}')
        
        if not is_typedef:
            for item in Node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id == '__annotations__':
                            if isinstance(item.value, ast.Dict):
                                for key, value in zip(item.value.keys, item.value.values):
                                    if isinstance(key, ast.Constant) and key.value == '__type__':
                                        value_str = ast.dump(value)
                                        if 'CTypedef' in value_str:
                                            is_typedef = True
                                            if isinstance(value, ast.Call):
                                                if value.args:
                                                    if isinstance(value.args[0], ast.Constant):
                                                        typedef_name = value.args[0].value
        
        if Node.name not in self.Trans.SymbolTable:
            if is_typedef:
                typedef_key = typedef_name if typedef_name else Node.name
                self.Trans.SymbolTable[typedef_key] = {'type': 'typedef', 'original_type': f'struct {Node.name}'}
                if Node.name != typedef_key:
                    self.Trans.SymbolTable[Node.name] = {'type': 'struct'}
            else:
                self.Trans.SymbolTable[Node.name] = {'type': 'struct'}
        else:
            if is_typedef:
                typedef_key = typedef_name if typedef_name else Node.name
                if typedef_key not in self.Trans.SymbolTable or self.Trans.SymbolTable[typedef_key]['type'] != 'typedef':
                    self.Trans.SymbolTable[typedef_key] = {'type': 'typedef', 'original_type': f'struct {Node.name}'}
                if Node.name != typedef_key and (Node.name not in self.Trans.SymbolTable or self.Trans.SymbolTable[Node.name]['type'] != 'struct'):
                    self.Trans.SymbolTable[Node.name] = {'type': 'struct'}
        
        Code.append(f'struct {Node.name} {{')
        
        for item in Node.body:
            if isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name):
                    var_name = item.target.id
                    try:
                        type_name = self.GetTypeName(item.annotation)
                        if type_name and type_name.strip():
                            is_struct = False
                            is_ptr = False
                            struct_name = None
                            base_type = type_name
                            
                            if base_type == 'struct *':
                                is_struct = True
                                is_ptr = True
                                if item.value:
                                    if isinstance(item.value, ast.Name):
                                        struct_name = item.value.id
                                    elif isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name):
                                        struct_name = item.value.func.id
                                    else:
                                        struct_name = 'XXX'
                            elif base_type == 'struct':
                                is_struct = True
                                if item.value:
                                    if isinstance(item.value, ast.Name):
                                        struct_name = item.value.id
                                    elif isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name):
                                        struct_name = item.value.func.id
                                    else:
                                        struct_name = 'XXX'
                            
                            if is_struct and struct_name:
                                if is_ptr:
                                    Code.append(f'    struct {struct_name}* {var_name};')
                                else:
                                    Code.append(f'    struct {struct_name} {var_name};')
                            else:
                                if '[' in type_name and ']' in type_name:
                                    base_type = type_name.split('[')[0]
                                    array_size = type_name[type_name.find('['):]
                                    if base_type.endswith('*'):
                                        base_type = base_type[:-1].strip()
                                        Code.append(f'    {base_type} *{var_name}{array_size};')
                                    else:
                                        Code.append(f'    {base_type} {var_name}{array_size};')
                                else:
                                    Code.append(f'    {type_name} {var_name};')
                        else:
                            Code.append(f'    int {var_name};')
                    except Exception as e:
                        print(f'Warning: Failed to get type annotation for {var_name}: {e}')
                        Code.append(f'    int {var_name};')
            elif isinstance(item, ast.FunctionDef):
                if item.name == '__init__':
                    for stmt in item.body:
                        if isinstance(stmt, ast.AnnAssign):
                            if isinstance(stmt.target, ast.Attribute) and isinstance(stmt.target.value, ast.Name) and stmt.target.value.id == 'self':
                                var_name = stmt.target.attr
                                try:
                                    type_name = self.GetTypeName(stmt.annotation)
                                    if type_name and type_name.strip():
                                        if type_name == 'struct *':
                                            type_name = 'void *'
                                        Code.append(f'    {type_name} {var_name};')
                                    else:
                                        Code.append(f'    int {var_name};')
                                except Exception as e:
                                    print(f'Warning: Failed to get type annotation for {var_name}: {e}')
                                    Code.append(f'    int {var_name};')
        Code.append('};')
        
        if is_typedef:
            typedef_target = typedef_name if typedef_name else Node.name
            if typedef_name:
                Code.append(f'typedef struct {Node.name} {typedef_target};')
            else:
                Code.append(f'typedef struct {Node.name} {Node.name};')
        
        return Code

    @debug_handle
    def HandleMethodDef(self, class_name, Node):
        Code = []
        ReturnType = 'void'
        
        if Node.returns:
            try:
                ReturnType = self.GetTypeName(Node.returns)
                if not ReturnType:
                    ReturnType = 'void'
            except Exception as e:
                print(f'Warning: Failed to get return type for {Node.name}: {e}')
                ReturnType = 'void'
        
        func_name = f'{class_name}__{Node.name}'
        
        Params = []
        Params.append(f'struct {class_name}* self')
        
        for Arg in Node.args.args:
            if Arg.arg != 'self':
                try:
                    ParamType = self.GetTypeName(Arg.annotation)
                    if not ParamType:
                        ParamType = 'int'
                    Params.append(f'{ParamType} {Arg.arg}')
                except Exception as e:
                    print(f'Warning: Failed to get parameter type for {Arg.arg}: {e}')
                    Params.append(f'int {Arg.arg}')
        
        ParamsStr = ', '.join(Params)
        
        if self.Trans.IsHeader:
            Code.append(f'{ReturnType} {func_name}({ParamsStr});')
        else:
            Code.append(f'{ReturnType} {func_name}({ParamsStr}) {{')
            
            self.Trans.VarScopes.append({})
            
            for Arg in Node.args.args:
                if Arg.arg != 'self':
                    try:
                        ParamType = self.GetTypeName(Arg.annotation)
                        if not ParamType:
                            ParamType = 'int'
                        self.Trans.VarScopes[-1][Arg.arg] = ParamType
                    except Exception as e:
                        print(f'Warning: Failed to get parameter type for {Arg.arg}: {e}')
                        self.Trans.VarScopes[-1][Arg.arg] = 'int'
            
            body_code = self.HandleBody(Node.body)
            Code.extend(['    ' + line for line in body_code])
            
            Code.append('}')
            
            if self.Trans.VarScopes:
                self.Trans.VarScopes.pop()
        
        return Code
