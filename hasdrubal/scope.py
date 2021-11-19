from typing import Dict, Generic, Iterator, Optional, Protocol, Tuple, TypeVar

from asts.base import Name
from asts.types_ import Type, TypeApply, TypeName, TypeScheme, TypeVar as TVar
from errors import FatalInternalError, UndefinedNameError

ValType = TypeVar("ValType")


# pylint: disable=C0116, R0903
class ScopeSubject(Protocol):
    value: str


# pylint: disable=R0903
class Scope(Generic[ValType]):
    """
    A mapping of all defined names to their values.

    Attributes
    ----------
    _data: Dict[str, ASTNode]
        A `dict` containing those names in string form and their values
        without the values being evaluated.
    parent: Optional[Scope]
        A scope that wraps around `self` and can be requested for
        names that were defined before `self` was made.
    """

    def __init__(self, parent: Optional["Scope"]) -> None:
        self._data: Dict[str, ValType] = {}
        self._parent: Optional[Scope[ValType]] = parent

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, ValType],
        parent: Optional["Scope[ValType]"] = None,
    ):
        """Create a new scope based on what is stored in a dict."""
        new_scope = cls(parent)
        new_scope._data = data
        return new_scope

    def depth(self, name: ScopeSubject) -> int:
        """
        Check how deep a name is in the hierarchy of scopes.

        Parameters
        ----------
        name: ScopeSubject
            The name being searched for.

        Raises
        ------
        UndefinedNameError
            The exception thrown when `name` is not in the scope and
            `raise_ = True`.

        Returns
        -------
        int
             How deep `name` is in the hierarchy. It will be `0` if
             `name` is in this object, `1` if it is in the direct
             parent, etc. But if `raise_ = False`, `-1` will be
             returned instead.
        """
        depth = 0
        current: Optional[Scope] = self
        while current is not None:
            if name.value in current._data:  # pylint: disable=W0212
                return depth
            current = current._parent  # pylint: disable=W0212
            depth += 1
        return -1

    def down(self) -> "Scope[ValType]":
        """Create a scope that will be a child of this one."""
        return Scope(self)

    def get(
        self, name: ScopeSubject, default: Optional[ValType] = None
    ) -> Optional[ValType]:
        if name.value in self._data:
            return self._data[name.value]
        if self._parent is not None:
            return self._parent[name]
        return default

    # pylint: disable=C0103
    def up(self) -> "Scope[ValType]":
        """Get the parent of this scope."""
        if self._parent is None:
            raise FatalInternalError()
        return self._parent

    def __bool__(self) -> bool:
        return bool(self._data) and self._parent is not None

    def __contains__(self, name: ScopeSubject) -> bool:
        return name.value in self._data or (
            self._parent is not None and name in self._parent
        )

    def __delitem__(self, name: ScopeSubject) -> None:
        if name in self:
            del self._data[name.value]
        elif self._parent is not None:
            del self._parent[name]

    def __iter__(self) -> Iterator[Tuple[str, ValType]]:
        for key, value in self._data.items():
            yield (key, value)

    def __getitem__(self, name: ScopeSubject) -> ValType:
        if name.value in self._data:
            return self._data[name.value]
        if self._parent is not None:
            return self._parent[name]
        raise UndefinedNameError(name)

    def __setitem__(self, name: ScopeSubject, value: ValType) -> None:
        if self._parent is not None and name in self._parent:
            self._parent[name] = value
        else:
            self._data[name.value] = value


