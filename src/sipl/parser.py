"""Парсер SIPL: текст -> типізоване AST (власні вузли, не дерево Lark)."""

from __future__ import annotations

from functools import lru_cache
from importlib import resources

from lark import Lark, Token, Transformer, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedEOF, UnexpectedInput, UnexpectedToken

from . import ast as A
from .diagnostics import Diagnostic, SiplSyntaxError

_FRIENDLY = {
    "VAR": "змінна",
    "NUM": "число",
    "OR": "∨",
    "NOT": "¬",
    "$END": "кінець файлу",
}

_HINTS = {
    "<": "оператора '<' немає в SIPL: замість X < Y напишіть Y > X",
    ">=": "оператора '>=' немає в SIPL: використайте X > Y ∨ X = Y",
    "<=": "оператора '<=' немає в SIPL: використайте ¬ X > Y",
    "!=": "оператора '!=' немає в SIPL: використайте ¬ X = Y",
    "/": "ділення немає в базовій SIPL: реалізуйте його циклом через +, -",
    "div": "операції div немає в базовій SIPL: реалізуйте її циклом через +, -",
    "mod": "операції mod немає в базовій SIPL: реалізуйте її циклом через +, -",
}


def grammar_text() -> str:
    return resources.files("sipl").joinpath("grammar/sipl.lark").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _lark() -> Lark:
    return Lark(grammar_text(), parser="earley", lexer="dynamic", propagate_positions=True)


def _span_meta(meta) -> A.SourceSpan | None:
    if getattr(meta, "empty", True):
        return None
    return A.SourceSpan(meta.start_pos, meta.end_pos, meta.line, meta.column, meta.end_line, meta.end_column)


def _span_tok(t: Token) -> A.SourceSpan:
    return A.SourceSpan(t.start_pos, t.end_pos, t.line, t.column, t.end_line, t.end_column)


@v_args(meta=True, inline=True)
class _ToAst(Transformer):
    def start(self, meta, body):
        return A.Program(body, span=_span_meta(meta))

    def seq(self, meta, a, b):
        return A.Seq(a, b, span=_span_meta(meta))

    def assign(self, meta, name, expr):
        return A.Assign(str(name), expr, span=_span_meta(meta))

    def if_(self, meta, c, t, e):
        return A.If(c, t, e, span=_span_meta(meta))

    def while_(self, meta, c, b):
        return A.While(c, b, span=_span_meta(meta))

    def block(self, meta, b):
        return A.Block(b, span=_span_meta(meta))

    def skip(self, meta):
        return A.Skip(span=_span_meta(meta))

    def add(self, meta, a, b):
        return A.BinOp("+", a, b, span=_span_meta(meta))

    def sub(self, meta, a, b):
        return A.BinOp("-", a, b, span=_span_meta(meta))

    def mul(self, meta, a, b):
        return A.BinOp("*", a, b, span=_span_meta(meta))

    def num(self, meta, tok):
        return A.Num(int(tok), str(tok), span=_span_tok(tok))

    def var(self, meta, tok):
        return A.Var(str(tok), span=_span_tok(tok))

    def apar(self, meta, e):
        return A.ParenA(e, span=_span_meta(meta))

    def eq(self, meta, a, b):
        return A.Cmp("=", a, b, span=_span_meta(meta))

    def gr(self, meta, a, b):
        return A.Cmp(">", a, b, span=_span_meta(meta))

    def or_(self, meta, a, op, b):
        return A.Or(a, b, str(op), span=_span_meta(meta))

    def not_(self, meta, op, b):
        return A.Not(b, str(op), span=_span_meta(meta))

    def bpar(self, meta, b):
        return A.ParenB(b, span=_span_meta(meta))


def _expected_names(names) -> list[str]:
    out = []
    lark = _lark()
    for n in sorted(set(names or [])):
        if n in _FRIENDLY:
            out.append(_FRIENDLY[n])
            continue
        try:
            pat = lark.get_terminal(n).pattern
            out.append(f"'{pat.value}'" if pat.type == "str" else n)
        except KeyError:
            out.append(n)
    return sorted(set(out))


def _line_col(text: str, pos: int) -> tuple[int, int]:
    line = text.count("\n", 0, pos) + 1
    col = pos - (text.rfind("\n", 0, pos) + 1) + 1
    return line, col


def _hint_for(text: str, pos: int) -> str | None:
    for start in (pos - 1, pos):
        if start < 0:
            continue
        rest = text[start:start + 3]
        for k in sorted(_HINTS, key=len, reverse=True):
            if rest.startswith(k) and start + len(k) > pos:
                return _HINTS[k]
    return None


def _diagnostic(text: str, e: UnexpectedInput) -> Diagnostic:
    if isinstance(e, UnexpectedEOF):
        line, col = _line_col(text, len(text.rstrip()))
        exp = ", ".join(_expected_names(e.expected))
        return Diagnostic("E001", f"Неочікуваний кінець програми. Очікувалось: {exp}", line, col)
    pos = getattr(e, "pos_in_stream", None)
    if pos is None:
        pos = 0
    line, col = _line_col(text, pos)
    if isinstance(e, UnexpectedCharacters):
        ch = text[pos] if pos < len(text) else ""
        word = ch
        j = pos
        while j < len(text) and (text[j].isalnum() or text[j] == "_"):
            j += 1
        if j > pos:
            word = text[pos:j]
        hint = _hint_for(text, pos)
        expected = _expected_names(e.allowed)
        msg = f"Неочікуваний фрагмент '{word}'"
        if expected:
            msg += f". Очікувалось: {', '.join(expected)}"
        else:
            msg += ": зайвий текст після завершального 'end' програми"
        if hint:
            msg += f". Підказка: {hint}"
        return Diagnostic("E002", msg, line, col, line, col + max(len(word), 1))
    if isinstance(e, UnexpectedToken):
        tok = e.token
        exp = ", ".join(_expected_names(e.expected))
        return Diagnostic("E003", f"Неочікуваний токен '{tok}'. Очікувалось: {exp}", line, col)
    return Diagnostic("E000", str(e), line, col)


def parse(text: str) -> A.Program:
    """Розбирає SIPL-програму. Кидає SiplSyntaxError з діагностикою (рядок/колонка)."""
    if not text.strip():
        raise SiplSyntaxError([Diagnostic("E004", "Порожня програма: очікувалось 'begin ... end'", 1, 1)])
    try:
        tree = _lark().parse(text)
    except UnexpectedInput as e:
        raise SiplSyntaxError([_diagnostic(text, e)]) from None
    return _ToAst().transform(tree)


def check(text: str) -> list[Diagnostic]:
    """Повертає список діагностик (порожній, якщо програма синтаксично коректна)."""
    try:
        parse(text)
    except SiplSyntaxError as e:
        return e.diagnostics
    return []
