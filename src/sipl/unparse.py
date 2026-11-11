"""AST -> текст SIPL (для повідомлень, trace і кроків побудови терму)."""

from __future__ import annotations

from . import ast as A


def unparse(n: A.Node) -> str:
    if isinstance(n, A.Program):
        return f"begin {unparse(n.body)} end"
    if isinstance(n, A.Assign):
        return f"{n.name} := {unparse(n.expr)}"
    if isinstance(n, A.Seq):
        return f"{unparse(n.first)}; {unparse(n.second)}"
    if isinstance(n, A.If):
        return f"if {unparse(n.cond)} then {unparse(n.then)} else {unparse(n.else_)}"
    if isinstance(n, A.While):
        return f"while {unparse(n.cond)} do {unparse(n.body)}"
    if isinstance(n, A.Block):
        return f"begin {unparse(n.body)} end"
    if isinstance(n, A.Skip):
        return "skip"
    if isinstance(n, A.Num):
        return n.text if n.text is not None else str(n.value)
    if isinstance(n, A.Var):
        return n.name
    if isinstance(n, A.BinOp):
        return f"{unparse(n.left)} {n.op} {unparse(n.right)}"
    if isinstance(n, A.ParenA):
        return f"({unparse(n.expr)})"
    if isinstance(n, A.Cmp):
        return f"{unparse(n.left)} {n.op} {unparse(n.right)}"
    if isinstance(n, A.Or):
        return f"{unparse(n.left)} {n.op_text} {unparse(n.right)}"
    if isinstance(n, A.Not):
        sep = " " if n.op_text.isalpha() else ""
        return f"{n.op_text}{sep}{unparse(n.operand)}"
    if isinstance(n, A.ParenB):
        return f"({unparse(n.cond)})"
    raise TypeError(f"Невідомий вузол: {type(n).__name__}")
