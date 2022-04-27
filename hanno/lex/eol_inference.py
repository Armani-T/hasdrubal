from typing import Container, Iterator

from .main import Token, TokenStream
from .tokens import TokenTypes

OPENERS: Container[TokenTypes] = (TokenTypes.lbracket, TokenTypes.lparen)
CLOSERS: Container[TokenTypes] = (TokenTypes.rbracket, TokenTypes.rparen)

VALID_STARTS: Container[TokenTypes] = (
    TokenTypes.bslash,
    TokenTypes.end,
    TokenTypes.false,
    TokenTypes.float_,
    TokenTypes.if_,
    TokenTypes.integer,
    TokenTypes.lbracket,
    TokenTypes.let,
    TokenTypes.lparen,
    TokenTypes.not_,
    TokenTypes.name_,
    TokenTypes.string,
    TokenTypes.tilde,
    TokenTypes.true,
)
VALID_ENDS: Container[TokenTypes] = (
    TokenTypes.end,
    TokenTypes.false,
    TokenTypes.float_,
    TokenTypes.integer,
    TokenTypes.name_,
    TokenTypes.rbracket,
    TokenTypes.rparen,
    TokenTypes.string,
    TokenTypes.true,
)


def can_add_eol(
    prev: Token,
    current: Token,
    next_: Token,
    stack_size: int,
) -> bool:
    """
    Check whether an EOL token can be added at the current position.

    Parameters
    ----------
    prev: Token
        The tokens present in the raw stream that came from the lexer.
    current: Token
        The whitespace token that triggered the calling of this
        function.
    next_: Token
        The next token in the stream.
    stack_size: int
        If it's `> 0`, then there are enclosing brackets/parentheses.

    Returns
    -------
    bool
        Whether to add an EOL token at the current position.
    """
    return (
        (stack_size == 0)
        and (current.value is not None)
        and ("\n" in current.value)
        and (prev.type_ in VALID_ENDS)
        and (next_ is None or next_.type_ in VALID_STARTS)
    )


def infer_eols(stream: TokenStream) -> TokenStream:
    """
    Replace `whitespace` with `eol` tokens, as needed, in the stream.

    Parameters
    ----------
    stream: TokenStream
        The raw token stream straight from the lexer.

    Returns
    -------
    Stream
        The stream with the inferred eols.
    """
    tokens = tuple(insert_eols(stream))
    return TokenStream(tokens, [])


def insert_eols(stream: TokenStream) -> Iterator[Token]:
    """
    Remove `whitespace` tokens from `stream` and replace them with
    `eol` tokens if applicable or drop them otherwise.

    Parameters
    ----------
    stream: TokenStream
        The stream of tokens that we're inferring EOLs for. The only
        token that isn't allowed in here is `comment` so please
        ensure that it is part of `stream.ignore`.

    Returns
    -------
    Iterator[Token]
        The stream of tokens with `eol` tokens inserted where needed.
    """
    has_run = False
    paren_stack_size = 0
    prev_token = Token((0, 0), TokenTypes.eol, None)
    for token in stream:
        has_run = True
        if token.type_ == TokenTypes.whitespace:
            next_token = stream.preview()
            if can_add_eol(prev_token, token, next_token, paren_stack_size):
                prev_token = Token(token.span, TokenTypes.eol, None)
                yield prev_token
            continue

        prev_token = token
        paren_stack_size += (
            1 if token.type_ in OPENERS else -1 if token.type_ in CLOSERS else 0
        )
        yield token

    # pylint: disable=W0631
    if has_run and token.type_ != TokenTypes.eol:
        end = prev_token.span[1]
        yield Token((end, end + 1), TokenTypes.eol, None)