DEFAULT_OPERATOR_TYPES: Scope[Type] = Scope(None)
DEFAULT_OPERATOR_TYPES[Name((0, 3), "and")] = TypeApply.func(
    (5, 25),
    TypeName((5, 9), "Bool"),
    TypeApply.func(
        (13, 25),
        TypeName((13, 17), "Bool"),
        TypeName((21, 25), "Bool"),
    ),
)
DEFAULT_OPERATOR_TYPES[Name((26, 28), "or")] = TypeApply.func(
    (30, 50),
    TypeName((30, 34), "Bool"),
    TypeApply.func(
        (38, 50),
        TypeName((38, 42), "Bool"),
        TypeName((46, 50), "Bool"),
    ),
)
DEFAULT_OPERATOR_TYPES[Name((51, 54), "not")] = TypeApply.func(
    (56, 68),
    TypeName((56, 60), "Bool"),
    TypeName((64, 68), "Bool"),
)
DEFAULT_OPERATOR_TYPES[Name((69, 70), "=")] = TypeScheme(
    TypeApply.func(
        (72, 86),
        TVar((72, 73), "x"),
        TypeApply.func(
            (77, 86),
            TVar((77, 78), "x"),
            TypeName((82, 86), "Bool"),
        ),
    ),
    {TVar((72, 73), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((87, 89), "/=")] = TypeScheme(
    TypeApply.func(
        (91, 105),
        TVar((91, 92), "x"),
        TypeApply.func(
            (96, 105),
            TVar((96, 97), "x"),
            TypeName((101, 105), "Bool"),
        ),
    ),
    {TVar((91, 92), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((106, 107), ">")] = TypeScheme(
    TypeApply.func(
        (109, 123),
        TVar((109, 110), "x"),
        TypeApply.func(
            (114, 123),
            TVar((114, 115), "x"),
            TypeName((119, 123), "Bool"),
        ),
    ),
    {TVar((109, 110), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((124, 125), "<")] = TypeScheme(
    TypeApply.func(
        (127, 141),
        TVar((127, 128), "x"),
        TypeApply.func(
            (132, 141),
            TVar((132, 133), "x"),
            TypeName((137, 141), "Bool"),
        ),
    ),
    {TVar((127, 128), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((142, 144), ">=")] = TypeScheme(
    TypeApply.func(
        (146, 160),
        TVar((146, 147), "x"),
        TypeApply.func(
            (151, 160),
            TVar((151, 152), "x"),
            TypeName((156, 160), "Bool"),
        ),
    ),
    {TVar((146, 147), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((161, 163), "<=")] = TypeScheme(
    TypeApply.func(
        (165, 179),
        TVar((165, 166), "x"),
        TypeApply.func(
            (170, 179),
            TVar((170, 171), "x"),
            TypeName((175, 179), "Bool"),
        ),
    ),
    {TVar((165, 166), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((180, 181), "+")] = TypeScheme(
    TypeApply.func(
        (183, 194),
        TVar((183, 184), "x"),
        TypeApply.func(
            (188, 194),
            TVar((188, 189), "x"),
            TVar((193, 194), "x"),
        ),
    ),
    {TVar((183, 184), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((195, 196), "-")] = TypeScheme(
    TypeApply.func(
        (198, 209),
        TVar((198, 199), "x"),
        TypeApply.func(
            (203, 209),
            TVar((203, 204), "x"),
            TVar((208, 209), "x"),
        ),
    ),
    {TVar((198, 199), "x")},
)

DEFAULT_OPERATOR_TYPES[Name((210, 212), "<>")] = TypeScheme(
    TypeApply.func(
        (214, 243),
        TypeApply((214, 221), TypeName((214, 218), "List"), TVar((219, 220), "x")),
        TypeApply.func(
            (225, 243),
            TypeApply((225, 232), TypeName((225, 229), "List"), TVar((230, 231), "x")),
            TypeApply((236, 243), TypeName((236, 240), "List"), TVar((241, 242), "x")),
        ),
    ),
    {TVar((219, 220), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((244, 245), "*")] = TypeScheme(
    TypeApply.func(
        (247, 258),
        TVar((247, 248), "x"),
        TypeApply.func(
            (252, 258),
            TVar((252, 253), "x"),
            TVar((257, 258), "x"),
        ),
    ),
    {TVar((247, 248), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((259, 260), "/")] = TypeScheme(
    TypeApply.func(
        (262, 273),
        TVar((262, 263), "x"),
        TypeApply.func(
            (267, 273),
            TVar((267, 268), "x"),
            TVar((272, 273), "x"),
        ),
    ),
    {TVar((262, 263), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((274, 275), "%")] = TypeScheme(
    TypeApply.func(
        (277, 288),
        TVar((277, 278), "x"),
        TypeApply.func(
            (282, 288),
            TVar((282, 283), "x"),
            TVar((287, 288), "x"),
        ),
    ),
    {TVar((277, 278), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((289, 290), "^")] = TypeApply.func(
    (292, 315),
    TypeName((292, 297), "Float"),
    TypeApply.func(
        (301, 315),
        TypeName((301, 306), "Float"),
        TypeName((310, 315), "Float"),
    ),
)
DEFAULT_OPERATOR_TYPES[Name((316, 317), "~")] = TypeScheme(
    TypeApply.func(
        (319, 325),
        TVar((319, 320), "x"),
        TVar((324, 325), "x"),
    ),
    {TVar((319, 320), "x")},
)
