"""Дерево синтаксичного виводу за БНФ курсу (VIS-01, практична робота 1).

Будується з реального AST: кожен нетермінал (<програма>, <оператор>, <вираз>, ...)
позначений правилом БНФ (NP1, NS1–NS6, NA1–NA6, NB1–NB5) і SourceSpan фрагмента.
Листки (термінали) нумеруються зліва направо; обхід листків має відтворювати
текст програми — це і є перевірка синтаксичної коректності з практикуму.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .. import ast as A


@dataclass
class PTNode:
    label: str
    rule: str | None = None
    children: list[PTNode] = field(default_factory=list)
    span: A.SourceSpan | None = None
    index: int | None = None

    @property
    def is_leaf(self) -> bool:
        return not self.children

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"label": self.label}
        if self.is_leaf:
            d["terminal"] = True
            d["index"] = self.index
        else:
            d["rule"] = self.rule
            d["children"] = [c.to_dict() for c in self.children]
        d["span"] = self.span.to_dict() if self.span else None
        return d


def _t(text: str, span: A.SourceSpan | None = None) -> PTNode:
    return PTNode(text, span=span)


def _nt(label: str, rule: str, children: list[PTNode], node: A.Node) -> PTNode:
    return PTNode(label, rule, children, node.span)


STM, EXP, COND = "<оператор>", "<вираз>", "<умова>"


def _var(name: str, node: A.Node) -> PTNode:
    return PTNode("<змінна>", "NV", [_t(name, node.span)], node.span)


def _build(n: A.Node) -> PTNode:
    if isinstance(n, A.Program):
        return _nt("<програма>", "NP1", [_t("begin"), _build(n.body), _t("end")], n)
    if isinstance(n, A.Assign):
        return _nt(STM, "NS1", [_var(n.name, n), _t(":="), _build(n.expr)], n)
    if isinstance(n, A.Seq):
        return _nt(STM, "NS2", [_build(n.first), _t(";"), _build(n.second)], n)
    if isinstance(n, A.If):
        return _nt(STM, "NS3", [_t("if"), _build(n.cond), _t("then"), _build(n.then),
                                _t("else"), _build(n.else_)], n)
    if isinstance(n, A.While):
        return _nt(STM, "NS4", [_t("while"), _build(n.cond), _t("do"), _build(n.body)], n)
    if isinstance(n, A.Block):
        return _nt(STM, "NS5", [_t("begin"), _build(n.body), _t("end")], n)
    if isinstance(n, A.Skip):
        return _nt(STM, "NS6", [_t("skip", n.span)], n)
    if isinstance(n, A.Num):
        text = n.text if n.text is not None else str(n.value)
        return _nt(EXP, "NA1", [PTNode("<число>", "NN", [_t(text, n.span)], n.span)], n)
    if isinstance(n, A.Var):
        return _nt(EXP, "NA2", [_var(n.name, n)], n)
    if isinstance(n, A.BinOp):
        rule = {"+": "NA3", "-": "NA4", "*": "NA5"}[n.op]
        return _nt(EXP, rule, [_build(n.left), _t(n.op), _build(n.right)], n)
    if isinstance(n, A.ParenA):
        return _nt(EXP, "NA6", [_t("("), _build(n.expr), _t(")")], n)
    if isinstance(n, A.Cmp):
        rule = {"=": "NB1", ">": "NB2"}[n.op]
        return _nt(COND, rule, [_build(n.left), _t(n.op), _build(n.right)], n)
    if isinstance(n, A.Or):
        return _nt(COND, "NB3", [_build(n.left), _t(n.op_text), _build(n.right)], n)
    if isinstance(n, A.Not):
        return _nt(COND, "NB4", [_t(n.op_text), _build(n.operand)], n)
    if isinstance(n, A.ParenB):
        return _nt(COND, "NB5", [_t("("), _build(n.cond), _t(")")], n)
    raise TypeError(f"Невідомий вузол: {type(n).__name__}")


def leaves(root: PTNode) -> list[PTNode]:
    out: list[PTNode] = []

    def go(p: PTNode) -> None:
        if p.is_leaf:
            out.append(p)
        else:
            for c in p.children:
                go(c)

    go(root)
    return out


def build_parse_tree(program: A.Program) -> PTNode:
    root = _build(program)
    for i, leaf in enumerate(leaves(root), 1):
        leaf.index = i
    return root


def leaf_yield(root: PTNode) -> list[str]:
    return [lf.label for lf in leaves(root)]


def numbered_yield(root: PTNode) -> str:
    """Рядок у форматі практикуму: '1 begin 2 R 3 := 4 1 ...'."""
    return " ".join(f"{lf.index} {lf.label}" for lf in leaves(root))


def _normalize(source: str) -> str:
    source = re.sub(r"//[^\n]*", "", source)
    return re.sub(r"\s+", "", source)


def check_yield(root: PTNode, source: str) -> bool:
    """Перевірка синтаксичної коректності: листки зліва направо = текст програми."""
    return "".join(leaf_yield(root)) == _normalize(source)


def render_text(root: PTNode) -> str:
    lines: list[str] = []

    def label(p: PTNode) -> str:
        if p.is_leaf:
            return f"({p.index}) {p.label}"
        return f"{p.label} [{p.rule}]"

    def go(p: PTNode, prefix: str, last: bool, top: bool) -> None:
        if top:
            lines.append(label(p))
            child_prefix = ""
        else:
            lines.append(prefix + ("└─ " if last else "├─ ") + label(p))
            child_prefix = prefix + ("   " if last else "│  ")
        for i, c in enumerate(p.children):
            go(c, child_prefix, i == len(p.children) - 1, False)

    go(root, "", True, True)
    return "\n".join(lines)


def _dot_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def render_dot(root: PTNode) -> str:
    out = ["digraph ParseTree {", '  node [shape=plaintext, fontname="Helvetica"];', "  edge [arrowsize=0.6];"]
    ids: dict[int, str] = {}

    def go(p: PTNode) -> str:
        nid = f"n{len(ids)}"
        ids[id(p)] = nid
        if p.is_leaf:
            lab = f'<<font color="red" point-size="9">{p.index}</font> {_html(p.label)}>'
            out.append(f"  {nid} [label={lab}];")
        else:
            tip = f"{p.rule}"
            if p.span:
                tip += f" @ {p.span.line}:{p.span.column}-{p.span.end_line}:{p.span.end_column}"
            out.append(f'  {nid} [label="{_dot_escape(p.label)}", tooltip="{_dot_escape(tip)}"];')
        for c in p.children:
            cid = go(c)
            out.append(f"  {nid} -> {cid};")
        return nid

    go(root)
    out.append("}")
    return "\n".join(out)


def _html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(root: PTNode) -> str:
    """Власна розкладка дерева (без залежності від graphviz), стиль як на рис. 1 практикуму."""
    cw, gap, dy, top = 8.2, 12.0, 62.0, 40.0
    widths: dict[int, float] = {}

    def tw(s: str) -> float:
        return len(s) * cw

    def width(p: PTNode) -> float:
        own = tw(p.label) + gap
        w = own if p.is_leaf else max(own, sum(width(c) for c in p.children))
        widths[id(p)] = w
        return w

    width(root)
    nodes: list[tuple[PTNode, float, float]] = []
    edges: list[tuple[float, float, float, float]] = []

    def place(p: PTNode, x0: float, depth: int) -> tuple[float, float]:
        w = widths[id(p)]
        cx, y = x0 + w / 2, top + depth * dy
        nodes.append((p, cx, y))
        if p.children:
            s = sum(widths[id(c)] for c in p.children)
            x = x0 + (w - s) / 2
            for c in p.children:
                ccx, cy = place(c, x, depth + 1)
                edges.append((cx, y, ccx, cy))
                x += widths[id(c)]
        return cx, y

    place(root, 20, 0)
    W = widths[id(root)] + 40
    H = max(y for _, _, y in nodes) + 30
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" '
        f'height="{H:.0f}" font-family="DejaVu Sans, Arial, sans-serif">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="black"/></marker></defs>',
    ]
    for x1, y1, x2, y2 in edges:
        out.append(f'<line x1="{x1:.1f}" y1="{y1 + 6:.1f}" x2="{x2:.1f}" y2="{y2 - 16:.1f}" '
                   f'stroke="black" stroke-width="1.2" marker-end="url(#a)"/>')
    for p, x, y in nodes:
        title = ""
        if p.span:
            title = f"<title>{p.rule or 'термінал'} {p.span.line}:{p.span.column}-{p.span.end_line}:{p.span.end_column}</title>"
        out.append(f'<g>{title}<text x="{x:.1f}" y="{y:.1f}" font-size="14" text-anchor="middle">'
                   f"{_html(p.label)}</text></g>")
        if p.is_leaf:
            out.append(f'<text x="{x - tw(p.label) / 2 - 2:.1f}" y="{y - 12:.1f}" font-size="11" '
                       f'fill="#d00" text-anchor="end">{p.index}</text>')
    out.append("</svg>")
    return "\n".join(out)
