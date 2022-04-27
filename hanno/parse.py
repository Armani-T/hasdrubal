# pylint: disable=C0116
from typing import Callable, cast, List, Mapping, Union

from asts import base, typed, types_ as types
from errors import merge, UnexpectedEOFError, UnexpectedTokenError
from lex import TokenStream, TokenTypes

PrefixParser = Callable[[TokenStream], base.ASTNode]
InfixParser = Callable[[TokenStream, base.ASTNode], base.ASTNode]


def _build_func_type(
    args: List[Union[base.Name, typed.Name]],
    return_type: types.Type,
) -> types.Type:
    for arg in reversed(args):
        arg_type = (
            arg.type_
            if isinstance(arg, typed.Name)
            else types.TypeVar.unknown((-1, -1))
        )
        return_type = types.TypeApply.func(
            merge(return_type.span, arg_type.span), arg_type, return_type
        )
    return return_type


# NOTE: Instead of doing a 2nd mini Pratt parser for the type level
# syntax, I decided to just use a recursive descent parser since it's
# not handling a lot of things.
def parse_type(stream: TokenStream) -> types.Type:
    left = parse_tuple_type(stream)
    if stream.consume_if(TokenTypes.arrow):
        right = parse_type(stream)
        return types.TypeApply.func(merge(left.span, right.span), left, right)
    return left


def parse_tuple_type(stream: TokenStream) -> types.Type:
    if stream.peek(TokenTypes.lparen):
        first = stream.consume(TokenTypes.lparen)
        elements = []
        while not stream.peek(TokenTypes.rparen):
            element = parse_type(stream)
            elements.append(element)
            if not stream.consume_if(TokenTypes.comma):
                break

        last = stream.consume(TokenTypes.rparen)
        span = merge(first.span, last.span)
        if not elements:
            return types.TypeName.unit(span)
        if len(elements) == 1:
            return elements[0]
        return types.TypeApply.tuple_(span, elements)
    return parse_generic_type(stream)


def parse_generic_type(stream: TokenStream) -> types.Type:
    base_token = stream.consume(TokenTypes.name_)
    type_: Union[types.TypeApply, types.TypeName]
    type_ = types.TypeName(base_token.span, base_token.value)  # type: ignore

    if stream.consume_if(TokenTypes.lbracket):
        while not stream.peek(TokenTypes.rparen):
            arg = parse_type(stream)
            type_ = types.TypeApply(merge(type_.span, arg.span), type_, arg)
            if not stream.consume_if(TokenTypes.comma):
                break
    return type_


def parse_body_section(stream: TokenStream) -> base.ASTNode:
    if stream.consume_if(TokenTypes.equal):
        return parse_expr(stream, 0)

    stream.consume(TokenTypes.colon_equal)
    body = parse_block(stream, TokenTypes.end)
    return body


def parse_block(stream: TokenStream, *expected_ends: TokenTypes) -> base.ASTNode:
    if not expected_ends:
        raise ValueError("This function requires at least 1 expected `TokenTypes`.")

    exprs = []
    while not stream.consume_if(*expected_ends):
        expr = parse_expr(stream, 0)
        stream.consume(TokenTypes.eol)
        exprs.append(expr)

    if not exprs:
        next_token = stream.preview()
        return base.Unit(next_token.span)
    if len(exprs) == 1:
        return exprs[0]
    return base.Block(merge(exprs[0].span, exprs[-1].span), exprs)


def parse_elements(stream: TokenStream, *end: TokenTypes) -> List[base.ASTNode]:
    precendence = precedence_table[TokenTypes.comma]
    elements: List[base.ASTNode] = []
    while not stream.peek(*end):
        elements.append(parse_expr(stream, precendence))
        if not stream.consume_if(TokenTypes.comma):
            break
    return elements


def parse_parameters(stream: TokenStream) -> List[base.Name]:
    params: List[base.Name] = []
    while stream.peek(TokenTypes.name_):
        name_token = stream.consume(TokenTypes.name_)
        param: base.Name
        if stream.peek(TokenTypes.colon):
            stream.consume(TokenTypes.colon)
            param_type = parse_type(stream)
            param = typed.Name(name_token.span, param_type, name_token.value)
        else:
            param = base.Name(name_token.span, name_token.value)
        params.append(param)
        if not stream.consume_if(TokenTypes.comma):
            break

    if params:
        return params
    stream.consume(TokenTypes.name_)
    assert False


def build_infix_op(
    token_type: TokenTypes, right_associative: bool = False
) -> InfixParser:
    def inner(stream: TokenStream, left: base.ASTNode) -> base.Apply:
        op = stream.consume(token_type)
        right = parse_expr(
            stream,
            precedence_table[token_type] - int(right_associative),
        )
        return base.Apply(
            merge(left.span, right.span),
            base.Apply(
                merge(left.span, op.span),
                base.Name(op.span, token_type.value),
                left,
            ),
            right,
        )

    return inner


