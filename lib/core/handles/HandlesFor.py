import ast
from lib.core.Handles.HandlesBase import BaseHandle, debug_handle


class ForHandle(BaseHandle):
    def __init__(self, translator):
        super().__init__(translator)

    @debug_handle
    def HandleFor(self, Node):
        Code = []

        is_string_slice = False
        var_name = None
        base_var = None
        start_index = 0

        if isinstance(Node.target, ast.Name):
            var_name = Node.target.id
            if isinstance(Node.iter, ast.Subscript):
                if isinstance(Node.iter.value, ast.Name) and isinstance(Node.iter.slice, ast.Slice):
                    base_var = Node.iter.value.id
                    if Node.iter.slice.lower:
                        start_index = self.HandleExpr(Node.iter.slice.lower)[0]
                    else:
                        start_index = '0'
                    is_string_slice = True

        if is_string_slice and var_name and base_var:
            Code.append(f'for (int __for_i = {start_index}; {base_var}[__for_i] != \'\\0\'; __for_i++) {{')
            Code.append(f'    char {var_name} = {base_var}[__for_i];')
            Code.extend(['    ' + line for line in self.HandleBody(Node.body, in_block=True)])
            Code.append('}')
            return Code

        is_string_iter = False
        if isinstance(Node.target, ast.Name) and isinstance(Node.iter, ast.Name):
            var_name = Node.target.id
            base_var = Node.iter.id
            is_string_iter = True

        if is_string_iter and var_name and base_var:
            Code.append(f'for (int __for_i = 0; {base_var}[__for_i] != 0; __for_i++) {{')
            Code.append(f'    char {var_name} = {base_var}[__for_i];')
            Code.extend(['    ' + line for line in self.HandleBody(Node.body, in_block=True)])
            Code.append('}')
            return Code

        if isinstance(Node.iter, ast.Call) and isinstance(Node.iter.func, ast.Name) and Node.iter.func.id == 'range':
            start = 0
            stop = 0
            step = 1

            if len(Node.iter.args) >= 1:
                stop = self.HandleExpr(Node.iter.args[0])[0]
            if len(Node.iter.args) >= 2:
                start = self.HandleExpr(Node.iter.args[0])[0]
                stop = self.HandleExpr(Node.iter.args[1])[0]
            if len(Node.iter.args) >= 3:
                step = self.HandleExpr(Node.iter.args[2])[0]

            if isinstance(Node.target, ast.Name):
                var_name = Node.target.id
                if str(step) == '-1':
                    condition_op = '>'
                else:
                    condition_op = '<'

                if str(start) == var_name:
                    Code.append(f'for (; {var_name} {condition_op} {stop}; {var_name} += {step}) {{')
                elif self.Trans.VarScopes and var_name in self.Trans.VarScopes[-1]:
                    Code.append(f'for ({var_name} = {start}; {var_name} {condition_op} {stop}; {var_name} += {step}) {{')
                else:
                    Code.append(f'for (int {var_name} = {start}; {var_name} {condition_op} {stop}; {var_name} += {step}) {{')
                Code.extend(['    ' + line for line in self.HandleBody(Node.body, in_block=True)])
                Code.append('}')
                return Code

        Code.append('for (...) {')
        Code.extend(['    ' + line for line in self.HandleBody(Node.body, in_block=True)])
        Code.append('}')
        return Code


class WhileHandle(BaseHandle):
    def __init__(self, translator):
        super().__init__(translator)

    @debug_handle
    def HandleWhile(self, Node):
        Code = []

        is_do_while = False
        condition = None

        if isinstance(Node.test, ast.Constant) and Node.test.value is True:
            if Node.body:
                last_stmt = Node.body[-1]
                if isinstance(last_stmt, ast.If):
                    if not last_stmt.orelse:
                        if len(last_stmt.body) == 1 and isinstance(last_stmt.body[0], ast.Break):
                            condition = last_stmt.test
                            is_do_while = True

        if is_do_while and condition:
            Code.append('do {')
            body_code = []
            for stmt in Node.body[:-1]:
                body_code.extend(self.HandleBody([stmt], in_block=True))
            if body_code:
                Code.extend(['    ' + line for line in body_code])
            condition_code = self.HandleExpr(condition)[0]
            Code.append('} while (!(' + condition_code + '));')
        else:
            Test = self.HandleExpr(Node.test)[0]
            Code.append('while (' + Test + ') {')
            body_code = self.HandleBody(Node.body, in_block=True)
            Code.extend(['    ' + line for line in body_code])
            Code.append('}')

        return Code
