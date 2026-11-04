from __future__ import annotations

import pytest

from axiom_x.semantic_v2_1 import parse_public_problem
from axiom_x.solver import (
    compare_specifications_by_name,
    enumerate_specification,
    solve_z3,
)
from axiom_x.spec import FormalSpecification


def spec(
    problem_id: str,
    constraints: list[dict[str, object]],
    *,
    names: tuple[str, ...] = ("x", "y", "z"),
    domain: tuple[int, ...] = (-1, 0, 1, 2),
) -> FormalSpecification:
    return FormalSpecification.from_dict(
        {
            "problem_id": problem_id,
            "variables": [{"name": name, "domain": list(domain)} for name in names],
            "constraints": constraints,
            "target": "count_solutions",
            "source": "v3-phase2-verification-test",
            "generation_id": f"v3-{problem_id}",
            "verification_status": "UNVERIFIED",
        }
    )


CONSTRAINT_MATRIX = [
    ("equal", {"kind": "equal", "variable": "x", "value": 0}),
    ("not_equal", {"kind": "not_equal", "variable": "x", "value": 0}),
    ("less_than", {"kind": "less_than", "left": "x", "right": "y"}),
    ("less_equal", {"kind": "less_equal", "left": "x", "right": "y"}),
    ("all_different", {"kind": "all_different", "variables": ["x", "y", "z"]}),
    ("sum_equal", {"kind": "sum_equal", "variables": ["x", "y", "z"], "value": 1}),
    ("sum_at_least", {"kind": "sum_at_least", "variables": ["x", "y", "z"], "value": 1}),
    ("sum_at_most", {"kind": "sum_at_most", "variables": ["x", "y", "z"], "value": 1}),
    (
        "count_equal",
        {"kind": "count_equal", "variables": ["x", "y", "z"], "value": 1, "count": 2},
    ),
    (
        "count_at_least",
        {"kind": "count_at_least", "variables": ["x", "y", "z"], "value": 1, "count": 2},
    ),
    (
        "count_at_most",
        {"kind": "count_at_most", "variables": ["x", "y", "z"], "value": 1, "count": 2},
    ),
    (
        "number_mod",
        {
            "kind": "number_mod",
            "variables": ["x", "y", "z"],
            "base": 4,
            "modulus": 3,
            "remainder": 1,
        },
    ),
]


@pytest.mark.parametrize(("kind", "constraint"), CONSTRAINT_MATRIX, ids=[row[0] for row in CONSTRAINT_MATRIX])
def test_all_dsl_constraints_have_python_z3_solution_set_parity(
    kind: str, constraint: dict[str, object]
) -> None:
    """Property: each supported formal constraint has identical finite semantics in both engines."""
    candidate = spec(kind, [constraint])
    python_result = enumerate_specification(candidate)
    z3_result = solve_z3(candidate)
    assert python_result.status == z3_result.status == "COMPLETE"
    assert python_result.solutions == z3_result.solutions


def test_negative_and_singleton_domain_boundaries_are_complete() -> None:
    """Property: inclusive negative bounds and singleton domains are not dropped at boundaries."""
    candidate = spec(
        "negative-singleton",
        [{"kind": "equal", "variable": "x", "value": -2}],
        names=("x",),
        domain=(-2,),
    )
    expected = frozenset({(-2,)})
    assert enumerate_specification(candidate).solutions == expected
    assert solve_z3(candidate).solutions == expected


def test_contradictory_constraints_return_a_complete_empty_set() -> None:
    """Property: unsatisfiable formal specifications are COMPLETE with zero solutions, not UNKNOWN."""
    candidate = spec(
        "empty",
        [
            {"kind": "equal", "variable": "x", "value": 0},
            {"kind": "equal", "variable": "x", "value": 1},
        ],
        names=("x",),
        domain=(0, 1),
    )
    assert enumerate_specification(candidate).solutions == frozenset()
    assert solve_z3(candidate).solutions == frozenset()


def test_resource_and_timeout_boundaries_are_not_certified() -> None:
    """Property: exhausted enumeration budgets and non-positive solver timeouts stay incomplete."""
    candidate = spec("limits", [], names=("x", "y"), domain=(0, 1, 2))
    assert enumerate_specification(candidate, max_assignments=8).status == "RESOURCE_LIMIT"
    assert solve_z3(candidate, timeout_ms=0).status == "UNKNOWN"
    assert compare_specifications_by_name(candidate, candidate, timeout_ms=0).status == "INCONCLUSIVE"


def test_constraint_and_declaration_reordering_preserve_equivalence() -> None:
    """Metamorphic property: irrelevant ordering changes do not change exact-name solution sets."""
    left = spec(
        "order-left",
        [
            {"kind": "less_equal", "left": "x", "right": "y"},
            {"kind": "not_equal", "variable": "x", "value": 2},
        ],
        names=("x", "y"),
        domain=(0, 1, 2),
    )
    right = FormalSpecification.from_dict(
        {
            **left.to_dict(),
            "problem_id": "order-right",
            "variables": list(reversed(left.to_dict()["variables"])),
            "constraints": list(reversed(left.to_dict()["constraints"])),
            "generation_id": "v3-order-right",
        }
    )
    assert compare_specifications_by_name(left, right).status == "EQUIVALENT"


def test_domain_value_reordering_preserves_equivalence() -> None:
    """Metamorphic property: finite domains are sets even when their serialized order changes."""
    left = spec("domain-order-left", [], names=("x",), domain=(-1, 0, 2))
    right = spec("domain-order-right", [], names=("x",), domain=(2, -1, 0))
    assert compare_specifications_by_name(left, right).status == "EQUIVALENT"


