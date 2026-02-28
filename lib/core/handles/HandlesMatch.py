from lib.core.Handles.HandlesBase import BaseHandle, debug_handle


class MatchHandle(BaseHandle):
    def __init__(self, translator):
        super().__init__(translator)

    @debug_handle
    def HandleMatch(self, Node):
        Code = []
        subject = self.HandleExpr(Node.subject)[0]
        Code.append(f'switch ({subject}) {{')

        has_default = False

        for case in Node.cases:
            pattern = case.pattern
            case_generated = False

            if isinstance(pattern, ast.MatchValue):
                value = self.HandleExpr(pattern.value)[0]
                Code.append(f'    case {value}:')
                case_generated = True
            elif isinstance(pattern, ast.MatchOr):
                for sub_pattern in pattern.patterns:
                    if isinstance(sub_pattern, ast.MatchValue):
                        value = self.HandleExpr(sub_pattern.value)[0]
                        Code.append(f'    case {value}:')
                case_generated = True
            elif isinstance(pattern, ast.MatchSingleton):
                if pattern.value is None:
                    Code.append('    case 0:')
                case_generated = True
            elif isinstance(pattern, ast.MatchAs):
                if pattern.pattern is None:
                    if pattern.name and pattern.name != '_':
                        value = pattern.name
                        Code.append(f'    case {value}:')
                        case_generated = True
                    else:
                        has_default = True
                        Code.append('    default:')
                        case_generated = True

            if case_generated and case.body:
                Code.append('        {')
                body_code = self.HandleBody(case.body, in_block=True)
                for line in body_code:
                    Code.append('            ' + line)
                Code.append('            break;')
                Code.append('        }')

        if not has_default:
            Code.append('    default:')
            Code.append('        {')
            Code.append('            break;')
            Code.append('        }')

        Code.append('}')
        return Code
