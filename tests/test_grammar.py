"""CORE-01: граматика відповідає БНФ курсу; ≥10 позитивних і ≥10 негативних тестів."""

import pytest

from sipl import ast as A
from sipl.diagnostics import SiplSyntaxError
from sipl.parser import check, parse

VALID = [
    "begin skip end",
    "begin X := 1 end",
    "begin X := -1 end",
    "begin X := 1; Y := 2; Z := 3 end",
    "begin R := 1; while Y > 0 do begin R := R * X; Y := Y - 1 end end",
    "begin if M > N then M := M - N else N := N - M end",
    "begin while ¬ M = N do if M > N then M := M - N else N := N - M end",
    "begin if X > 0 ∨ X = 0 then skip else X := 0 - X end",
    "begin if not (X > 0 or X = 0) then skip else skip end",
    "begin X := (1 + 2) * (3 - 4) end",
    "begin if (X + 1) > 2 then skip else skip end",
    "begin begin begin skip end end end",
    "begin X := 3 - -1 end",
    "begin\n  // коментар\n  X := 1 // ще коментар\nend",
    "begin beginner := 1; ending := beginner end",
]

INVALID = [
    "",
    "X := 1",
    "begin X := 1",
    "begin X := 1 end end",
    "begin X = 1 end",
    "begin X := end",
    "begin while X >= 0 do skip end",
    "begin if X > 1 then skip end",
    "begin X := Y < 2 end",
    "begin end := 1 end",
    "begin X := 1; end",
    "begin X := (1 + 2 end",
    "begin while X > 0 skip end",
    "begin X := 7 / 2 end",
    "begin if X then skip else skip end",
]


@pytest.mark.parametrize("src", VALID)
def test_valid_programs_parse(src):
    assert isinstance(parse(src), A.Program)
    assert check(src) == []


@pytest.mark.parametrize("src", INVALID)
def test_invalid_programs_report_position(src):
    diags = check(src)
    assert len(diags) == 1
    d = diags[0]
    assert d.line >= 1 and d.column >= 1
    assert d.message


def test_counts_meet_criteria():
    assert len(VALID) >= 10 and len(INVALID) >= 10


def test_error_position_and_hint():
    with pytest.raises(SiplSyntaxError) as ei:
        parse("begin\n  R := 0;\n  while X >= Y do skip\nend")
    d = ei.value.diagnostics[0]
    assert (d.line, d.column) == (3, 12)
    assert "X > Y ∨ X = Y" in d.message


def test_seq_is_right_associative():
    p = parse("begin A := 1; B := 2; C := 3 end")
    assert isinstance(p.body, A.Seq)
    assert isinstance(p.body.first, A.Assign)
    assert isinstance(p.body.second, A.Seq)


def test_while_binds_tighter_than_seq():
    p = parse("begin while X > 0 do X := X - 1; Y := 1 end")
    assert isinstance(p.body, A.Seq)
    assert isinstance(p.body.first, A.While)


def test_arithmetic_precedence_and_left_assoc():
    p = parse("begin X := 1 - 2 - 3 * 4 end")
    e = p.body.expr
    assert e.op == "-" and e.right.op == "*"
    assert e.left.op == "-"


def test_boolean_precedence():
    p = parse("begin if ¬ X = 1 ∨ Y > 2 then skip else skip end")
    c = p.body.cond
    assert isinstance(c, A.Or)
    assert isinstance(c.left, A.Not) and isinstance(c.left.operand, A.Cmp)


def test_spans_point_into_source():
    src = "begin\n  X := 1;\n  Y := X + 2\nend"
    p = parse(src)
    second = p.body.second
    assert (second.span.line, second.span.column) == (3, 3)
    assert src[second.span.start:second.span.end] == "Y := X + 2"