def test_equal_counts_with_different_sets_return_a_witness() -> None:
    """Counterexample property: equal cardinality never substitutes for solution-set equality."""
    left = spec(
        "equal-count-left",
        [{"kind": "equal", "variable": "x", "value": 0}],
        names=("x",),
        domain=(0, 1),
    )
    right = spec(
        "equal-count-right",
        [{"kind": "equal", "variable": "x", "value": 1}],
        names=("x",),
        domain=(0, 1),
    )
    result = compare_specifications_by_name(left, right)
    assert result.status == "DIFFERENT"
    assert result.count_equal is True
    assert result.counterexample in ({"x": 0}, {"x": 1})


def test_domain_mismatch_witness_belongs_to_exactly_one_set() -> None:
    """Counterexample property: a reported witness lies in the formal symmetric difference."""
    left = spec("domain-left", [], names=("x",), domain=(0, 1))
    right = spec("domain-right", [], names=("x",), domain=(0, 1, 2))
    result = compare_specifications_by_name(left, right)
    assert result.status == "DIFFERENT"
    assert result.counterexample == {"x": 2}
    left_set = enumerate_specification(left).solutions
    right_set = enumerate_specification(right).solutions
    assert ((2,) in left_set) != ((2,) in right_set)


SUPPORTED_GRAMMAR_MATRIX = [
    (
        "distinct_sum",
        "Variables a, b, c each range over integers 0 through 3. All variables are distinct. "
        "Their sum is exactly 4. How many assignments satisfy all conditions?",
        {"VARIABLE_DOMAINS", "ALL_DIFFERENT", "SUM_EQUAL"},
    ),
    (
        "distinct_only",
        "Variables a, b, c each range over integers 0 through 3. No two variables have the same "
        "value. How many assignments are possible?",
        {"VARIABLE_DOMAINS", "ALL_DIFFERENT"},
    ),
    (
        "strict_order",
        "Variables x and y each range over integers -1 through 3. Require x to be strictly less "
        "than y. How many ordered assignments are possible?",
        {"VARIABLE_DOMAINS", "STRICT_INEQUALITY"},
    ),
    (
        "sum_bounds",
        "Variables x and y each range over integers 0 through 4. Their sum is at least 2 and at "
        "most 6. How many ordered assignments satisfy both bounds?",
        {"VARIABLE_DOMAINS", "SUM_LOWER_BOUND", "SUM_UPPER_BOUND"},
    ),
    (
        "binary_at_least",
        "Variables b0, b1, b2 are each either 0 or 1. At least 2 of them equal 1. How many "
        "assignments satisfy this?",
        {"BINARY_DOMAINS", "CARDINALITY_AT_LEAST"},
    ),
    (
        "digit_modular",
        "Digits d0, d1, d2 each range from 0 through 9 and form a three-digit base-10 number in "
        "that order. d0 is nonzero. All variables are distinct. The number has remainder 1 modulo "
        "3. How many such numbers exist?",
        {"DIGIT_DOMAINS", "LEADING_NONZERO", "ALL_DIFFERENT", "MODULAR_RESTRICTION"},
    ),
]


@pytest.mark.parametrize(
    ("grammar", "text", "expected_checks"),
    SUPPORTED_GRAMMAR_MATRIX,
    ids=[row[0] for row in SUPPORTED_GRAMMAR_MATRIX],
)
def test_supported_fixed_grammars_require_full_match_and_expected_checks(
    grammar: str, text: str, expected_checks: set[str]
) -> None:
    """Grammar property: each declared fixed form fully parses and records its semantic checks."""
    parsed = parse_public_problem(f"grammar-{grammar}", text)
    assert parsed.status == "COMPLETE"
    assert parsed.specification is not None
    assert set(parsed.triggered_checks) == expected_checks


UNSUPPORTED_TEXTS = [
    "Variables x and y each range over integers 0 through 2. Require x < y or x = y. How many assignments are possible?",
    "Variables x and y each range over integers 0 through 2. Require x != 1. How many assignments are possible?",
    "variables x and y each range over integers 0 through 2. Require x < y. How many assignments are possible?",
    "Variables x and y range over {0, 2, 4}. Require x < y. How many assignments are possible?",
    "Variables x and y each range over integers 0 through 2. Require x < y. Count them.",
    "Variable x ranges over integers 0 through 4. Require x to be prime. How many values are possible?",
]


@pytest.mark.parametrize("text", UNSUPPORTED_TEXTS)
def test_unsupported_or_partial_syntax_is_rejected(text: str) -> None:
    """Rejection property: disjunction, free paraphrase, non-contiguous domains, and unsupported predicates abstain."""
    parsed = parse_public_problem("unsupported", text)
    assert parsed.status == "UNSUPPORTED"
    assert parsed.specification is None


def test_exact_name_mapping_allows_order_but_rejects_renaming() -> None:
    """Mapping property: declaration order is irrelevant, but an unproved alpha-renaming is inconclusive."""
    left = spec(
        "mapping-left",
        [{"kind": "less_than", "left": "x", "right": "y"}],
        names=("x", "y"),
        domain=(0, 1, 2),
    )
    reordered = spec(
        "mapping-reordered",
        [{"kind": "less_than", "left": "x", "right": "y"}],
        names=("y", "x"),
        domain=(0, 1, 2),
    )
    renamed = spec(
        "mapping-renamed",
        [{"kind": "less_than", "left": "u", "right": "v"}],
        names=("u", "v"),
        domain=(0, 1, 2),
    )
    assert compare_specifications_by_name(left, reordered).status == "EQUIVALENT"
    assert compare_specifications_by_name(left, renamed).status == "INCONCLUSIVE"

