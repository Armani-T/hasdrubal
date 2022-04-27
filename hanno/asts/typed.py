# pylint: disable=R0903, C0115, W0231
from abc import ABC
from typing import cast, Iterable, Optional, Sequence

from . import base
from .types_ import Type, TypeApply, TypeName


class TypedASTNode(base.ASTNode, ABC):
    """
    The base of all the nodes used in the AST but now with type
    annotations for all of them.

    Attributes
    ----------
    type_: Optional[Type]
        The type of the value that this AST node will evaluate to.
    """

    def __init__(self, span: base.Span, type_: Type) -> None:
        super().__init__(span)
        self.type_: Type = type_


class Apply(base.Apply, TypedASTNode):
    __slots__ = ("arg", "func", "span", "type_")

    def __init__(
        self, span: base.Span, type_: Type, func: TypedASTNode, arg: TypedASTNode
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.func: TypedASTNode = func
        self.arg: TypedASTNode = arg


class Block(base.Block, TypedASTNode):
    __slots__ = ("body", "span", "type_")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        body: Sequence[TypedASTNode],
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.body: Sequence[TypedASTNode] = body


class Cond(base.Cond, TypedASTNode):
    __slots__ = ("cons", "else_", "pred", "span", "type_")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        pred: TypedASTNode,
        cons: TypedASTNode,
        else_: TypedASTNode,
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.pred: TypedASTNode = pred
        self.cons: TypedASTNode = cons
        self.else_: TypedASTNode = else_


class Define(base.Define, TypedASTNode):
    __slots__ = ("span", "target", "type_", "value")

    def __init__(
        self, span: base.Span, type_: Type, target: "Name", value: TypedASTNode
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.target: Name = target
        self.value: TypedASTNode = value


class Function(base.Function, TypedASTNode):
    __slots__ = ("body", "param", "span", "type_")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        param: "Name",
        body: TypedASTNode,
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.param: Name = param
        self.body: TypedASTNode = body

    @classmethod
    def curry(cls, span: base.Span, params: Iterable[base.Name], body: base.ASTNode):
        """
        Make a function which takes any number of arguments at once
        into a series of nested ones that takes one arg at a time.

        Warnings
        --------
        - This function takes the typed version of `params` and `body`.
          The type annotations say otherwise to maintain the Liskov
          substitution principle.
        """
        if not params:
            return body

        params = cast(Iterable["Name"], params)
        body = cast(TypedASTNode, body)
        first, *rest = params
        if rest:
            return cls(
                span,
                TypeApply.func(span, first.type_, body.type_),
                first,
                cls.curry(span, rest, body),
            )
        return cls(span, TypeApply.func(span, first.type_, body.type_), first, body)


class List(base.List, TypedASTNode):
    __slots__ = ("elements", "span", "type_")

    def __init__(
        self, span: base.Span, type_: Type, elements: Iterable[TypedASTNode]
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.elements: Iterable[TypedASTNode] = elements


class Pair(base.Pair, TypedASTNode):
    __slots__ = ("first", "second", "span", "type_")

    def __init__(
        self, span: base.Span, type_: Type, first: TypedASTNode, second: TypedASTNode
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.first: TypedASTNode = first
        self.second: TypedASTNode = second


class Name(base.Name, TypedASTNode):
    __slots__ = ("span", "type_", "value")

    def __init__(self, span: base.Span, type_: Type, value: Optional[str]) -> None:
        if value is None:
            raise TypeError("`None` was passed to `typed.Name.__init__`.")

        TypedASTNode.__init__(self, span, type_)
        self.value: str = value


class Scalar(base.Scalar, TypedASTNode):
    __slots__ = ("span", "type_", "value")

    def __init__(
        self,
        span: base.Span,
        type_: TypeName,
        value: base.ValidScalarTypes,
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.value: base.ValidScalarTypes = value


class Unit(base.Unit, TypedASTNode):
    __slots__ = ("span", "type_")

    def __init__(self, span: base.Span, type_: Type = None) -> None:
        TypedASTNode.__init__(self, span, type_ or TypeName.unit(span))