def parse_apply(stream: TokenStream, left: base.ASTNode) -> base.ASTNode:
    stream.consume(TokenTypes.lparen)
    arguments = parse_elements(stream, TokenTypes.rparen)
    # NOTE: I'm using `parse_elements` because it parses exactly
    # what I need: multiple comma-separated expressions with an
    # arbitrary end token.
    last = stream.consume(TokenTypes.rparen)
    result: base.ASTNode = left
    for argument in arguments:
        result = base.Apply(merge(result.span, argument.span), result, argument)
    result.span = merge(left.span, last.span)
    return result


def parse_define(stream: TokenStream) -> base.Define:
    start_token = stream.consume(TokenTypes.let)
    target_token = stream.consume(TokenTypes.name_)
    if stream.consume_if(TokenTypes.lparen):
        params = parse_parameters(stream)
        stream.consume(TokenTypes.rparen)
        if stream.consume_if(TokenTypes.arrow):
            return_type = parse_type(stream)
            body = parse_body_section(stream)
            return typed.Define(
                merge(start_token.span, body.span),
                _build_func_type(params, return_type),
                typed.Name(
                    target_token.span,
                    types.TypeVar.unknown(target_token.span),
                    target_token.value,
                ),
                base.Function.curry(merge(target_token.span, body.span), params, body),
            )
        body = parse_body_section(stream)
        return base.Define(
            merge(start_token.span, body.span),
            base.Name(target_token.span, target_token.value),
            base.Function.curry(merge(target_token.span, body.span), params, body),
        )

    target: Union[typed.Name, base.Name]
    if stream.consume_if(TokenTypes.colon):
        type_ann = parse_type(stream)
        target = typed.Name(target_token.span, type_ann, target_token.value)
    else:
        target = base.Name(target_token.span, target_token.value)

    body = parse_body_section(stream)
    return base.Define(merge(start_token.span, body.span), target, body)


def parse_dot(stream: TokenStream, left: base.ASTNode) -> base.Apply:
    stream.consume(TokenTypes.dot)
    name_token = stream.consume(TokenTypes.name_)
    right = base.Name(name_token.span, name_token.value)
    return base.Apply(merge(left.span, right.span), right, left)


def parse_func(stream: TokenStream) -> base.ASTNode:
    first = stream.consume(TokenTypes.bslash)
    params = parse_parameters(stream)
    stream.consume(TokenTypes.arrow)
    body = parse_expr(stream, precedence_table[TokenTypes.bslash])
    return base.Function.curry(merge(first.span, body.span), params, body)


def parse_if(stream: TokenStream) -> base.ASTNode:
    first = stream.consume(TokenTypes.if_)
    pred = parse_expr(stream, precedence_table[TokenTypes.if_])
    stream.consume(TokenTypes.then)
    cons = parse_expr(stream, precedence_table[TokenTypes.if_])
    stream.consume(TokenTypes.else_)
    else_ = parse_expr(stream, precedence_table[TokenTypes.if_])
    return base.Cond(merge(first.span, else_.span), pred, cons, else_)


def parse_list(stream: TokenStream) -> base.ASTNode:
    first = stream.consume(TokenTypes.lbracket)
    elements = parse_elements(stream, TokenTypes.rbracket)
    last = stream.consume(TokenTypes.rbracket)
    return base.List(merge(first.span, last.span), elements)


def parse_name(stream: TokenStream) -> base.ASTNode:
    token = stream.consume(TokenTypes.name_)
    return base.Name(token.span, token.value)


def parse_negate(stream: TokenStream) -> base.Apply:
    token = stream.consume(TokenTypes.dash)
    operand = parse_expr(stream, precedence_table[TokenTypes.dash])
    return base.Apply(
        merge(token.span, operand.span), base.Name(token.span, "~"), operand
    )


def parse_not(stream: TokenStream) -> base.Apply:
    token = stream.consume(TokenTypes.not_)
    operand = parse_expr(stream, precedence_table[TokenTypes.not_])
    return base.Apply(
        merge(token.span, operand.span), base.Name(token.span, "not"), operand
    )


def parse_pair(stream: TokenStream, left: base.ASTNode) -> base.ASTNode:
    stream.consume(TokenTypes.comma)
    right = parse_expr(stream, precedence_table[TokenTypes.comma] - 1)
    return base.Pair(merge(left.span, right.span), left, right)


def parse_scalar(stream: TokenStream) -> base.Scalar:
    token = stream.consume(
        TokenTypes.false,
        TokenTypes.float_,
        TokenTypes.integer,
        TokenTypes.string,
        TokenTypes.true,
    )
    type_: TokenTypes = token.type_
    value = cast(str, token.value)
    if type_ == TokenTypes.false:
        return base.Scalar(token.span, False)
    if type_ == TokenTypes.float_:
        return base.Scalar(token.span, float(value))
    if type_ == TokenTypes.integer:
        return base.Scalar(token.span, int(value))
    if type_ == TokenTypes.string:
        return base.Scalar(token.span, value[1:-1])
    if type_ == TokenTypes.true:
        return base.Scalar(token.span, True)
    assert False


