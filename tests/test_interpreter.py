"""CORE-03 / CORE-04: виконання, стан, ліміт кроків, trace."""

import pytest

from sipl.interpreter import StepLimitExceeded, UndefinedVariable, run
from sipl.parser import parse


def exec_(src, **state):
    return run(parse(src), state).state


@pytest.mark.parametrize("n,expected", [(1, 4), (2, 13), (3, 40), (5, 364)])
def test_sum_geom3(example, n, expected):
    st = exec_(example("sum_geom3.sipl"), N=n)
    assert st["S"] == expected == (3 ** (n + 1) - 1) // 2
    assert st["N"] == 0 and st["P"] == 3 ** n


@pytest.mark.parametrize("x,y", [(5, 2), (2, 10), (7, 1), (3, 0)])
def test_power(example, x, y):
    assert exec_(example("power.sipl"), X=x, Y=y)["R"] == x ** y


@pytest.mark.parametrize("x,y", [(7, 4), (8, 2), (3, 5), (100, 7)])
def test_division(example, x, y):
    st = exec_(example("division.sipl"), X=x, Y=y)
    assert st["R"] == x // y and st["X"] == x % y


@pytest.mark.parametrize("m,n,g", [(8, 16, 8), (21, 14, 7), (13, 7, 1)])
def test_gcd(example, m, n, g):
    st = exec_(example("gcd.sipl"), M=m, N=n)
    assert st["M"] == st["N"] == g


def test_factorial(example):
    assert exec_(example("factorial.sipl"), N=5)["F"] == 120


@pytest.mark.parametrize("x,y,m", [(-7, 4, 7), (3, -9, 9), (0, 0, 0)])
def test_abs_max_branches(example, x, y, m):
    assert exec_(example("abs_max.sipl"), X=x, Y=y)["M"] == m


def test_skip_is_identity():
    assert exec_("begin skip end", X=1) == {"X": 1}


def test_state_extension_is_monotone(example):
    small = exec_(example("gcd.sipl"), M=8, N=16)
    big = exec_(example("gcd.sipl"), M=8, N=16, L=9)
    assert big["L"] == 9 and {k: big[k] for k in small} == small


def test_undefined_variable_has_position():
    with pytest.raises(UndefinedVariable) as ei:
        exec_("begin\n  X := Y + 1\nend")
    d = ei.value.diagnostics[0]
    assert d.code == "R001" and (d.line, d.column) == (2, 8)


def test_infinite_loop_hits_step_limit():
    with pytest.raises(StepLimitExceeded):
        run(parse("begin while X > 0 do X := X + 1 end"), {"X": 1}, max_steps=500)


def test_trace_events(example):
    res = run(parse(example("power.sipl")), {"X": 5, "Y": 2}, trace=True)
    kinds = [e.kind for e in res.events]
    assert kinds[0] == "before" and kinds[-1] == "finish"
    conds = [e.data["value"] for e in res.events if e.kind == "condition"]
    assert conds == [True, True, False]
    assigns = [(e.data["name"], e.data["new"]) for e in res.events if e.kind == "assign"]
    assert assigns == [("R", 1), ("R", 5), ("Y", 1), ("R", 25), ("Y", 0)]
    assert all("span" in e.to_dict() for e in res.events if e.kind != "finish")
