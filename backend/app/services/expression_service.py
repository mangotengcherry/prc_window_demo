"""Spotfire/SQL 통합 서브셋 필터식 파서·평가기 (§5).

`eval`/`exec`/`DataFrame.query`는 사용하지 않는다. 자체 정규식 토크나이저 →
재귀 하강 파서 → AST → pandas 벡터 연산(`evaluate`)으로 처리한다.
"""

from __future__ import annotations

import difflib
import operator
import re
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


class ExpressionError(Exception):
    def __init__(self, message: str, position: int = 0):
        super().__init__(message)
        self.message = message
        self.position = position


# ---------------------------------------------------------------------------
# AST 노드
# ---------------------------------------------------------------------------


@dataclass
class Literal:
    value: Any
    kind: str  # "number" | "string" | "bool"


@dataclass
class Column:
    name: str
    pos: int


@dataclass
class UnaryNot:
    operand: Any


@dataclass
class BinOp:
    op: str
    left: Any
    right: Any
    pos: int = 0


@dataclass
class InOp:
    target: Any
    values: list[Literal]
    negate: bool


@dataclass
class IsNullOp:
    target: Any
    negate: bool


@dataclass
class FuncCall:
    name: str
    arg: Any


@dataclass
class CaseWhen:
    branches: list[tuple[Any, Any]]
    else_value: Any | None


# ---------------------------------------------------------------------------
# 토크나이저
# ---------------------------------------------------------------------------

_KEYWORDS = {
    "AND", "OR", "NOT", "IN", "IS", "NULL", "TRUE", "FALSE",
    "CASE", "WHEN", "THEN", "ELSE", "END",
    "ABS", "LOG", "LOG10", "SQRT",
}
_FUNCS = {"ABS", "LOG", "LOG10", "SQRT"}
_FUNC_MAP = {"ABS": np.abs, "LOG": np.log, "LOG10": np.log10, "SQRT": np.sqrt}

_TOKEN_SPEC = [
    ("SKIP", r"[ \t\r\n]+"),
    ("BRACKET_COLUMN", r"\[[^\]]+\]"),
    ("STRING", r"'[^']*'|\"[^\"]*\""),
    ("NUMBER", r"\d+\.\d+|\d+"),
    ("OP", r"!=|<>|==|>=|<=|=|>|<|\+|-|\*|/|\(|\)|,"),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
]
_TOKEN_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in _TOKEN_SPEC))


@dataclass
class Token:
    type: str
    value: str
    pos: int


