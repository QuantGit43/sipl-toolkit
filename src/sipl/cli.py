"""Командний рядок SIPL (CORE-05).

Команди: parse, check, run, trace, term, tree.
Кожна команда має --json: стабільний конверт зі schema_version (див. docs/json-format.md).

Коди завершення:
  0 — успіх
  1 — синтаксична помилка
  2 — неправильні аргументи (argparse)
  3 — помилка виконання (напр. змінна без значення)
  4 — результат невизначений: перевищено ліміт кроків (ймовірно, нескінченний цикл)
  5 — помилка вводу/виводу (файл не знайдено тощо)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .diagnostics import Diagnostic, SiplError, SiplSyntaxError
from .interpreter import DEFAULT_MAX_STEPS, Interpreter, StepLimitExceeded, format_state
from .parser import parse
from .semantics import derivation_chain, rule_steps, semantic_term, to_dict, to_latex, to_text
from .unparse import unparse
from .visualization import (
    build_parse_tree,
    check_yield,
    numbered_yield,
    render_dot,
    render_svg,
    render_text,
)

SCHEMA_VERSION = 1
EXIT_OK, EXIT_SYNTAX, EXIT_USAGE, EXIT_RUNTIME, EXIT_DIVERGE, EXIT_IO = 0, 1, 2, 3, 4, 5


class _Out:
    def __init__(self, args: argparse.Namespace):
        self.json = getattr(args, "json", False)
        self.command = args.command
        self.file = getattr(args, "file", "-")

    def emit(self, ok: bool, result: Any = None, diagnostics: list[Diagnostic] | None = None,
             text: str | None = None) -> None:
        diags = diagnostics or []
        if self.json:
            env = {
                "schema_version": SCHEMA_VERSION,
                "tool": "sipl",
                "version": __version__,
                "command": self.command,
                "ok": ok,
                "result": result,
                "diagnostics": [d.to_dict() for d in diags],
            }
            print(json.dumps(env, ensure_ascii=False, indent=2))
            return
        if text:
            print(text)
        name = "<stdin>" if self.file == "-" else self.file
        for d in diags:
            print(d.format(name), file=sys.stderr)


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _parse_state(items: list[str] | None) -> dict[str, int]:
    st: dict[str, int] = {}
    for it in items or []:
        if "=" not in it:
            raise ValueError(f"Очікувалось NAME=VALUE, отримано '{it}'")
        k, v = it.split("=", 1)
        k = k.strip()
        if not k.isidentifier():
            raise ValueError(f"Некоректне ім'я змінної '{k}'")
        st[k] = int(v)
    return st


def cmd_parse(args, out: _Out, src: str) -> int:
    prog = parse(src)
    out.emit(True, prog.to_dict(), text=json.dumps(prog.to_dict(), ensure_ascii=False, indent=2))
    return EXIT_OK


def cmd_check(args, out: _Out, src: str) -> int:
    prog = parse(src)
    out.emit(True, {"valid": True, "normalized": unparse(prog)}, text="OK: програма синтаксично коректна")
    return EXIT_OK


def _run(args, out: _Out, src: str, trace: bool) -> int:
    prog = parse(src)
    st = _parse_state(args.set)
    lines: list[str] = []
    interp = Interpreter(max_steps=args.max_steps, record_trace=trace and out.json,
                         on_event=(lambda e: lines.append(e.format())) if trace and not out.json else None)
    initial = dict(st)
    try:
        res = interp.run(prog, st)
    except StepLimitExceeded as e:
        result = {"defined": False, "initial_state": initial, "steps": interp.steps}
        if trace and out.json:
            result["events"] = [ev.to_dict() for ev in interp.events]
        text = "\n".join(lines + ["Результат невизначений (↑)"]) if not out.json else None
        out.emit(False, result, e.diagnostics, text=text)
        return EXIT_DIVERGE
    result = {"defined": True, "initial_state": initial, "final_state": res.state, "steps": res.steps}
    if trace and out.json:
        result["events"] = [ev.to_dict() for ev in res.events]
    if out.json:
        out.emit(True, result)
    else:
        body = lines if trace else []
        out.emit(True, text="\n".join(body + [f"Кінцевий стан: {format_state(res.state)}"]))
    return EXIT_OK


def cmd_run(args, out: _Out, src: str) -> int:
    return _run(args, out, src, trace=False)


def cmd_trace(args, out: _Out, src: str) -> int:
    return _run(args, out, src, trace=True)


def cmd_term(args, out: _Out, src: str) -> int:
    prog = parse(src)
    term = semantic_term(prog)
    render = to_latex if args.format == "latex" else to_text
    chain = derivation_chain(prog) if args.chain else None
    steps = rule_steps(prog) if args.steps else None
    if out.json:
        res: dict[str, Any] = {"term": to_text(term), "latex": to_latex(term), "tree": to_dict(term)}
        if chain is not None:
            res["chain"] = chain
        if steps is not None:
            res["steps"] = [s.to_dict() for s in steps]
        out.emit(True, res)
        return EXIT_OK
    parts: list[str] = []
    if steps is not None:
        parts.append("Застосовані правила:")
        parts += [f"  {s.format()}" for s in steps]
        parts.append("")
    if chain is not None:
        if args.format == "latex":
            parts.append("Ланцюжок у LaTeX доступний лише як кінцевий терм; показую текстом:")
        parts.append(chain[0] + " =")
        parts += [f"= {c}" + (" =" if i < len(chain) - 2 else "") for i, c in enumerate(chain[1:])]
        parts.append("")
        parts.append("Семантичний терм:")
    parts.append(render(term))
    out.emit(True, text="\n".join(parts))
    return EXIT_OK


def cmd_tree(args, out: _Out, src: str) -> int:
    prog = parse(src)
    tree = build_parse_tree(prog)
    ok = check_yield(tree, src)
    diags = [] if ok else [Diagnostic("W001", "Обхід листків не збігся з текстом програми", 1, 1, severity="warning")]
    fmt = "json" if out.json else args.format
    if fmt == "json":
        payload = {"tree": tree.to_dict(), "yield": numbered_yield(tree), "yield_matches_source": ok}
        if out.json:
            out.emit(ok, payload, diags)
        else:
            _write(args, json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK
    if fmt == "dot":
        _write(args, render_dot(tree))
    elif fmt == "svg":
        _write(args, render_svg(tree))
    else:
        verdict = ("Обхід збігається з текстом програми, отже програма синтаксично коректна."
                   if ok else "УВАГА: обхід не збігся з текстом програми.")
        _write(args, render_text(tree) + "\n\nОбхід листків зліва направо:\n" + numbered_yield(tree)
               + "\n" + verdict)
    return EXIT_OK


def _write(args, content: str) -> None:
    if getattr(args, "output", None):
        Path(args.output).write_text(content, encoding="utf-8")
        print(f"Записано: {args.output}", file=sys.stderr)
    else:
        print(content)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sipl", description="SIPL Language Toolkit")
    p.add_argument("--version", action="version", version=f"sipl {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def add(name: str, help_: str) -> argparse.ArgumentParser:
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("file", help="файл .sipl або '-' для stdin")
        sp.add_argument("--json", action="store_true", help="структурований JSON-вивід")
        return sp

    add("parse", "розібрати програму і вивести AST")
    add("check", "перевірити синтаксис")
    for name, help_ in (("run", "виконати програму"), ("trace", "виконати з покроковим trace")):
        sp = add(name, help_)
        sp.add_argument("-s", "--set", action="append", metavar="NAME=VALUE", help="початковий стан, напр. -s N=3")
        sp.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS, help="ліміт кроків (контроль нескінченних циклів)")
    sp = add("term", "побудувати семантичний терм у нотації курсу")
    sp.add_argument("--format", choices=["text", "latex"], default="text")
    sp.add_argument("--chain", action="store_true", help="показати ланцюжок перетворень, як у лекції")
    sp.add_argument("--steps", action="store_true", help="показати застосовані правила NS_*")
    sp = add("tree", "побудувати дерево синтаксичного виводу")
    sp.add_argument("--format", choices=["text", "json", "dot", "svg"], default="text")
    sp.add_argument("-o", "--output", help="записати результат у файл")
    return p


COMMANDS = {"parse": cmd_parse, "check": cmd_check, "run": cmd_run, "trace": cmd_trace,
            "term": cmd_term, "tree": cmd_tree}


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    args = build_arg_parser().parse_args(argv)
    out = _Out(args)
    try:
        src = _read(args.file)
    except OSError as e:
        out.emit(False, None, [Diagnostic("IO01", f"Не вдалося прочитати файл: {e}", 1, 1)])
        return EXIT_IO
    try:
        return COMMANDS[args.command](args, out, src)
    except ValueError as e:
        out.emit(False, None, [Diagnostic("U001", str(e), 1, 1)])
        return EXIT_USAGE
    except SiplSyntaxError as e:
        out.emit(False, None, e.diagnostics)
        return EXIT_SYNTAX
    except SiplError as e:
        out.emit(False, None, e.diagnostics)
        return EXIT_RUNTIME


if __name__ == "__main__":
    raise SystemExit(main())
