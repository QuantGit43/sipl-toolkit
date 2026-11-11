"""Семантичні терми програмної алгебри A_SIPL (лекція 1-2, практична робота 2).

Композиції: S^n (суперпозиція), AS^x (присвоювання), • (послідовне виконання),
IF, WH; базові функції: x⇒ (розіменування), n̄ (константа), id (тотожна).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


@dataclass(frozen=True)
class Const:
    """Функція-константа n̄: State → Int, n̄(st) = n."""
    value: int


@dataclass(frozen=True)
class Deref:
    """Розіменування x⇒: State → Int, x⇒(st) = st(x)."""
    name: str


@dataclass(frozen=True)
class Sup:
    """Суперпозиція S^n(f, g1, ..., gn); f — add/sub/mult/eq/gr/or/neg."""
    op: str
    args: tuple[Term, ...]


@dataclass(frozen=True)
class AssignT:
    """AS^x(fa)."""
    name: str
    fa: Term


@dataclass(frozen=True)
class Comp:
    """Послідовне виконання fs1 • fs2."""
    first: Term
    second: Term


@dataclass(frozen=True)
class IfT:
    fb: Term
    fs1: Term
    fs2: Term


@dataclass(frozen=True)
class WhT:
    fb: Term
    fs: Term


@dataclass(frozen=True)
class IdT:
    """Тотожна функція id."""


@dataclass(frozen=True)
class Pending:
    """Ще не розкритий фрагмент: sem_P/sem_S/sem_A/sem_B(текст). Використовується в ланцюжку перетворень."""
    kind: str
    text: str


Term = Const | Deref | Sup | AssignT | Comp | IfT | WhT | IdT | Pending


def _overline(n: int) -> str:
    s = str(n)
    return "".join(ch + "̄" if ch.isdigit() else ch for ch in s)


def _flatten(t: Term) -> list[Term]:
    if isinstance(t, Comp):
        return _flatten(t.first) + _flatten(t.second)
    return [t]


def to_text(t: Term) -> str:
    """Нотація курсу: AS^S(1̄) • WH(S²(gr, N⇒, 0̄), ...)."""
    if isinstance(t, Const):
        return _overline(t.value)
    if isinstance(t, Deref):
        return f"{t.name}⇒"
    if isinstance(t, Sup):
        n = str(len(t.args)).translate(_SUP)
        return f"S{n}({t.op}, " + ", ".join(to_text(a) for a in t.args) + ")"
    if isinstance(t, AssignT):
        return f"AS^{t.name}({to_text(t.fa)})"
    if isinstance(t, Comp):
        return " • ".join(to_text(x) for x in _flatten(t))
    if isinstance(t, IfT):
        return f"IF({to_text(t.fb)}, {to_text(t.fs1)}, {to_text(t.fs2)})"
    if isinstance(t, WhT):
        return f"WH({to_text(t.fb)}, {to_text(t.fs)})"
    if isinstance(t, IdT):
        return "id"
    if isinstance(t, Pending):
        return f"sem_{t.kind}({t.text})"
    raise TypeError(t)


def _tex_escape(s: str) -> str:
    rep = {"\\": r"\textbackslash{}", "_": r"\_", "{": r"\{", "}": r"\}", "&": r"\&", "%": r"\%",
           "#": r"\#", "$": r"\$", "^": r"\^{}", "~": r"\~{}"}
    return "".join(rep.get(c, c) for c in s)


def to_latex(t: Term) -> str:
    """LaTeX-нотація (для звітів): \\mathit{AS}^{S}(\\overline{1}) \\bullet ..."""
    if isinstance(t, Const):
        return rf"\overline{{{t.value}}}"
    if isinstance(t, Deref):
        return rf"{t.name}\Rightarrow"
    if isinstance(t, Sup):
        return rf"S^{{{len(t.args)}}}(\mathit{{{t.op}}}, " + ", ".join(to_latex(a) for a in t.args) + ")"
    if isinstance(t, AssignT):
        return rf"\mathit{{AS}}^{{{t.name}}}({to_latex(t.fa)})"
    if isinstance(t, Comp):
        return r" \bullet ".join(to_latex(x) for x in _flatten(t))
    if isinstance(t, IfT):
        return rf"\mathit{{IF}}({to_latex(t.fb)}, {to_latex(t.fs1)}, {to_latex(t.fs2)})"
    if isinstance(t, WhT):
        return rf"\mathit{{WH}}({to_latex(t.fb)}, {to_latex(t.fs)})"
    if isinstance(t, IdT):
        return r"\mathit{id}"
    if isinstance(t, Pending):
        return rf"\mathit{{sem\_{t.kind}}}(\texttt{{{_tex_escape(t.text)}}})"
    raise TypeError(t)


def to_dict(t: Term) -> dict[str, Any]:
    if isinstance(t, Const):
        return {"type": "const", "value": t.value}
    if isinstance(t, Deref):
        return {"type": "deref", "name": t.name}
    if isinstance(t, Sup):
        return {"type": "superposition", "arity": len(t.args), "op": t.op, "args": [to_dict(a) for a in t.args]}
    if isinstance(t, AssignT):
        return {"type": "assign", "name": t.name, "fa": to_dict(t.fa)}
    if isinstance(t, Comp):
        return {"type": "seq", "items": [to_dict(x) for x in _flatten(t)]}
    if isinstance(t, IfT):
        return {"type": "if", "fb": to_dict(t.fb), "fs1": to_dict(t.fs1), "fs2": to_dict(t.fs2)}
    if isinstance(t, WhT):
        return {"type": "while", "fb": to_dict(t.fb), "fs": to_dict(t.fs)}
    if isinstance(t, IdT):
        return {"type": "id"}
    if isinstance(t, Pending):
        return {"type": "pending", "kind": t.kind, "text": t.text}
    raise TypeError(t)


def has_pending(t: Term) -> bool:
    if isinstance(t, Pending):
        return True
    if isinstance(t, Sup):
        return any(has_pending(a) for a in t.args)
    if isinstance(t, AssignT):
        return has_pending(t.fa)
    if isinstance(t, Comp):
        return has_pending(t.first) or has_pending(t.second)
    if isinstance(t, IfT):
        return has_pending(t.fb) or has_pending(t.fs1) or has_pending(t.fs2)
    if isinstance(t, WhT):
        return has_pending(t.fb) or has_pending(t.fs)
    return False
