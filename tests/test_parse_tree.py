"""VIS-01: дерево виводу за БНФ курсу, нумерація листків, прив'язка до тексту, експорти."""

import json

import pytest

from sipl.parser import parse
from sipl.visualization import (
    build_parse_tree,
    check_yield,
    leaf_yield,
    numbered_yield,
    render_dot,
    render_svg,
    render_text,
)


def test_power_matches_textbook_figure(example):
    tree = build_parse_tree(parse(example("power.sipl")))
    assert numbered_yield(tree) == (
        "1 begin 2 R 3 := 4 1 5 ; 6 while 7 Y 8 > 9 0 10 do 11 begin 12 R 13 := 14 R "
        "15 * 16 X 17 ; 18 Y 19 := 20 Y 21 - 22 1 23 end 24 end"
    )


def test_variant19_has_34_leaves(example):
    tree = build_parse_tree(parse(example("sum_geom3.sipl")))
    assert len(leaf_yield(tree)) == 34


@pytest.mark.parametrize("name", ["power.sipl", "sum_geom3.sipl", "division.sipl", "gcd.sipl",
                                  "factorial.sipl", "abs_max.sipl"])
def test_yield_reproduces_source(example, name):
    src = example(name)
    assert check_yield(build_parse_tree(parse(src)), src)


def test_root_and_rules(example):
    tree = build_parse_tree(parse(example("power.sipl")))
    assert tree.label == "<програма>" and tree.rule == "NP1"
    seq = tree.children[1]
    assert seq.label == "<оператор>" and seq.rule == "NS2"


def test_nodes_linked_to_source(example):
    src = example("power.sipl")
    tree = build_parse_tree(parse(src))
    loop = tree.children[1].children[2]
    assert loop.rule == "NS4"
    assert src[loop.span.start:loop.span.end].startswith("while Y > 0 do")


def test_exports(example):
    tree = build_parse_tree(parse(example("gcd.sipl")))
    assert "<програма> [NP1]" in render_text(tree)
    dot = render_dot(tree)
    assert dot.startswith("digraph") and "->" in dot
    svg = render_svg(tree)
    assert svg.startswith("<svg") and "&lt;умова&gt;" in svg
    d = tree.to_dict()
    json.dumps(d, ensure_ascii=False)
    assert d["rule"] == "NP1" and d["span"]["line"] >= 1
