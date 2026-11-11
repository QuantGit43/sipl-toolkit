"""CORE-05: інтеграційні тести CLI, коди завершення і стабільний JSON-конверт."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import EXAMPLES

from sipl.cli import main

ENVELOPE_KEYS = {"schema_version", "tool", "version", "command", "ok", "result", "diagnostics"}


def run_cli(capsys, *args):
    code = main(list(args))
    out = capsys.readouterr()
    return code, out.out, out.err


def ex(name):
    return str(EXAMPLES / name)


def test_run_text(capsys):
    code, out, _ = run_cli(capsys, "run", ex("sum_geom3.sipl"), "-s", "N=3")
    assert code == 0 and "S ↦ 40" in out


@pytest.mark.parametrize("cmd,extra", [
    ("parse", []), ("check", []), ("run", ["-s", "N=2"]), ("trace", ["-s", "N=2"]),
    ("term", ["--chain", "--steps"]), ("tree", []),
])
def test_json_envelope_is_stable(capsys, cmd, extra):
    code, out, _ = run_cli(capsys, cmd, ex("sum_geom3.sipl"), "--json", *extra)
    data = json.loads(out)
    assert code == 0 and set(data) == ENVELOPE_KEYS
    assert data["schema_version"] == 1 and data["ok"] is True and data["command"] == cmd


def test_run_json_result(capsys):
    _, out, _ = run_cli(capsys, "run", ex("power.sipl"), "-s", "X=5", "-s", "Y=2", "--json")
    res = json.loads(out)["result"]
    assert res["defined"] is True and res["final_state"]["R"] == 25


def test_trace_json_has_events(capsys):
    _, out, _ = run_cli(capsys, "trace", ex("power.sipl"), "-s", "X=5", "-s", "Y=2", "--json")
    events = json.loads(out)["result"]["events"]
    assert events[-1]["event"] == "finish"


def test_term_json(capsys):
    _, out, _ = run_cli(capsys, "term", ex("power.sipl"), "--json")
    res = json.loads(out)["result"]
    assert res["term"].startswith("AS^R(1̄)") and "latex" in res and res["tree"]["type"] == "seq"


def test_syntax_error_exit_code_and_json(capsys):
    code, out, _ = run_cli(capsys, "check", ex("errors/ge_operator.sipl"), "--json")
    data = json.loads(out)
    assert code == 1 and data["ok"] is False
    d = data["diagnostics"][0]
    assert d["line"] == 3 and d["column"] == 14 and d["code"] == "E002"


def test_syntax_error_text_has_location(capsys):
    code, _, err = run_cli(capsys, "check", ex("errors/missing_end.sipl"))
    assert code == 1 and "missing_end.sipl:" in err and "error[" in err


def test_runtime_error_exit_code(capsys):
    code, _, err = run_cli(capsys, "run", ex("sum_geom3.sipl"))
    assert code == 3 and "R001" in err


def test_divergence_exit_code(capsys):
    code, out, _ = run_cli(capsys, "run", ex("errors/infinite_loop.sipl"), "-s", "X=1",
                           "--max-steps", "300", "--json")
    data = json.loads(out)
    assert code == 4 and data["result"]["defined"] is False


def test_bad_state_argument(capsys):
    code, _, _ = run_cli(capsys, "run", ex("power.sipl"), "-s", "X5")
    assert code == 2


def test_missing_file(capsys):
    code, _, _ = run_cli(capsys, "check", "no_such_file.sipl")
    assert code == 5


def test_tree_formats(capsys, tmp_path):
    for fmt in ("dot", "svg", "json"):
        target = tmp_path / f"t.{fmt}"
        code, _, _ = run_cli(capsys, "tree", ex("power.sipl"), "--format", fmt, "-o", str(target))
        assert code == 0 and target.read_text(encoding="utf-8")


def test_stdin_and_module_entrypoint():
    src_dir = str(Path(__file__).resolve().parents[1] / "src")
    env = {**os.environ, "PYTHONPATH": src_dir + os.pathsep + os.environ.get("PYTHONPATH", "")}
    p = subprocess.run([sys.executable, "-m", "sipl.cli", "check", "-"], input="begin skip end",
                       capture_output=True, text=True, encoding="utf-8", env=env)
    assert p.returncode == 0 and "OK" in p.stdout
