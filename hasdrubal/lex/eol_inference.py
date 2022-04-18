from typing import Container, Optional

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


def can_add_eol(prev: Token, next_: Optional[Token], stack_size: int) -> bool:
    """
    Check whether an EOL token can be added at the current position.

    Parameters
    ----------
    prev: Token
        The tokens present in the raw stream that came from the lexer.
    next_: Stream
        The next token in the stream, or `None` if the stream is empty.
    stack_size: int
        If it's `!= 0`, then there are enclosing brackets/parentheses.

    Returns
    -------
    bool
        Whether to add an EOL token at the current position.
    """
    return (
        stack_size == 0
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
    return TokenStream(insert_eols(stream))


def insert_eols(stream):
    has_run = False
    paren_stack_size = 0
    prev_token = Token((0, 0), TokenTypes.eol, None)
    token: Optional[Token] = next(stream, None)
    while token is not None:
        has_run = True
        if token.type_ == TokenTypes.newline:
            next_token: Optional[Token] = next(stream, None)
            if next_token is None:
                break
            if can_add_eol(prev_token, next_token, paren_stack_size):
                yield Token(
                    (prev_token.span[1], next_token.span[0]), TokenTypes.eol, None
                )
            token = next_token
            continue
        if token.type_ in OPENERS:
            paren_stack_size += 1
        elif token.type_ in CLOSERS:
            paren_stack_size -= 1
        yield token
        prev_token, token = token, next(stream, None)

    if has_run and prev_token.type_ != TokenTypes.eol:
        yield Token(
            (prev_token.span[1], prev_token.span[1] + 1),
            TokenTypes.eol,
            None,
        )
