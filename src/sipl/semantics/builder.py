"""Побудова семантичного терму з AST (SEM-01).

Реалізує перетворення sem_P, sem_S, sem_A, sem_B з практикуму (с. 15):
рекурсивно за структурою програми, з журналом застосованих правил
(NS_Prog, NS_Stm_As, ...) та ланцюжком перетворень, як у лекції.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import ast as A
from ..unparse import unparse
from .terms import (
    AssignT,
    Comp,
    Const,
    Deref,
    IdT,
    IfT,
    Pending,
    Sup,
    Term,
    WhT,
    has_pending,
    to_text,
)

_OPS = {"+": ("add", "NS_A_Add"), "-": ("sub", "NS_A_Sub"), "*": ("mult", "NS_A_Mult")}
_CMP = {"=": ("eq", "NS_B_eq"), ">": ("gr", "NS_B_gr")}


@dataclass
class RuleStep:
    rule: str
    lhs: str
    rhs: str

    def format(self) -> str:
        return f"{self.rule}: {self.lhs} = {self.rhs}"

    def to_dict(self) -> dict[str, str]:
        return {"rule": self.rule, "lhs": self.lhs, "rhs": self.rhs}


def _kind(n: A.Node) -> str:
    if isinstance(n, A.Program):
        return "P"
    if isinstance(n, (A.Assign, A.Seq, A.If, A.While, A.Block, A.Skip)):
        return "S"
    if isinstance(n, (A.Num, A.Var, A.BinOp, A.ParenA)):
        return "A"
    return "B"


def _pend(n: A.Node) -> Pending:
    return Pending(_kind(n), unparse(n))


def _build(n: A.Node, depth: float, log: list[RuleStep] | None) -> Term:
    """Будує терм; вузли глибше за depth лишаються нерозкритими (Pending)."""
    if depth <= 0:
        return _pend(n)
    d = depth - 1

    def sub(child: A.Node) -> Term:
        return _build(child, d, log)

    def note(rule: str, rhs: Term) -> None:
        if log is not None:
            log.append(RuleStep(rule, to_text(_pend(n)), to_text(rhs)))

    if isinstance(n, A.Program):
        note("NS_Prog", _pend(n.body))
        return sub(n.body)
    if isinstance(n, A.Assign):
        note("NS_Stm_As", AssignT(n.name, _pend(n.expr)))
        return AssignT(n.name, sub(n.expr))
    if isinstance(n, A.Seq):
        note("NS_Stm_Seq", Comp(_pend(n.first), _pend(n.second)))
        return Comp(sub(n.first), sub(n.second))
    if isinstance(n, A.If):
        note("NS_Stm_If", IfT(_pend(n.cond), _pend(n.then), _pend(n.else_)))
        return IfT(sub(n.cond), sub(n.then), sub(n.else_))
    if isinstance(n, A.While):
        note("NS_Stm_Wh", WhT(_pend(n.cond), _pend(n.body)))
        return WhT(sub(n.cond), sub(n.body))
    if isinstance(n, A.Block):
        note("NS_Stm_BE", _pend(n.body))
        return sub(n.body)
    if isinstance(n, A.Skip):
        note("NS_Stm_skip", IdT())
        return IdT()
    if isinstance(n, A.Num):
        note("NS_A_Num", Const(n.value))
        return Const(n.value)
    if isinstance(n, A.Var):
        note("NS_A_Var", Deref(n.name))
        return Deref(n.name)
    if isinstance(n, A.BinOp):
        op, rule = _OPS[n.op]
        note(rule, Sup(op, (_pend(n.left), _pend(n.right))))
        return Sup(op, (sub(n.left), sub(n.right)))
    if isinstance(n, A.ParenA):
        note("NS_A_Par", _pend(n.expr))
        return sub(n.expr)
    if isinstance(n, A.Cmp):
        op, rule = _CMP[n.op]
        note(rule, Sup(op, (_pend(n.left), _pend(n.right))))
        return Sup(op, (sub(n.left), sub(n.right)))
    if isinstance(n, A.Or):
        note("NS_B_or", Sup("or", (_pend(n.left), _pend(n.right))))
        return Sup("or", (sub(n.left), sub(n.right)))
    if isinstance(n, A.Not):
        note("NS_B_neg", Sup("neg", (_pend(n.operand),)))
        return Sup("neg", (sub(n.operand),))
    if isinstance(n, A.ParenB):
        note("NS_B_Par", _pend(n.cond))
        return sub(n.cond)
    raise TypeError(f"Невідомий вузол: {type(n).__name__}")


def semantic_term(node: A.Node) -> Term:
    """sem_P/sem_S/sem_A/sem_B для довільного вузла AST."""
    return _build(node, float("inf"), None)


def rule_steps(node: A.Node) -> list[RuleStep]:
    """Журнал застосованих правил заміни у порядку обходу (зверху вниз, зліва направо)."""
    log: list[RuleStep] = []
    _build(node, float("inf"), log)
    return log


def derivation_chain(node: A.Node) -> list[str]:
    """Ланцюжок перетворень, як у лекції: sem_P(...) = sem_S(...) = ... = кінцевий терм.

    На кожному кроці розкривається один рівень вкладеності (усі незакриті sem_ одночасно).
    Однакові сусідні рядки зливаються.
    """
    chain: list[str] = []
    depth = 0
    while True:
        t = _build(node, depth, None)
        s = to_text(t)
        if not chain or chain[-1] != s:
            chain.append(s)
        if not has_pending(t):
            return chain
        depth += 1
