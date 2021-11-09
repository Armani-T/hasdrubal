from asts import lowered, visitor


class ConstantFolder(visitor.LoweredASTVisitor[lowered.LoweredASTNode]):
    """
    Combine literal operations into a single AST node.
    """

    def visit_block(self, node: lowered.Block) -> lowered.Block:
        return lowered.Block(
            node.span,
            [expr.visit(self) for expr in node.body()],
        )

    def visit_cond(self, node: lowered.Cond) -> lowered.Cond:
        if isinstance(node.pred, lowered.Scalar):
            return node.cons.visit(self) if node.pred.value else node.else_.visit(self)
        return lowered.Cond(
            node.span,
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: lowered.Define) -> lowered.Define:
        return lowered.Define(
            node.span,
            node.target,
            node.value.visit(self),
        )

    def visit_function(self, node: lowered.Function) -> lowered.Function:
        return lowered.Function(
            node.span,
            node.params,
            node.body.visit(self),
        )

    def visit_func_call(self, node: lowered.FuncCall) -> lowered.FuncCall:
        return lowered.FuncCall(
            node.span,
            node.func.visit(self),
            [arg.visit(self) for arg in node.args],
        )

    def visit_name(self, node: lowered.Name) -> lowered.Name:
        return node

    def visit_native_operation(
        self, node: lowered.NativeOperation
    ) -> lowered.LoweredASTNode:
        if _can_simplify_negate(node):
            return lowered.Scalar(node.span, -node.left.value)
        if _can_simplify_math_op(node):
            return fold_math_op(node)
        if _can_simplify_compare_op(node):
            return fold_compare_op(node)
        return lowered.NativeOperation(
            node.span,
            node.operation,
            node.left,
            node.right,
        )

    def visit_scalar(self, node: lowered.Scalar) -> lowered.Scalar:
        return node

    def visit_vector(self, node: lowered.Vector) -> lowered.Vector:
        return lowered.Vector(
            node.span,
            node.vec_type,
            [elem.visit(self) for elem in node.elements],
        )