def parse_group(stream: TokenStream) -> base.ASTNode:
    start_token = stream.consume(TokenTypes.lparen)
    expr = (
        base.Unit((0, 0)) if stream.peek(TokenTypes.rparen) else parse_expr(stream, 0)
    )
    end_token = stream.consume(TokenTypes.rparen)
    expr.span = merge(start_token.span, end_token.span)
    return expr


prefix_parsers: Mapping[TokenTypes, PrefixParser] = {
    TokenTypes.if_: parse_if,
    TokenTypes.bslash: parse_func,
    TokenTypes.name_: parse_name,
    TokenTypes.lbracket: parse_list,
    TokenTypes.lparen: parse_group,
    TokenTypes.let: parse_define,
    TokenTypes.not_: parse_not,
    TokenTypes.dash: parse_negate,
    TokenTypes.false: parse_scalar,
    TokenTypes.float_: parse_scalar,
    TokenTypes.integer: parse_scalar,
    TokenTypes.string: parse_scalar,
    TokenTypes.true: parse_scalar,
}
infix_parsers: Mapping[TokenTypes, InfixParser] = {
    TokenTypes.and_: build_infix_op(TokenTypes.and_),
    TokenTypes.or_: build_infix_op(TokenTypes.or_),
    TokenTypes.greater: build_infix_op(TokenTypes.greater),
    TokenTypes.less: build_infix_op(TokenTypes.less),
    TokenTypes.greater_equal: build_infix_op(TokenTypes.greater_equal),
    TokenTypes.less_equal: build_infix_op(TokenTypes.less_equal),
    TokenTypes.equal: build_infix_op(TokenTypes.equal),
    TokenTypes.question_equal: build_infix_op(TokenTypes.question_equal),
    TokenTypes.plus: build_infix_op(TokenTypes.plus),
    TokenTypes.dash: build_infix_op(TokenTypes.dash),
    TokenTypes.diamond: build_infix_op(TokenTypes.diamond),
    TokenTypes.fslash: build_infix_op(TokenTypes.fslash, right_associative=True),
    TokenTypes.asterisk: build_infix_op(TokenTypes.asterisk),
    TokenTypes.percent: build_infix_op(TokenTypes.percent),
    TokenTypes.caret: build_infix_op(TokenTypes.caret),
    TokenTypes.lparen: parse_apply,
    TokenTypes.dot: parse_dot,
    TokenTypes.comma: parse_pair,
}

precedence_table: Mapping[TokenTypes, int] = {
    TokenTypes.let: 0,
    TokenTypes.comma: 10,
    TokenTypes.bslash: 20,
    TokenTypes.if_: 30,
    TokenTypes.and_: 40,
    TokenTypes.or_: 50,
    TokenTypes.not_: 60,
    TokenTypes.greater: 70,
    TokenTypes.less: 70,
    TokenTypes.greater_equal: 70,
    TokenTypes.less_equal: 70,
    TokenTypes.question_equal: 70,
    TokenTypes.equal: 70,
    TokenTypes.plus: 80,
    TokenTypes.dash: 80,
    TokenTypes.diamond: 80,
    TokenTypes.fslash: 90,
    TokenTypes.asterisk: 90,
    TokenTypes.percent: 90,
    TokenTypes.caret: 100,
    TokenTypes.lparen: 110,
    TokenTypes.dot: 120,
}


def parse_expr(stream: TokenStream, current_precedence: int) -> base.ASTNode:
    first_token = stream.preview()
    if first_token is None:
        raise UnexpectedEOFError()

    prefix_parser = prefix_parsers.get(first_token.type_)
    if prefix_parser is None:
        raise UnexpectedTokenError(first_token)

    left = prefix_parser(stream)
    op = stream.preview()
    while op is not None and precedence_table.get(op.type_, -1) > current_precedence:
        infix_parser = infix_parsers.get(op.type_)
        if infix_parser is None:
            break

        left = infix_parser(stream, left)
        op = stream.preview()
    return left


def parse(stream: TokenStream) -> base.ASTNode:
    """
    Convert a stream of lexer tokens into an AST.

    Parameters
    ----------
    stream: TokenStream
        The lexer tokens used in parsing.

    Returns
    -------
    nodes.ASTNode
        The program in AST format.
    """
    exprs = []
    while stream:
        exprs.append(parse_expr(stream, 0))
        stream.consume(TokenTypes.eol)

    if not exprs:
        return base.Unit((0, 0))
    if len(exprs) == 1:
        return exprs[0]
    return base.Block(merge(exprs[0].span, exprs[-1].span), exprs)