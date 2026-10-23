from __future__ import annotations

from axiom_x.providers import FixtureProvider
from axiom_x.solver import enumerate_specification, solve_z3
from axiom_x.spec import FormalSpecification
from axiom_x.v2 import predict_cases


def make_spec(problem_id: str, constraints: list[dict]) -> dict:
    return {"problem_id": problem_id,
            "variables": [{"name": "x", "domain": [0, 1, 2]},
                          {"name": "y", "domain": [0, 1, 2]}],
            "constraints": constraints, "target": "count_solutions", "source": "test",
            "generation_id": "replaced", "verification_status": "UNVERIFIED"}


def test_extended_bounds_match_python_and_z3() -> None:
    parsed = FormalSpecification.from_dict(make_spec("bounds", [
        {"kind": "sum_at_least", "variables": ["x", "y"], "value": 2},
        {"kind": "sum_at_most", "variables": ["x", "y"], "value": 3},
        {"kind": "count_at_most", "variables": ["x", "y"], "value": 2, "count": 1},
    ]))
    assert enumerate_specification(parsed).solutions == solve_z3(parsed).solutions


def test_four_groups_share_one_primary_generation() -> None:
    case = {"problem_id": "P", "problem_text": "Variables x and y range over 0 through 2.",
            "group_id": "P", "category": "test"}
    fixture = make_spec("P", [])
    row = predict_cases([case], FixtureProvider("p", {"P": fixture}),
                        FixtureProvider("s", {"P": fixture}))[0]
    assert set(row["strategies"]) == {"B0", "B1", "B2", "B3"}
    assert row["answer"] == 9
    assert row["strategies"]["B2"]["decision"] == "ACCEPT"

