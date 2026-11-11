"""Типізоване AST мови SIPL.

Кожен вузол зберігає SourceSpan — позицію у вихідному тексті.
Вузли ParenA/ParenB/Block зберігаються, щоб дерево виводу (VIS-01)
точно відтворювало текст програми; на семантику вони не впливають.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any


@dataclass(frozen=True)
class SourceSpan:
    start: int
    end: int
    line: int
    column: int
    end_line: int
    end_column: int

    def to_dict(self) -> dict[str, int]:
        return {
            "start": self.start,
            "end": self.end,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }


@dataclass
class Node:
    span: SourceSpan | None = field(default=None, kw_only=True, compare=False, repr=False)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"type": type(self).__name__}
        for f in fields(self):
            if f.name == "span":
                continue
            out[f.name] = _value_to_json(getattr(self, f.name))
        out["span"] = self.span.to_dict() if self.span else None
        return out


def _value_to_json(v: Any) -> Any:
    if isinstance(v, Node):
        return v.to_dict()
    return v


@dataclass
class Num(Node):
    value: int
    text: str | None = None


@dataclass
class Var(Node):
    name: str


@dataclass
class BinOp(Node):
    op: str
    left: Aexp
    right: Aexp


@dataclass
class ParenA(Node):
    expr: Aexp


@dataclass
class Cmp(Node):
    op: str
    left: Aexp
    right: Aexp


@dataclass
class Or(Node):
    left: Bexp
    right: Bexp
    op_text: str = "∨"


@dataclass
class Not(Node):
    operand: Bexp
    op_text: str = "¬"


@dataclass
class ParenB(Node):
    cond: Bexp


@dataclass
class Assign(Node):
    name: str
    expr: Aexp


@dataclass
class Seq(Node):
    first: Stm
    second: Stm


@dataclass
class If(Node):
    cond: Bexp
    then: Stm
    else_: Stm


@dataclass
class While(Node):
    cond: Bexp
    body: Stm


@dataclass
class Block(Node):
    body: Stm


@dataclass
class Skip(Node):
    pass


@dataclass
class Program(Node):
    body: Stm


Aexp = Num | Var | BinOp | ParenA
Bexp = Cmp | Or | Not | ParenB
Stm = Assign | Seq | If | While | Block | Skip

__all__ = [
    "SourceSpan", "Node", "Num", "Var", "BinOp", "ParenA", "Cmp", "Or", "Not", "ParenB",
    "Assign", "Seq", "If", "While", "Block", "Skip", "Program", "Aexp", "Bexp", "Stm",
]