def _tokenize(expression: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    length = len(expression)
    while pos < length:
        match = _TOKEN_RE.match(expression, pos)
        if not match:
            raise ExpressionError(f"인식할 수 없는 문자: '{expression[pos]}'", pos)
        kind = match.lastgroup
        value = match.group()
        if kind != "SKIP":
            tokens.append(Token(kind, value, pos))
        pos = match.end()
    tokens.append(Token("EOF", "", length))
    return tokens


# ---------------------------------------------------------------------------
# 재귀 하강 파서
# ---------------------------------------------------------------------------

_CMP_OPS = {"=", "==", "!=", "<>", ">", ">=", "<", "<="}


class _Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.i = 0

    def peek(self) -> Token:
        return self.tokens[self.i]

    def peek_next(self) -> Token:
        return self.tokens[min(self.i + 1, len(self.tokens) - 1)]

    def advance(self) -> Token:
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    @staticmethod
    def _is_keyword(tok: Token, word: str) -> bool:
        return tok.type == "IDENT" and tok.value.upper() == word

    def _expect_keyword(self, word: str) -> Token:
        tok = self.peek()
        if not self._is_keyword(tok, word):
            raise ExpressionError(f"'{word}' 키워드가 필요합니다", tok.pos)
        return self.advance()

    def _expect_op(self, value: str) -> Token:
        tok = self.peek()
        if not (tok.type == "OP" and tok.value == value):
            raise ExpressionError(f"'{value}' 가 필요합니다", tok.pos)
        return self.advance()

    def parse_expr(self) -> Any:
        if self._is_keyword(self.peek(), "CASE"):
            return self._parse_case()
        return self._parse_or()

    def _parse_case(self) -> Any:
        self._expect_keyword("CASE")
        branches: list[tuple[Any, Any]] = []
        self._expect_keyword("WHEN")
        while True:
            cond = self.parse_expr()
            self._expect_keyword("THEN")
            value = self.parse_expr()
            branches.append((cond, value))
            if self._is_keyword(self.peek(), "WHEN"):
                self.advance()
                continue
            break
        else_value = None
        if self._is_keyword(self.peek(), "ELSE"):
            self.advance()
            else_value = self.parse_expr()
        self._expect_keyword("END")
        return CaseWhen(branches, else_value)

    def _parse_or(self) -> Any:
        left = self._parse_and()
        while self._is_keyword(self.peek(), "OR"):
            tok = self.advance()
            right = self._parse_and()
            left = BinOp("OR", left, right, tok.pos)
        return left

    def _parse_and(self) -> Any:
        left = self._parse_not()
        while self._is_keyword(self.peek(), "AND"):
            tok = self.advance()
            right = self._parse_not()
            left = BinOp("AND", left, right, tok.pos)
        return left

    def _parse_not(self) -> Any:
        if self._is_keyword(self.peek(), "NOT"):
            self.advance()
            return UnaryNot(self._parse_comparison())
        return self._parse_comparison()

    def _parse_comparison(self) -> Any:
        left = self._parse_additive()
        tok = self.peek()
        if tok.type == "OP" and tok.value in _CMP_OPS:
            self.advance()
            right = self._parse_additive()
            return BinOp(tok.value, left, right, tok.pos)
        if self._is_keyword(tok, "NOT") and self._is_keyword(self.peek_next(), "IN"):
            self.advance()
            self.advance()
            return self._parse_in_tail(left, negate=True)
        if self._is_keyword(tok, "IN"):
            self.advance()
            return self._parse_in_tail(left, negate=False)
        if self._is_keyword(tok, "IS"):
            self.advance()
            negate = False
            if self._is_keyword(self.peek(), "NOT"):
                self.advance()
                negate = True
            self._expect_keyword("NULL")
            return IsNullOp(left, negate)
        return left

    def _parse_in_tail(self, target: Any, negate: bool) -> Any:
        self._expect_op("(")
        values = [self._parse_literal()]
        while self.peek().type == "OP" and self.peek().value == ",":
            self.advance()
            values.append(self._parse_literal())
        self._expect_op(")")
        return InOp(target, values, negate)

    def _parse_additive(self) -> Any:
        left = self._parse_term()
        while self.peek().type == "OP" and self.peek().value in ("+", "-"):
            tok = self.advance()
            right = self._parse_term()
            left = BinOp(tok.value, left, right, tok.pos)
        return left

    def _parse_term(self) -> Any:
        left = self._parse_factor()
        while self.peek().type == "OP" and self.peek().value in ("*", "/"):
            tok = self.advance()
            right = self._parse_factor()
            left = BinOp(tok.value, left, right, tok.pos)
        return left

    def _parse_factor(self) -> Any:
        tok = self.peek()
        if tok.type == "OP" and tok.value == "(":
            self.advance()
            inner = self.parse_expr()
            self._expect_op(")")
            return inner
        if tok.type == "IDENT" and tok.value.upper() in _FUNCS:
            func_name = self.advance().value.upper()
            self._expect_op("(")
            arg = self.parse_expr()
            self._expect_op(")")
            return FuncCall(func_name, arg)
        if tok.type == "NUMBER" or tok.type == "STRING" or self._is_keyword(tok, "TRUE") or self._is_keyword(tok, "FALSE"):
            return self._parse_literal()
        if tok.type == "BRACKET_COLUMN":
            self.advance()
            return Column(tok.value[1:-1], tok.pos)
        if tok.type == "IDENT" and tok.value.upper() not in _KEYWORDS:
            self.advance()
            return Column(tok.value, tok.pos)
        raise ExpressionError(f"예상치 못한 토큰: '{tok.value}'", tok.pos)

    def _parse_literal(self) -> Literal:
        tok = self.peek()
        if tok.type == "NUMBER":
            self.advance()
            value = float(tok.value) if "." in tok.value else int(tok.value)
            return Literal(value, "number")
        if tok.type == "STRING":
            self.advance()
            return Literal(tok.value[1:-1], "string")
        if self._is_keyword(tok, "TRUE"):
            self.advance()
            return Literal(True, "bool")
        if self._is_keyword(tok, "FALSE"):
            self.advance()
            return Literal(False, "bool")
        raise ExpressionError(f"리터럴이 필요합니다: '{tok.value}'", tok.pos)


def parse(expression: str) -> Any:
    if not expression or not expression.strip():
        raise ExpressionError("빈 필터식은 지원하지 않습니다", 0)
    tokens = _tokenize(expression)
    parser = _Parser(tokens)
    ast = parser.parse_expr()
    tok = parser.peek()
    if tok.type != "EOF":
        raise ExpressionError(f"예상치 못한 토큰: '{tok.value}'", tok.pos)
    return ast


# ---------------------------------------------------------------------------
# 평가
# ---------------------------------------------------------------------------

_COMPARISON_OPS = {
    "=": operator.eq,
    "==": operator.eq,
    "!=": operator.ne,
    "<>": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}
_ARITH_OPS = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}


def resolve_column(name: str, df: pd.DataFrame, pos: int = 0) -> str:
    lower_map = {str(c).lower(): c for c in df.columns}
    key = name.strip().lower()
    if key in lower_map:
        return lower_map[key]
    suggestions = difflib.get_close_matches(key, lower_map.keys(), n=3)
    hint = f" — 유사: {', '.join(lower_map[s] for s in suggestions)}" if suggestions else ""
    raise ExpressionError(f"알 수 없는 컬럼 [{name}]{hint}", pos)


