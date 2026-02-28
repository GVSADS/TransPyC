import ast
import re
from lib.core.Handles.HandlesBase import BaseHandle, debug_handle
from lib.constants.config import TYPE_MAP

T_MODULE_TYPES = [
    'CChar', 'CUnsignedChar', 'CInt', 'CUnsignedInt',
    'CShort', 'CUnsignedShort', 'CLong', 'CUnsignedLong',
    'CFloat', 'CDouble', 'CVoid', 'CPtr'
]

T_ALL_TYPES = [
    'CInt', 'CChar', 'CShort', 'CLong', 'CFloat', 'CDouble', 'CVoid',
    'CUnsigned', 'CUnsignedChar', 'CUnsignedInt', 'CUnsignedShort', 'CUnsignedLong',
    'CSignedChar', 'CSizeT', 'CInt8T', 'CInt16T', 'CInt32T', 'CInt64T',
    'CUInt8T', 'CUInt16T', 'CUInt32T', 'CUInt64T',
    'CIntPtrT', 'CUIntPtrT', 'CPtrDiffT', 'CWCharT',
    'CChar16T', 'CChar32T', 'CBool', 'CComplex', 'CImaginary', 'CPtr'
]


class TSpecialCallHandle(BaseHandle):
    def __init__(self, translator):
        super().__init__(translator)

    @debug_handle
    def HandleTSpecialCall(self, attr, args, keywords):
        if attr == 'CType':
            if len(args) >= 1:
                value = self.HandleExpr(args[0])[0]
                type_str = ''
                for i in range(1, len(args)):
                    type_arg = args[i]
                    type_name = self.GetTypeName(type_arg)
                    if type_name:
                        type_str += f'{type_name} '
                type_str = type_str.strip()
                if type_str.startswith('struct '):
                    type_name = type_str[7:]
                    if any(basic_type in type_name for basic_type in T_MODULE_TYPES):
                        for basic_type in T_MODULE_TYPES:
                            if basic_type in type_name:
                                if basic_type in TYPE_MAP:
                                    type_str = TYPE_MAP[basic_type]
                                    if 'CPtr' in type_name:
                                        type_str += '*'
                                break
                if type_str:
                    return [f'(({type_str}){value})']
                else:
                    return [value]
            return ['0']
        elif attr == 'CStruct':
            if len(args) >= 1:
                addr = self.HandleExpr(args[0])[0]
                struct_name = 'BOOTINFO'
                if len(args) >= 2 and isinstance(args[1], ast.Name):
                    struct_name = args[1].id
                return [f'((struct {struct_name} *){addr})']
            return ['0']
        elif attr in T_ALL_TYPES:
            if len(args) >= 1:
                value = self.HandleExpr(args[0])[0]
                type_parts = []
                if attr in TYPE_MAP:
                    type_parts.append(TYPE_MAP[attr])
                for i in range(1, len(args)):
                    type_arg = args[i]
                    type_name = self.GetTypeName(type_arg)
                    if type_name:
                        type_parts.append(type_name)
                type_str = ' '.join(type_parts)
                if '*' in type_str:
                    type_str = re.sub(r'(?<!\s)\*', ' *', type_str)
                    type_str = type_str.strip()
                return [f'(({type_str}){value})']
        args_str = ', '.join([self.HandleExpr(arg)[0] for arg in args])
        return [f't.{attr}({args_str});']


class CSpecialCallHandle(BaseHandle):
    def __init__(self, translator):
        super().__init__(translator)

    @debug_handle
    def HandleCSpecialCall(self, attr, args, keywords):
        from lib.includes.c import Library_C

        if attr in Library_C:
            handler_class = Library_C[attr]
            return handler_class.HandleCall(self.Trans, args, keywords)

        if attr == 'sizeof':
            if len(args) >= 1:
                type_arg = args[0]
                type_name = self.GetTypeName(type_arg)
                if type_name:
                    return [f'sizeof({type_name})']
            return ['0']
        elif attr == 'offsetof':
            if len(args) >= 2:
                struct_type = self.GetTypeName(args[0])
                member = args[1]
                if isinstance(member, ast.Attribute):
                    member_name = member.attr
                    return [f'offsetof({struct_type}, {member_name})']
            return ['0']
        elif attr == 'asm' or attr == '__asm__':
            if args:
                asm_str = self.HandleExpr(args[0])[0]
                return [f'__asm__({asm_str})']
            return ['']
        elif attr == 'cast':
            if len(args) >= 2:
                type_name = self.GetTypeName(args[0])
                value = self.HandleExpr(args[1])[0]
                return [f'(({type_name}){value})']
            return ['0']
        elif attr == 'pointer':
            if len(args) >= 1:
                value = self.HandleExpr(args[0])[0]
                return [f'((void *){value})']
            return ['0']
        elif attr == 'address':
            if len(args) >= 1:
                value = self.HandleExpr(args[0])[0]
                return [f'(&{value})']
            return ['0']
        elif attr == 'dereference':
            if len(args) >= 1:
                value = self.HandleExpr(args[0])[0]
                return [f'*{value}']
            return ['0']
        elif attr == 'State':
            return ['c.State']
        elif attr == 'Define':
            if len(args) >= 1:
                name = self.HandleExpr(args[0])[0]
                if len(args) >= 2:
                    value = self.HandleExpr(args[1])[0]
                    return [f'#define {name} {value}']
            return ['0']
        else:
            args_str = ', '.join([self.HandleExpr(arg)[0] for arg in args])
            return [f'c.{attr}({args_str});']
