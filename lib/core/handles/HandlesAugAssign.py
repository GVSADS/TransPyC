from lib.core.Handles.HandlesBase import BaseHandle, debug_handle


class AugAssignHandle(BaseHandle):
    def __init__(self, translator):
        super().__init__(translator)

    @debug_handle
    def HandleAugAssign(self, Node):
        Code = []
        if isinstance(Node.target, ast.Name):
            var_name = Node.target.id
            value = self.HandleExpr(Node.value)[0]
            op = self.Trans.GetAugOpSymbol(Node.op)
            if op:
                Code.append(f'{var_name} {op}= {value};')
        elif isinstance(Node.target, ast.Subscript):
            arr = self.HandleExpr(Node.target.value)[0]
            index = self.HandleExpr(Node.target.slice)[0]
            value = self.HandleExpr(Node.value)[0]
            op = self.Trans.GetAugOpSymbol(Node.op)
            if op:
                Code.append(f'{arr}[{index}] {op}= {value};')
        elif isinstance(Node.target, ast.Attribute):
            if isinstance(Node.target.value, ast.Name) and Node.target.value.id == 'self':
                attr_name = Node.target.attr
                value = self.HandleExpr(Node.value)[0]
                op = self.Trans.GetAugOpSymbol(Node.op)
                if op:
                    Code.append(f'self->{attr_name} {op}= {value};')
            else:
                obj = self.HandleExpr(Node.target.value)[0]
                attr = Node.target.attr
                value = self.HandleExpr(Node.value)[0]
                op = self.Trans.GetAugOpSymbol(Node.op)

                is_ptr = False
                if isinstance(Node.target.value, ast.Name):
                    var_name = Node.target.value.id
                    for scope in reversed(self.Trans.VarScopes):
                        if var_name in scope:
                            var_type = scope[var_name]
                            if '*' in var_type:
                                is_ptr = True
                            break

                if op:
                    if is_ptr:
                        Code.append(f'{obj}->{attr} {op}= {value};')
                    else:
                        Code.append(f'{obj}.{attr} {op}= {value};')
        return Code
