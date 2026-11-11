"""SEM-01: семантичний терм у нотації курсу; golden tests на прикладах практикуму."""

import pytest

from sipl.parser import parse
from sipl.semantics import derivation_chain, rule_steps, semantic_term, to_dict, to_latex, to_text

GOLDEN = {
    "power.sipl": "AS^R(1̄) • WH(S²(gr, Y⇒, 0̄), AS^R(S²(mult, R⇒, X⇒)) • AS^Y(S²(sub, Y⇒, 1̄)))",
    "sum_geom3.sipl": "AS^S(1̄) • AS^P(1̄) • WH(S²(gr, N⇒, 0̄), AS^P(S²(mult, P⇒, 3̄)) • "
                      "AS^S(S²(add, S⇒, P⇒)) • AS^N(S²(sub, N⇒, 1̄)))",
    "division.sipl": "AS^R(0̄) • WH(S²(or, S²(gr, X⇒, Y⇒), S²(eq, X⇒, Y⇒)), "
                     "AS^X(S²(sub, X⇒, Y⇒)) • AS^R(S²(add, R⇒, 1̄)))",
    "gcd.sipl": "WH(S¹(neg, S²(eq, M⇒, N⇒)), IF(S²(gr, M⇒, N⇒), AS^M(S²(sub, M⇒, N⇒)), "
                "AS^N(S²(sub, N⇒, M⇒))))",
}


@pytest.mark.parametrize("name,expected", GOLDEN.items())
def test_golden_terms(example, name, expected):
    assert to_text(semantic_term(parse(example(name)))) == expected


def test_skip_gives_id():
    assert to_text(semantic_term(parse("begin skip end"))) == "id"


def test_parentheses_are_semantically_transparent():
    a = semantic_term(parse("begin X := (Y + 1) end"))
    b = semantic_term(parse("begin X := Y + 1 end"))
    assert a == b


def test_seq_grouping_does_not_matter():
    a = semantic_term(parse("begin begin A := 1; B := 2 end; C := 3 end"))
    b = semantic_term(parse("begin A := 1; begin B := 2; C := 3 end end"))
    assert to_text(a) == to_text(b)


def test_chain_starts_with_sem_p_and_ends_with_term(example):
    prog = parse(example("power.sipl"))
    chain = derivation_chain(prog)
    assert chain[0].startswith("sem_P(begin R := 1;")
    assert chain[-1] == GOLDEN["power.sipl"]
    assert all("sem_" in c for c in chain[:-1])


def test_rule_steps_cover_all_rules(example):
    steps = rule_steps(parse(example("power.sipl")))
    assert steps[0].rule == "NS_Prog"
    rules = {s.rule for s in steps}
    assert {"NS_Stm_Seq", "NS_Stm_As", "NS_Stm_Wh", "NS_Stm_BE", "NS_B_gr",
            "NS_A_Mult", "NS_A_Sub", "NS_A_Var", "NS_A_Num"} <= rules


def test_latex_and_json(example):
    t = semantic_term(parse(example("sum_geom3.sipl")))
    tex = to_latex(t)
    assert r"\mathit{AS}^{S}(\overline{1})" in tex and r"\bullet" in tex
    d = to_dict(t)
    assert d["type"] == "seq" and d["items"][2]["type"] == "while"
