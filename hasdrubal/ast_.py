# pylint: disable=R0903
from abc import ABC, abstractmethod
from enum import auto, Enum
from typing import Callable, final, Iterable, Optional, Reversible, Sequence, Tuple

from errors import UnexpectedTokenError
from lex import Token, TokenTypes

merge: Callable[[Tuple[int, int], Tuple[int, int]], Tuple[int, int]]
merge = lambda left_span, right_span: (
    min(left_span[0], right_span[0]),
    max(left_span[1], right_span[1]),
)


class ScalarTypes(Enum):
    BOOL = auto()
    FLOAT = auto()
    INTEGER = auto()
    STRING = auto()


class VectorTypes(Enum):
    """The different types of vectors that are allowed."""

    LIST = auto()
    TUPLE = auto()


class ASTNode(ABC):
    """
    The base of all the nodes used in the AST.

    Attributes
    ----------
    span: Tuple[int, int]
        The position in the source text that this AST node came from.
    type_: Optional[Type]
        The type of the value that this AST node will eventually
        evaluate to (default: `None`).
    """

    def __init__(self, span: Tuple[int, int]) -> None:
        self.span: Tuple[int, int] = span
        self.type_: Optional["Type"] = None

    @abstractmethod
    def visit(self, visitor):
        """Run `visitor` on this node by selecting the correct node."""


class Block(ASTNode):
    __slots__ = ("body", "span", "type_")

    def __init__(self, span: Tuple[int, int], body: Iterable[ASTNode]) -> None:
        super().__init__(span)
        self.body: Iterable[ASTNode] = body

    def visit(self, visitor):
        return visitor.visit_block(self)


class Cond(ASTNode):
    __slots__ = ("cons", "else_", "pred", "span", "type_")

    def __init__(
        self, span: Tuple[int, int], pred: ASTNode, cons: ASTNode, else_: ASTNode
    ) -> None:
        super().__init__(span)
        self.pred: ASTNode = pred
        self.cons: ASTNode = cons
        self.else_: ASTNode = else_

    def visit(self, visitor):
        return visitor.visit_cond(self)


class Define(ASTNode):
    __slots__ = ("body", "span", "target", "type_", "value")

    def __init__(
        self,
        span: Tuple[int, int],
        target: "Name",
        value: ASTNode,
        body: Optional[ASTNode] = None,
    ) -> None:
        super().__init__(span)
        self.target: Name = target
        self.value: ASTNode = value
        self.body: Optional[ASTNode] = body

    def visit(self, visitor):
        return visitor.visit_define(self)


class FuncCall(ASTNode):
    __slots__ = ("callee", "callee", "span", "type_")

    def __init__(self, caller: ASTNode, callee: ASTNode) -> None:
        super().__init__(merge(caller.span, callee.span))
        self.caller: ASTNode = caller
        self.callee: ASTNode = callee

    def visit(self, visitor):
        return visitor.visit_func_call(self)


class Function(ASTNode):
    __slots__ = ("body", "param", "span", "type_")

    def __init__(self, span: Tuple[int, int], param: "Name", body: ASTNode) -> None:
        super().__init__(span)
        self.param: Name = param
        self.body: ASTNode = body

    @classmethod
    def curry(cls, span: Tuple[int, int], params: Reversible["Name"], body: ASTNode):
        """
        Make a function which takes any number of arguments at once
        into a series of nested ones that takes one arg at a time.

        Warnings
        --------
        - This function assumes that the params list has been checked
          to ensure it isn't empty.
        """
        for param in reversed(params):
            body = cls(span, param, body)
        return body

    def visit(self, visitor):
        return visitor.visit_function(self)


class Name(ASTNode):
    __slots__ = ("span", "type_", "value")

    def __init__(self, span: Tuple[int, int], value: str) -> None:
        super().__init__(span)
        self.value: str = value

    @classmethod
    def from_token(cls, token: Token):
        """Create an instance of this node using a lexer token."""
        if token.value is None:
            raise UnexpectedTokenError(token, TokenTypes.name)
        return cls(token.span, token.value)

    def visit(self, visitor):
        return visitor.visit_name(self)

    def __eq__(self, other):
        return isinstance(other, Name) and self.value == other.value


