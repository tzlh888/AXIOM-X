from __future__ import annotations

import pytest

from axiom_x.audit import audit
from axiom_x.demo import digit_spec
from axiom_x.experiment import FrozenPrediction, evaluate_frozen, evaluate_strategies, freeze_predictions, grouped_bootstrap_difference
from axiom_x.providers import FixtureProvider, generate_isolated
from axiom_x.solver import compare_specifications, enumerate_specification, solve_z3
from axiom_x.spec import FormalSpecification, SpecificationError


def spec(problem_id: str, constraints: list[dict], *, names=("d0", "d1"), domains=None) -> FormalSpecification:
    domains = domains or [[0, 1, 2], [0, 1, 2]]
    return FormalSpecification.from_dict({
        "problem_id": problem_id,
        "variables": [{"name": name, "domain": domain} for name, domain in zip(names, domains)],
        "constraints": constraints,
        "target": "count_solutions",
        "source": "deterministic-test-fixture",
        "generation_id": f"fixture-{problem_id}",
        "verification_status": "UNVERIFIED",
    })


def test_schema_rejects_unbounded_and_unknown_constraints() -> None:
    raw = digit_spec("bad", [{"kind": "python", "code": "__import__('os')"}], "test")
    with pytest.raises(SpecificationError):
        FormalSpecification.from_dict(raw)
    raw["constraints"] = []
    raw["variables"] = [{"name": "x", "domain": list(range(21))}]
    with pytest.raises(SpecificationError):
        FormalSpecification.from_dict(raw)


def test_leading_zero_omission_is_detected() -> None:
    incomplete = spec("leading-zero", [{"kind": "all_different", "variables": ["d0", "d1"]}])
    faithful = spec("leading-zero", [
        {"kind": "not_equal", "variable": "d0", "value": 0},
        {"kind": "all_different", "variables": ["d0", "d1"]},
    ])
    decision = audit(incomplete, faithful, proposed_answer=6)
    assert decision.decision == "FAIL"
    assert decision.reason_code == "SPECIFICATION_SET_DIFFERENCE"


def test_repetition_error_and_correct_answer() -> None:
    with_repetition = spec("repeat", [])
    without_repetition = spec("repeat", [{"kind": "all_different", "variables": ["d0", "d1"]}])
    assert enumerate_specification(with_repetition).count == 9
    assert enumerate_specification(without_repetition).count == 6
    assert audit(without_repetition, without_repetition, proposed_answer=6).decision == "PASS"


def test_equal_counts_do_not_imply_equal_solution_sets() -> None:
    left = spec("equal-count", [{"kind": "equal", "variable": "d0", "value": 0}])
    right = spec("equal-count", [{"kind": "equal", "variable": "d0", "value": 1}])
    result = compare_specifications(left, right)
    assert result.count_equal is True
    assert result.set_equal is False
    assert result.counterexample is not None


def test_shared_semantic_omission_can_false_certify() -> None:
    shared_bad = spec("shared", [{"kind": "equal", "variable": "d1", "value": 1}], domains=[[0, 1], [1]])
    assert audit(shared_bad, shared_bad, proposed_answer=2).decision == "PASS"
    payload, digest = freeze_predictions([FrozenPrediction("shared", "g1", "dual", "PASS", 2)])
    metrics = evaluate_frozen(payload, digest, {"shared": 1})
    assert metrics["false_certification_rate"] == 1.0


def test_secondary_detects_primary_difference() -> None:
    primary_raw = digit_spec("isolated", [], "primary")
    secondary_raw = digit_spec("isolated", [{"kind": "not_equal", "variable": "d0", "value": 0}], "secondary")
    primary, secondary = generate_isolated(
        "isolated", "public text", FixtureProvider("p", {"isolated": primary_raw}),
        FixtureProvider("s", {"isolated": secondary_raw}),
    )
    assert primary.generation_id != secondary.generation_id
    assert audit(primary.specification, secondary.specification).decision == "FAIL"


def test_timeout_and_unreliable_mapping_are_inconclusive() -> None:
    left = spec("timeout", [])
    assert solve_z3(left, timeout_ms=0).status == "UNKNOWN"
    assert audit(left, left, timeout_ms=0).decision == "INCONCLUSIVE"
    right = spec("mapping", [], names=("x", "y"))
    assert compare_specifications(left, right).status == "INCONCLUSIVE"


def test_zero_denominator_and_always_abstain_are_not_success() -> None:
    payload, digest = freeze_predictions([
        FrozenPrediction("a", "g", "dual", "INCONCLUSIVE", 1),
        FrozenPrediction("b", "g", "dual", "INCONCLUSIVE", 2),
    ])
    metrics = evaluate_frozen(payload, digest, {"a": 1, "b": 2})
    assert metrics["false_certification_rate"] is None
    assert metrics["false_certification_rate_status"] == "UNDEFINED_ZERO_DENOMINATOR"
    assert metrics["decision_coverage"] == 0.0
    assert metrics["abstention_rate"] == 1.0


def test_three_strategies_are_evaluated_only_after_one_freeze() -> None:
    predictions = [
        FrozenPrediction("a", "g", strategy, decision, 2)
        for strategy, decision in (("baseline", "PASS"), ("single", "PASS"), ("dual", "FAIL"))
    ]
    payload, digest = freeze_predictions(predictions)
    results = evaluate_strategies(payload, digest, {"a": 1})
    assert set(results) == {"baseline", "single", "dual"}
    assert results["baseline"]["false_negatives"] == 1
    assert results["dual"]["false_negatives"] == 0


def test_gold_is_absent_until_frozen_evaluation() -> None:
    captured: list[tuple[str, str]] = []

    class Spy:
        def generate(self, problem_id: str, problem_text: str):
            captured.append((problem_id, problem_text))
            return FixtureProvider("spy", {problem_id: digit_spec(problem_id, [], "spy")}).generate(problem_id, problem_text)

    generate_isolated("blind", "only public problem", Spy(), Spy())
    assert captured == [("blind", "only public problem"), ("blind", "only public problem")]
    payload, digest = freeze_predictions([FrozenPrediction("blind", "g", "dual", "PASS", 9)])
    assert "gold" not in payload.casefold()
    with pytest.raises(ValueError, match="changed after freeze"):
        evaluate_frozen(payload + " ", digest, {"blind": 9})


def test_grouped_bootstrap_is_deterministic() -> None:
    rows = [
        {"group_id": "g1", "strategy": "dual", "error": 0.0},
        {"group_id": "g1", "strategy": "single", "error": 1.0},
        {"group_id": "g2", "strategy": "dual", "error": 1.0},
        {"group_id": "g2", "strategy": "single", "error": 1.0},
    ]
    metric = lambda sample: sum(row["error"] for row in sample) / len(sample)
    first = grouped_bootstrap_difference(rows, metric, left="dual", right="single", replicates=100, seed=7)
    assert first == grouped_bootstrap_difference(rows, metric, left="dual", right="single", replicates=100, seed=7)