def _value_kind(value: Any) -> str:
    if isinstance(value, pd.Series):
        dtype = value.dtype
        if pd.api.types.is_bool_dtype(dtype):
            return "bool"
        if pd.api.types.is_numeric_dtype(dtype):
            return "numeric"
        return "string"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float, np.integer, np.floating)):
        return "numeric"
    if isinstance(value, str):
        return "string"
    return "other"


def _negate(value: Any) -> Any:
    return ~value if isinstance(value, pd.Series) else not value


def _evaluate_case(node: CaseWhen, df: pd.DataFrame) -> pd.Series:
    conditions = []
    choices = []
    for cond_node, value_node in node.branches:
        cond_val = _evaluate(cond_node, df)
        if not isinstance(cond_val, pd.Series):
            cond_val = pd.Series(cond_val, index=df.index)
        if not pd.api.types.is_bool_dtype(cond_val):
            raise ExpressionError("CASE WHEN 조건은 boolean 이어야 합니다", 0)
        value_val = _evaluate(value_node, df)
        if not isinstance(value_val, pd.Series):
            value_val = pd.Series([value_val] * len(df), index=df.index)
        conditions.append(cond_val.to_numpy())
        choices.append(value_val.to_numpy())
    if node.else_value is not None:
        else_val = _evaluate(node.else_value, df)
        if not isinstance(else_val, pd.Series):
            else_val = pd.Series([else_val] * len(df), index=df.index)
        default = else_val.to_numpy()
    else:
        default = np.array([None] * len(df), dtype=object)
    result = np.select(conditions, choices, default=default)
    return pd.Series(result, index=df.index)


def _evaluate(node: Any, df: pd.DataFrame) -> Any:
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, Column):
        col = resolve_column(node.name, df, node.pos)
        return df[col]
    if isinstance(node, UnaryNot):
        return _negate(_evaluate(node.operand, df))
    if isinstance(node, BinOp):
        left = _evaluate(node.left, df)
        right = _evaluate(node.right, df)
        if node.op in _COMPARISON_OPS:
            kinds = {_value_kind(left), _value_kind(right)}
            if kinds == {"string", "numeric"}:
                raise ExpressionError("타입 불일치: 문자열과 숫자는 비교할 수 없습니다", node.pos)
            return _COMPARISON_OPS[node.op](left, right)
        if node.op in _ARITH_OPS:
            return _ARITH_OPS[node.op](left, right)
        if node.op in ("AND", "OR"):
            left_series = left if isinstance(left, pd.Series) else pd.Series(left, index=df.index)
            right_series = right if isinstance(right, pd.Series) else pd.Series(right, index=df.index)
            return (left_series & right_series) if node.op == "AND" else (left_series | right_series)
        raise ExpressionError(f"지원하지 않는 연산자: {node.op}", node.pos)
    if isinstance(node, InOp):
        target = _evaluate(node.target, df)
        values = [literal.value for literal in node.values]
        result = target.isin(values) if isinstance(target, pd.Series) else (target in values)
        return _negate(result) if node.negate else result
    if isinstance(node, IsNullOp):
        target = _evaluate(node.target, df)
        result = target.isna() if isinstance(target, pd.Series) else bool(pd.isna(target))
        return _negate(result) if node.negate else result
    if isinstance(node, FuncCall):
        return _FUNC_MAP[node.name](_evaluate(node.arg, df))
    if isinstance(node, CaseWhen):
        return _evaluate_case(node, df)
    raise ExpressionError(f"알 수 없는 노드: {node}", 0)


def evaluate_filter(expression: str, df: pd.DataFrame) -> pd.Series:
    ast = parse(expression)
    result = _evaluate(ast, df)
    if not isinstance(result, pd.Series):
        result = pd.Series(result, index=df.index)
    if not pd.api.types.is_bool_dtype(result):
        raise ExpressionError(f"filter 식은 boolean 결과여야 합니다 (실제 결과 타입: {result.dtype})", 0)
    return result


def evaluate_column(expression: str, df: pd.DataFrame) -> pd.Series:
    ast = parse(expression)
    result = _evaluate(ast, df)
    if not isinstance(result, pd.Series):
        result = pd.Series([result] * len(df), index=df.index)
    return result


def columns_used(expression: str) -> list[str]:
    ast = parse(expression)
    names: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, Column):
            if node.name not in names:
                names.append(node.name)
        elif isinstance(node, UnaryNot):
            walk(node.operand)
        elif isinstance(node, BinOp):
            walk(node.left)
            walk(node.right)
        elif isinstance(node, InOp):
            walk(node.target)
        elif isinstance(node, IsNullOp):
            walk(node.target)
        elif isinstance(node, FuncCall):
            walk(node.arg)
        elif isinstance(node, CaseWhen):
            for cond, value in node.branches:
                walk(cond)
                walk(value)
            if node.else_value is not None:
                walk(node.else_value)

    walk(ast)
    return names
