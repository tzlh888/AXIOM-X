from research_v3.controlled_development import cases
from axiom_x.evaluation_v2 import _label
from axiom_x.semantic_v2_1 import parse_public_problem
from axiom_x.solver import compare_specifications_by_name, enumerate_specification, solve_z3
from axiom_x.spec import FormalSpecification


def test_controlled_dataset_is_frozen_shape_and_formal_first() -> None:
    rows = cases()
    assert len(rows) == 48
    assert sum(row.split == "development" for row in rows) == 32
    assert sum(row.split == "controlled_confirmation" for row in rows) == 16
    assert len({row.problem_id for row in rows}) == 48
    assert all(row.reference["source"] == "controlled-formal-first-v1" for row in rows)


def test_every_controlled_reference_has_solver_parity_and_declared_parser_boundary() -> None:
    for row in cases():
        reference = FormalSpecification.from_dict(row.reference)
        assert enumerate_specification(reference).solutions == solve_z3(reference).solutions
        parsed = parse_public_problem(row.problem_id, row.text)
        assert parsed.status == row.parser_expected
        if parsed.specification is not None:
            assert compare_specifications_by_name(reference, parsed.specification).status == "EQUIVALENT"


def test_evaluation_labels_semantically_equivalent_domain_restriction_as_correct() -> None:
    reference = {
        "problem_id": "P",
        "variables": [{"name": "x", "domain": [-1, 0, 1]}],
        "constraints": [{"kind": "not_equal", "variable": "x", "value": 0}],
        "target": "count_solutions",
        "source": "reference",
        "generation_id": "reference-P",
        "verification_status": "VALIDATED",
    }
    equivalent = {
        **reference,
        "variables": [{"name": "x", "domain": [-1, 1]}],
        "constraints": [],
        "source": "candidate",
        "generation_id": "candidate-P",
        "verification_status": "UNVERIFIED",
    }
    prediction = {"primary": {"specification": equivalent}, "answer": 2}
    assert _label(prediction, {"specification": reference, "answer": 2}) == {
        "specification": "CORRECT",
        "answer": "CORRECT",
    }
