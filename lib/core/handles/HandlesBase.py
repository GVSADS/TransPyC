import ast
import functools


T_MODULE_TYPES = [
    'CChar', 'CUnsignedChar', 'CInt', 'CUnsignedInt',
    'CShort', 'CUnsignedShort', 'CLong', 'CUnsignedLong',
    'CFloat', 'CDouble', 'CVoid', 'CPtr'
]


def debug_handle(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        func_name = func.__name__
        node_info = ""
        if args and hasattr(args[0], '__class__'):
            node = args[0]
            node_type = type(node).__name__
            node_info = f"[{node_type}]"
        
        result = func(self, *args, **kwargs)
        return result
    return wrapper


class BaseHandle:
    def __init__(self, translator):
        self.Trans = translator
    
    def DebugPrint(self, msg):
        if hasattr(self.Trans, 'DebugPrint'):
            self.Trans.DebugPrint(msg)
    
    def HandleExpr(self, Node, use_single_quote=False):
        return self.Trans.HandleExpr(Node, use_single_quote)
    
    def HandleBody(self, Body, in_block=False):
        return self.Trans.HandleBody(Body, in_block)
    
    def GetTypeName(self, Node):
        return self.Trans.GetTypeName(Node)
