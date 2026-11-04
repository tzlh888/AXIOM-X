from axiom_x.evaluation_v2 import _label
from axiom_x.solver import compare_specifications_by_name
from axiom_x.spec import FormalSpecification
from research_v4.v4_experiment import MECHANISMS, cases


def _spec(names=("x", "y"), domains=((0, 1), (0, 1)), constraints=()):
    return {
        "problem_id": "P",
        "variables": [{"name": name, "domain": list(domain)} for name, domain in zip(names, domains)],
        "constraints": list(constraints),
        "target": "count_solutions",
        "source": "test",
        "generation_id": "test-P",
        "verification_status": "UNVERIFIED",
    }


def test_v4_challenge_is_prospectively_fixed_and_unique() -> None:
    rows = cases()
    assert len(rows) == 96
    assert len({row.case_id for row in rows}) == 96
    assert {row.mechanism for row in rows} == set(MECHANISMS)
    assert all(sum(row.mechanism == mechanism for row in rows) == 8 for mechanism in MECHANISMS)


def test_evaluator_accepts_order_changes_but_not_semantic_changes() -> None:
    reference = _spec(domains=((0, 1, 2), (0, 1, 2)), constraints=({"kind": "less_than", "left": "x", "right": "y"},))
    reordered = _spec(names=("y", "x"), domains=((2, 1, 0), (2, 1, 0)), constraints=({"kind": "less_than", "left": "x", "right": "y"},))
    different = _spec(domains=((0, 1, 2), (0, 1, 2)), constraints=({"kind": "less_equal", "left": "x", "right": "y"},))
    assert _label({"primary": {"specification": reordered}, "answer": 3}, {"specification": reference, "answer": 3})["specification"] == "CORRECT"
    assert _label({"primary": {"specification": different}, "answer": 6}, {"specification": reference, "answer": 3})["specification"] == "ERROR"


def test_exact_name_boundary_makes_renaming_unknown() -> None:
    reference = FormalSpecification.from_dict(_spec())
    renamed = FormalSpecification.from_dict(_spec(names=("u", "v")))
    assert compare_specifications_by_name(reference, renamed).status == "INCONCLUSIVE"
    assert _label({"primary": {"specification": renamed.to_dict()}, "answer": 4}, {"specification": reference.to_dict(), "answer": 4})["specification"] == "UNKNOWN"
import json
from pathlib import Path



def test_v4_model_inputs_are_gold_free_and_do_not_reuse_v3_texts() -> None:
    root = Path(__file__).parents[1]
    v4_public = json.loads((root / "research_v4/evidence/natural_model_public.json").read_text())
    v3_public = json.loads((root / "research_v3/evidence/public_dataset.json").read_text())
    forbidden = {"answer", "gold", "label", "labels", "reference_specification", "specification"}
    assert all(not forbidden.intersection({key.casefold() for key in row}) for row in v4_public)
    assert {row["problem_text"] for row in v4_public}.isdisjoint({row["problem_text"] for row in v3_public})