class Scalar(ASTNode):
    __slots__ = ("span", "type_", "value")

    def __init__(
        self,
        span: Tuple[int, int],
        scalar_type: ScalarTypes,
        value_string: str,
    ) -> None:
        super().__init__(span)
        self.scalar_type: ScalarTypes = scalar_type
        self.value_string: str = value_string

    @classmethod
    def from_token(cls, token: Token):
        """Create an instance of this node using a lexer token."""
        type_ = {
            TokenTypes.false: ScalarTypes.BOOL,
            TokenTypes.float_: ScalarTypes.FLOAT,
            TokenTypes.integer: ScalarTypes.INTEGER,
            TokenTypes.string: ScalarTypes.STRING,
            TokenTypes.true: ScalarTypes.BOOL,
        }.get(token.type_)
        if type_ is None or token.value is None:
            raise UnexpectedTokenError(
                token,
                TokenTypes.false,
                TokenTypes.float_,
                TokenTypes.integer,
                TokenTypes.string,
                TokenTypes.true,
            )
        return cls(token.span, type_, token.value)

    def visit(self, visitor):
        return visitor.visit_scalar(self)


class Type(ASTNode, ABC):
    """
    This is the base class for the program's representation of types in
    the type system.

    Warnings
    --------
    - This class should not be used directly, instead use one of its
      subclasses.
    """

    @abstractmethod
    def is_concrete(self) -> bool:
        """
        Check whether the type is concrete or is made up of concrete
        types.

        Returns
        -------
        bool
            If `True`, the type is concrete or made up of concrete
            types.
        """

    @final
    def visit(self, visitor):
        return visitor.visit_type(self)


class FuncType(Type):
    """
    This is the type of a function for the type system.

    Attributes
    ----------
    left: Type
        The type of the single argument to the function.
    right: Type
        The type of what the function's return.
    """

    __slots__ = ("left", "span", "right", "type_")

    def __init__(self, span: Tuple[int, int], left: Type, right: Type) -> None:
        super().__init__(span)
        self.left: Type = left
        self.right: Type = right

    def is_concrete(self) -> bool:
        return self.left.is_concrete() and self.right.is_concrete()

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, FuncType)
            and self.left == other.left
            and self.right == other.right
        )


class GenericType(Type):

    __slots__ = ("args", "base", "span", "type_")

    def __init__(
        self, span: Tuple[int, int], base: Name, args: Sequence[Type] = ()
    ) -> None:
        super().__init__(span)
        self.base: Name = base
        self.args: Sequence[Type] = args

    def is_concrete(self) -> bool:
        return all(map(lambda arg: arg.is_concrete(), self.args))

    def __eq__(self, other):
        return (
            isinstance(other, GenericType)
            and self.base == other.base
            and tuple(self.args) == tuple(other.args)
        )


class TypeVar(Type):

    __slots__ = ("span", "type_", "value")
    n_type_vars = 0

    def __init__(self, span: Tuple[int, int], value: str) -> None:
        super().__init__(span)
        self.value: str = value

    @classmethod
    def unknown(cls, span: Tuple[int, int]):
        """
        Make a type var instance without explicitly providing a name
        for it.

        Attribute
        ---------
        span: Tuple[int, int]
            The position of this instance in the source code.
        """
        cls.n_type_vars += 1
        return cls(span, str(cls.n_type_vars))

    @classmethod
    def from_token(cls, token: Token):
        """Create an instance of this node using a lexer token."""
        if token.value is None:
            raise UnexpectedTokenError(token, TokenTypes.name)
        return cls(token.span, token.value)

    def is_concrete(self) -> bool:
        return False

    def __eq__(self, other) -> bool:
        return isinstance(other, TypeVar) and self.value == other.value


class Vector(ASTNode):
    __slots__ = ("elements", "span", "type_", "vec_type")

    def __init__(
        self, span: Tuple[int, int], vec_type: VectorTypes, elements: Iterable[ASTNode]
    ) -> None:
        super().__init__(span)
        self.vec_type: VectorTypes = vec_type
        self.elements: Iterable[ASTNode] = elements

    @classmethod
    def unit(cls, span: Tuple[int, int]):
        return cls(span, VectorTypes.TUPLE, ())

    def visit(self, visitor):
        return visitor.visit_vector(self)