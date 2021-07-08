from typing import List, Union

from lex import TokenStream, TokenTypes
import ast_ as ast

COMPARE_OPS = (
    TokenTypes.equal,
    TokenTypes.greater,
    TokenTypes.less,
    TokenTypes.fslash_equal,
    TokenTypes.greater_equal,
    TokenTypes.less_equal,
)
SCALAR_TOKENS = (
    TokenTypes.false,
    TokenTypes.float_,
    TokenTypes.integer,
    TokenTypes.name,
    TokenTypes.string,
    TokenTypes.true,
)


def parse(stream: TokenStream) -> ast.ASTNode:
    """
    Convert a stream of lexer tokens into an AST.

    Parameters
    ----------
    stream: TokenStream
        The lexer tokens used in parsing.

    Returns
    -------
    nodes.Block
        The program in AST format.
    """
    return _program(stream)


def _program(stream: TokenStream) -> ast.ASTNode:
    exprs = []
    while not stream.is_empty():
        expr = _expr(stream)
        stream.consume(TokenTypes.eol)
        exprs.append(expr)

    if exprs:
        return ast.Block(exprs[0].span, exprs)
    return ast.Vector((0, 0), ast.VectorTypes.TUPLE, ())


def _definition(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.let):
        first = stream.consume_get(TokenTypes.let)
        name_token = stream.consume_get(TokenTypes.name)
        stream.consume(TokenTypes.equal)
        value = _expr(stream)
        body = _expr(stream) if stream.consume_if(TokenTypes.in_) else None
        span = ast.merge(first.span, value.span if body is None else body.span)
        return ast.Define(span, ast.Name.from_token(name_token), value, body)
    return _pipe(stream)


def _pipe(stream: TokenStream) -> ast.ASTNode:
    left = _func(stream)
    if stream.peek(TokenTypes.pipe_greater):
        stream.consume(TokenTypes.pipe_greater)
        right = _pipe(stream)
        return ast.FuncCall(right, left)
    return left


def _func(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.bslash):
        first = stream.consume_get(TokenTypes.bslash)
        params = _params(stream)
        stream.consume(TokenTypes.arrow)
        body = _func(stream)
        return ast.Function.curry(ast.merge(first.span, body.span), params, body)
    return _cond(stream)


def _params(stream: TokenStream) -> List[ast.Name]:
    params: List[ast.Name] = []
    while stream.peek(TokenTypes.name):
        param = ast.Name.from_token(stream.consume_get(TokenTypes.name))
        params.append(param)
        if not stream.consume_if(TokenTypes.comma):
            break
    return params


def _cond(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.if_):
        first = stream.consume_get(TokenTypes.if_)
        pred = _and(stream)
        stream.consume(TokenTypes.then)
        cons = _cond(stream)
        stream.consume(TokenTypes.else_)
        else_ = _cond(stream)
        return ast.Cond(ast.merge(first.span, else_.span), pred, cons, else_)
    return _and(stream)


def _and(stream: TokenStream) -> ast.ASTNode:
    left = _or(stream)
    if stream.peek(TokenTypes.and_):
        op = stream.consume_get(TokenTypes.and_)
        right = _and(stream)
        return ast.FuncCall(ast.FuncCall(ast.Name(op.span, "and"), left), right)
    return left


def _or(stream: TokenStream) -> ast.ASTNode:
    left = _not(stream)
    if stream.peek(TokenTypes.or_):
        op = stream.consume_get(TokenTypes.or_)
        right = _or(stream)
        return ast.FuncCall(ast.FuncCall(ast.Name(op.span, "or"), left), right)
    return left


def _not(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.not_):
        op = stream.consume_get(TokenTypes.not_)
        operand = _not(stream)
        return ast.FuncCall(ast.Name(op.span, "not"), operand)
    return _compare(stream)


def _compare(stream: TokenStream) -> ast.ASTNode:
    left = _add_sub_con(stream)
    if stream.peek(*COMPARE_OPS):
        op = stream.consume_get(*COMPARE_OPS)
        right = _compare(stream)
        return ast.FuncCall(
            ast.FuncCall(ast.Name(op.span, op.type_.value), left), right
        )
    return left


def _add_sub_con(stream: TokenStream) -> ast.ASTNode:
    left = _mul_div_mod(stream)
    if stream.peek(TokenTypes.diamond, TokenTypes.plus, TokenTypes.dash):
        op = stream.consume_get(TokenTypes.diamond, TokenTypes.plus, TokenTypes.dash)
        right = _add_sub_con(stream)
        return ast.FuncCall(
            ast.FuncCall(ast.Name(op.span, op.type_.value), left), right
        )
    return left


def _mul_div_mod(stream: TokenStream) -> ast.ASTNode:
    left = _exponent(stream)
    if stream.peek(TokenTypes.asterisk, TokenTypes.fslash, TokenTypes.percent):
        op = stream.consume_get(
            TokenTypes.asterisk, TokenTypes.fslash, TokenTypes.percent
        )
        right = _mul_div_mod(stream)
        return ast.FuncCall(
            ast.FuncCall(ast.Name(op.span, op.type_.value), left), right
        )
    return left


def _exponent(stream: TokenStream) -> ast.ASTNode:
    result = _negate(stream)
    while stream.peek(TokenTypes.caret):
        op = stream.consume_get(TokenTypes.caret)
        other = _negate(stream)
        result = ast.FuncCall(ast.FuncCall(ast.Name(op.span, "^"), result), other)
    return result


def _negate(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.dash):
        op = stream.consume_get(TokenTypes.dash)
        operand = _negate(stream)
        return ast.FuncCall(ast.Name(op.span, "~"), operand)
    return _func_call(stream)


def _func_call(stream: TokenStream) -> ast.ASTNode:
    result = _list(stream)
    while stream.peek(TokenTypes.lparen):
        while not stream.peek(TokenTypes.rparen):
            result = ast.FuncCall(result, _expr(stream))
            if not stream.consume_if(TokenTypes.comma):
                break
        stream.consume(TokenTypes.rparen)
    return result


def _list(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.lbracket):
        first = stream.consume_get(TokenTypes.lbracket)
        elements = _elements(stream, TokenTypes.rbracket)
        last = stream.consume_get(TokenTypes.rbracket)
        return ast.Vector(
            ast.merge(first.span, last.span), ast.VectorTypes.LIST, elements
        )
    return _tuple(stream)


def _elements(stream: TokenStream, *end: TokenTypes) -> List[ast.ASTNode]:
    elements: List[ast.ASTNode] = []
    while not stream.peek(*end):
        elements.append(_expr(stream))
        if not stream.consume_if(TokenTypes.comma):
            break
    return elements


def _tuple(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.lparen):
        first = stream.consume_get(TokenTypes.lparen)
        elements = _elements(stream, TokenTypes.rparen)
        last = stream.consume_get(TokenTypes.rparen)
        if len(elements) == 1:
            return elements[0]
        return ast.Vector(
            ast.merge(first.span, last.span), ast.VectorTypes.TUPLE, elements
        )
    return _scalar(stream)


def _scalar(stream: TokenStream) -> Union[ast.Name, ast.Scalar]:
    token = stream.consume_get(*SCALAR_TOKENS)
    func = (
        ast.Name.from_token if stream.peek(TokenTypes.name) else ast.Scalar.from_token
    )
    return func(token)


_expr = _definition