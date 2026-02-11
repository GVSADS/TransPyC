"""
Handle 函数基类
"""

import functools


def debug_handle(func):
    """装饰器：记录 Handle 方法的进入和退出"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        func_name = func.__name__
        node_info = ""
        if args and hasattr(args[0], '__class__'):
            node = args[0]
            node_type = type(node).__name__
            node_info = f"[{node_type}]"
            if hasattr(node, 'id'):
                node_info += f" id={node.id}"
            elif hasattr(node, 'attr'):
                node_info += f" attr={node.attr}"
            elif hasattr(node, 'name'):
                node_info += f" name={node.name}"
        
        self.debug_print(f"[ENTER] {func_name} {node_info}")
        try:
            result = func(self, *args, **kwargs)
            result_summary = ""
            if isinstance(result, list):
                result_summary = f" -> {len(result)} lines"
            elif isinstance(result, str):
                result_summary = f" -> '{result[:50]}...'" if len(result) > 50 else f" -> '{result}'"
            self.debug_print(f"[EXIT] {func_name} {node_info}{result_summary}")
            return result
        except Exception as e:
            self.debug_print(f"[ERROR] {func_name} {node_info}: {e}")
            raise
    return wrapper


class HandleMixin:
    """Handle 函数 Mixin 基类"""
    
    # 这些属性由 Translator 类提供
    VarScopes = None
    FunctionReturnTypes = None
    SymbolTable = None
    OriginalLines = None
    Content = None
    debug_file = None
    
    def debug_print(self, *args, **kwargs):
        """输出调试信息到文件"""
        if self.debug_file:
            with open(self.debug_file, 'a', encoding='utf-8') as f:
                print(*args, file=f, **kwargs)
    
    # 以下方法由子类实现或从 translator 导入
    def GetTypeName(self, Node):
        raise NotImplementedError
    
    def GetOpSymbol(self, op):
        raise NotImplementedError
    
    def GetUnaryOpSymbol(self, op):
        raise NotImplementedError
    
    def GetComparatorSymbol(self, op):
        raise NotImplementedError
    
    def GetAugOpSymbol(self, op):
        raise NotImplementedError
    
    def GetStringQuoteType(self, content, node):
        raise NotImplementedError
    
    def GetNumericLiteral(self, content, node):
        raise NotImplementedError
