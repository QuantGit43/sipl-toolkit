"""Інтерпретатор SIPL (CORE-03) з подієвою моделлю виконання (CORE-04).

Стан — часткове відображення Var -> Int (State у лекції 1-2).
Нескінченні цикли контролюються лімітом кроків: якщо його перевищено,
результат вважається невизначеним (fs(st)↑).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .. import ast as A
from ..diagnostics import Diagnostic, SiplError
from ..unparse import unparse

DEFAULT_MAX_STEPS = 100_000


class SiplRuntimeError(SiplError):
    pass


class UndefinedVariable(SiplRuntimeError):
    pass


class StepLimitExceeded(SiplRuntimeError):
    """Обчислення не завершилось за відведену кількість кроків (результат ↑)."""


@dataclass
class Event:
    kind: str
    step: int
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"event": self.kind, "step": self.step, **self.data}

    def format(self) -> str:
        d = self.data
        if self.kind == "before":
            return f"[{self.step}] ▶ {d['node']}: {d['text']}"
        if self.kind == "after":
            return f"[{self.step}] ◀ {d['node']}"
        if self.kind == "assign":
            old = "↑" if d["old"] is None else d["old"]
            return f"[{self.step}]   {d['name']}: {old} → {d['new']}"
        if self.kind == "condition":
            return f"[{self.step}]   {d['construct']} умова {d['text']} = {str(d['value']).lower()}"
        if self.kind == "finish":
            return f"[{self.step}] ■ завершено: {format_state(d['state'])}"
        return f"[{self.step}] {self.kind} {d}"


@dataclass
class RunResult:
    state: dict[str, int]
    steps: int
    events: list[Event]


def format_state(st: dict[str, int]) -> str:
    return "[" + ", ".join(f"{k} ↦ {v}" for k, v in st.items()) + "]"


class Interpreter:
    def __init__(
        self,
        max_steps: int = DEFAULT_MAX_STEPS,
        record_trace: bool = False,
        on_event: Callable[[Event], None] | None = None,
    ):
        self.max_steps = max_steps
        self.record_trace = record_trace
        self.on_event = on_event
        self.events: list[Event] = []
        self.steps = 0

    def _emit(self, kind: str, **data: Any) -> None:
        if not (self.record_trace or self.on_event):
            return
        ev = Event(kind, self.steps, data)
        if self.record_trace:
            self.events.append(ev)
        if self.on_event:
            self.on_event(ev)

    def _tick(self, node: A.Node) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise StepLimitExceeded([Diagnostic.at_span(
                "R002",
                f"Перевищено ліміт у {self.max_steps} кроків: ймовірно, цикл не завершується "
                f"(результат невизначений, fs(st)↑)",
                node.span,
            )])

    def run(self, program: A.Program, state: dict[str, int] | None = None) -> RunResult:
        st = dict(state or {})
        self.events, self.steps = [], 0
        self.exec(program.body, st)
        self._emit("finish", state=dict(st))
        return RunResult(st, self.steps, self.events)

    def exec(self, s: A.Stm, st: dict[str, int]) -> None:
        if isinstance(s, A.Seq):
            self.exec(s.first, st)
            self.exec(s.second, st)
            return
        if isinstance(s, A.Block):
            self.exec(s.body, st)
            return
        self._tick(s)
        self._emit("before", node=type(s).__name__, text=unparse(s), span=_span(s))
        if isinstance(s, A.Assign):
            old = st.get(s.name)
            new = self.eval_a(s.expr, st)
            st[s.name] = new
            self._emit("assign", name=s.name, old=old, new=new, span=_span(s))
        elif isinstance(s, A.If):
            c = self.eval_b(s.cond, st)
            self._emit("condition", construct="if", text=unparse(s.cond), value=c, span=_span(s.cond))
            self.exec(s.then if c else s.else_, st)
        elif isinstance(s, A.While):
            while True:
                c = self.eval_b(s.cond, st)
                self._emit("condition", construct="while", text=unparse(s.cond), value=c, span=_span(s.cond))
                if not c:
                    break
                self.exec(s.body, st)
                self._tick(s)
        elif isinstance(s, A.Skip):
            pass
        else:
            raise TypeError(f"Невідомий оператор: {type(s).__name__}")
        self._emit("after", node=type(s).__name__, span=_span(s))

    def eval_a(self, a: A.Aexp, st: dict[str, int]) -> int:
        if isinstance(a, A.Num):
            return a.value
        if isinstance(a, A.Var):
            if a.name not in st:
                raise UndefinedVariable([Diagnostic.at_span(
                    "R001",
                    f"Змінна '{a.name}' не має значення у поточному стані ({a.name}⇒(st) невизначене). "
                    f"Задайте її, напр.: --set {a.name}=5",
                    a.span,
                )])
            return st[a.name]
        if isinstance(a, A.ParenA):
            return self.eval_a(a.expr, st)
        if isinstance(a, A.BinOp):
            x, y = self.eval_a(a.left, st), self.eval_a(a.right, st)
            if a.op == "+":
                return x + y
            if a.op == "-":
                return x - y
            if a.op == "*":
                return x * y
        raise TypeError(f"Невідомий вираз: {type(a).__name__}")

    def eval_b(self, b: A.Bexp, st: dict[str, int]) -> bool:
        if isinstance(b, A.Cmp):
            x, y = self.eval_a(b.left, st), self.eval_a(b.right, st)
            return x == y if b.op == "=" else x > y
        if isinstance(b, A.Or):
            left = self.eval_b(b.left, st)
            right = self.eval_b(b.right, st)
            return left or right
        if isinstance(b, A.Not):
            return not self.eval_b(b.operand, st)
        if isinstance(b, A.ParenB):
            return self.eval_b(b.cond, st)
        raise TypeError(f"Невідома умова: {type(b).__name__}")


def _span(n: A.Node) -> dict[str, int] | None:
    return n.span.to_dict() if n.span else None


def run(program: A.Program, state: dict[str, int] | None = None, *,
        max_steps: int = DEFAULT_MAX_STEPS, trace: bool = False) -> RunResult:
    return Interpreter(max_steps=max_steps, record_trace=trace).run(program, state)
