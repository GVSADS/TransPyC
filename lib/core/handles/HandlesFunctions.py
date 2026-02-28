import ast
from lib.core.Handles.HandlesBase import BaseHandle, debug_handle


class FunctionHandle(BaseHandle):
    def __init__(self, translator):
        super().__init__(translator)

    @debug_handle
    def HandleFunctionDef(self, Node):
        Code = []
        ReturnType = 'void'
        is_function_declaration = False
        attributes = []
        
        if Node.decorator_list:
            for decorator in Node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr == 'Attribute':
                            for arg in decorator.args:
                                if isinstance(arg, ast.Call):
                                    attr_value = self.HandleExpr(arg)[0]
                                    if attr_value:
                                        attributes.append(attr_value)
                                elif isinstance(arg, ast.Constant):
                                    attributes.append(arg.value)
        
        if Node.returns:
            try:
                return_type = self.GetTypeName(Node.returns)
                if return_type == '#define':
                    func_name = Node.name
                    params = []
                    for arg in Node.args.args:
                        params.append(arg.arg)
                    params_str = ', '.join(params)
                    if len(Node.body) == 1 and isinstance(Node.body[0], ast.Return):
                        return_expr = Node.body[0].value
                        expr_code = self.HandleExpr(return_expr)[0]
                        Code.append(f'#define {func_name}({params_str}) ({expr_code})')
                        return Code
            except Exception as e:
                print(f'Warning: Failed to check for macro definition: {e}')
        
        if Node.returns:
            try:
                if isinstance(Node.returns, ast.BinOp) and isinstance(Node.returns.op, ast.BitOr):
                    left_type = self.GetTypeName(Node.returns.left)
                    right_type = self.GetTypeName(Node.returns.right)
                    if 'c.State' in left_type:
                        is_function_declaration = True
                        if right_type == '*':
                            if isinstance(Node.returns.left, ast.BinOp):
                                struct_type = self.GetTypeName(Node.returns.left.right)
                                if struct_type and struct_type.startswith('struct '):
                                    ReturnType = f'{struct_type}*'
                                else:
                                    ReturnType = 'void'
                            elif isinstance(Node.returns.right, ast.BinOp):
                                combined_type = self.GetTypeName(Node.returns.right)
                                if combined_type and combined_type != '*':
                                    ReturnType = combined_type
                                else:
                                    ReturnType = 'void'
                            else:
                                ReturnType = right_type if right_type else 'void'
                        else:
                            ReturnType = right_type if right_type else 'void'
                    elif 'c.State' in right_type:
                        is_function_declaration = True
                        ReturnType = left_type if left_type else 'void'
                    else:
                        if left_type == 'long' and right_type == 'int':
                            ReturnType = 'long int'
                        else:
                            ReturnType = self.GetTypeName(Node.returns)
                else:
                    ReturnType = self.GetTypeName(Node.returns)
                    if ReturnType == 'c.State':
                        is_function_declaration = True
                        ReturnType = 'void'
                
                if not ReturnType:
                    ReturnType = 'void'
            except Exception as e:
                print(f'Warning: Failed to get return type: {e}')
                ReturnType = 'void'
        
        if Node.name == 'main' and ReturnType == 'void':
            ReturnType = 'int'
        
        Params = []
        self.Trans.VarScopes.append({})
        self.Trans.DebugPrint(f"[SCOPE] Enter function '{Node.name}', new scope created, depth={len(self.Trans.VarScopes)}")
        
        for Arg in Node.args.args:
            if Arg.annotation:
                try:
                    ParamType = self.GetTypeName(Arg.annotation)
                    if not ParamType:
                        ParamType = 'int'
                    if ParamType.count(' ') > 1:
                        types = ParamType.split()
                        unique_types = []
                        for t in types:
                            if t not in unique_types:
                                unique_types.append(t)
                        ParamType = ' '.join(unique_types)
                    Params.append(f'{ParamType} {Arg.arg}')
                    self.Trans.VarScopes[-1][Arg.arg] = ParamType
                except Exception as e:
                    print(f'Warning: Failed to get parameter type: {e}')
                    Params.append(f'int {Arg.arg}')
                    self.Trans.VarScopes[-1][Arg.arg] = 'int'
            else:
                Params.append(f'int {Arg.arg}')
                self.Trans.VarScopes[-1][Arg.arg] = 'int'
        
        if not Params:
            ParamsStr = 'void'
        else:
            ParamsStr = ', '.join(Params)
        
        attr_str = ''
        if attributes:
            attr_str = f' __attribute__(({", ".join(attributes)}))'
        
        if is_function_declaration or self.Trans.IsHeader:
            Code.append(f'{ReturnType}{attr_str} {Node.name}({ParamsStr});')
        else:
            Code.append(f'{ReturnType}{attr_str} {Node.name}({ParamsStr}) {{')
            body_code = self.HandleBody(Node.body)
            Code.extend(['    ' + line for line in body_code])
            Code.append('}')
        
        if self.Trans.VarScopes:
            self.Trans.VarScopes.pop()
        self.Trans.DebugPrint(f"[SCOPE] Exit function '{Node.name}', scope popped, depth={len(self.Trans.VarScopes)}")
        
        self.Trans.FunctionReturnTypes[Node.name] = ReturnType
        
        return Code

    def HandleMethodDef(self, class_name, Node):
        return self.Trans.HandleMethodDef(class_name, Node)
