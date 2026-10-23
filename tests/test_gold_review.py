from __future__ import annotations

from axiom_x.gold_review import independent_solutions_from_text, render_specification


def test_text_driven_synthetic_fixture_requires_no_bundled_gold() -> None:
    case = {
        "problem_id": "INLINE-1",
        "category": "exactly_count",
        "problem_text": (
            "Variables x, y are each either 0 or 1. "
            "Exactly 1 of them equal 1. How many assignments satisfy this?"
        ),
    }
    names, solutions = independent_solutions_from_text(case)
    assert names == ("x", "y")
    assert solutions == {(0, 1), (1, 0)}


def test_rendered_candidate_is_human_readable() -> None:
    specification = {
        "variables": [{"name": "x", "domain": [0, 1]}],
        "constraints": [{"kind": "not_equal", "variable": "x", "value": 0}],
    }
    rendered = render_specification(specification)
    assert "x ∈ {0, 1}" in rendered
    assert "x ≠ 0" in rendered
