import ast
from lib.core.Handles.HandlesBase import BaseHandle, debug_handle


class IfHandle(BaseHandle):
    def __init__(self, translator):
        super().__init__(translator)

    @debug_handle
    def HandleIf(self, Node):
        Code = []
        Test = self.HandleExpr(Node.test)[0]
        Code.append('if (' + Test + ') {')
        body_code = self.HandleBody(Node.body, in_block=True)
        Code.extend(['    ' + line for line in body_code])
        Code.append('}')
        if Node.orelse:
            current_else = Node.orelse
            while len(current_else) == 1 and isinstance(current_else[0], ast.If):
                elif_node = current_else[0]
                elif_test = self.HandleExpr(elif_node.test)[0]
                Code.append('else if (' + elif_test + ') {')
                elif_body_code = self.HandleBody(elif_node.body, in_block=True)
                Code.extend(['    ' + line for line in elif_body_code])
                Code.append('}')
                current_else = elif_node.orelse

            if current_else:
                Code.append('else {')
                else_code = self.HandleBody(current_else, in_block=True)
                Code.extend(['    ' + line for line in else_code])
                Code.append('}')
        return Code
