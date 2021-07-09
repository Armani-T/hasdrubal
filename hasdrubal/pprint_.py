from ast_ import FuncType, GenericType, TypeVar
from visitor import NodeVisitor
import ast_ as ast


# pylint: disable=R0904
class PPrinter(NodeVisitor[str]):
    """
    This visitor just produces a string that shows the entire AST.
    The code produced looks like clojure code though it may not be
    valid.
    """

    def __init__(self) -> None:
        self.indent_level: int = 0

    def visit_block(self, node: ast.Block) -> str:
        body = (node.first,  *node.rest)
        self.indent_level += 1
        preface = f"\n{'  ' * self.indent_level}"
        result = preface + preface.join((expr.visit(self) for expr in body))
        self.indent_level -= 1
        return result

    def visit_cond(self, node: ast.Cond) -> str:
        pred = node.pred.visit(self)
        cons = node.cons.visit(self)
        else_ = node.else_.visit(self)
        return f"if {pred} then {cons} else {else_}"

    def visit_define(self, node: ast.Define) -> str:
        target = node.target.visit(self)
        value = node.value.visit(self)
        body = "" if node.body is None else f" in {node.body.visit(self)}"
        return f"let {target} = {value}{body}"

    def visit_func_call(self, node: ast.FuncCall) -> str:
        return f"{node.caller.visit(self)}( {node.callee.visit(self)} )"

    def visit_function(self, node: ast.Function) -> str:
        return f"\\{node.param.visit(self)} -> {node.body.visit(self)}"

    def visit_name(self, node: ast.Name) -> str:
        return node.value

    def visit_scalar(self, node: ast.Scalar) -> str:
        return node.value_string

    def visit_type(self, node: ast.Type) -> str:
        if isinstance(node, TypeVar):
            return f"@{node.value}"
        if isinstance(node, FuncType):
            return f"{node.left.visit(self)} -> {node.right.visit(self)}"
        if isinstance(node, GenericType):
            result = node.base.visit(self)
            return (
                f"({result}[{' '.join(map(lambda n: n.visit(self), node.args))}]"
                if node.args
                else result
            )
        raise TypeError(
            f"{node} is an invalid subtype of nodes.Type, it is {type(node)}"
        )

    def visit_vector(self, node: ast.Vector) -> str:
        bracket = {
            ast.VectorTypes.LIST: lambda string: f"[{string}]",
            ast.VectorTypes.TUPLE: lambda string: f"({string})",
        }[node.vec_type]
        return bracket(", ".join((elem.visit(self) for elem in node.elements)))