from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from axiom_x.audit import audit
from axiom_x.evaluation_v2 import evaluate
from axiom_x.providers import FixtureProvider
from axiom_x.v2 import predict_cases, validate_public_cases, write_frozen_predictions


def raw_spec(problem_id: str, source: str) -> dict:
    return {"problem_id": problem_id, "variables": [{"name": "x", "domain": [0, 1]}],
            "constraints": [], "target": "count_solutions", "source": source,
            "generation_id": "replaced", "verification_status": "UNVERIFIED"}


def test_primary_secondary_receive_only_public_id_and_text() -> None:
    calls: list[tuple[str, str, str]] = []

    class Spy(FixtureProvider):
        def generate(self, problem_id: str, problem_text: str):
            calls.append((self.name, problem_id, problem_text))
            return super().generate(problem_id, problem_text)

    case = {"problem_id": "P1", "problem_text": "Public canary only", "group_id": "G", "category": "test"}
    predict_cases([case], Spy("primary", {"P1": raw_spec("P1", "p")}),
                  Spy("secondary", {"P1": raw_spec("P1", "s")}))
    assert calls == [("primary", "P1", "Public canary only"),
                     ("secondary", "P1", "Public canary only")]


def test_audit_interface_has_no_gold_parameter() -> None:
    assert "gold" not in inspect.signature(audit).parameters


def test_prompts_contain_no_gold_canary_or_answer(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    combined = (root / "prompts/v2_primary.txt").read_text() + (root / "prompts/v2_secondary.txt").read_text()
    assert "CANARY_GOLD_917263" not in combined
    assert "reference answer=" not in combined.casefold()


def test_contaminated_public_dataset_blocks_prediction() -> None:
    with pytest.raises(ValueError, match="Gold-bearing"):
        validate_public_cases([{"problem_id": "P", "problem_text": "x", "answer": 2}])
    with pytest.raises(ValueError, match="Gold-bearing"):
        validate_public_cases([{"problem_id": "P", "problem_text": "x", "specification": {}}])


def test_evaluation_requires_untampered_freeze(tmp_path: Path) -> None:
    case = {"problem_id": "P1", "problem_text": "x is binary", "group_id": "G", "category": "test"}
    provider = FixtureProvider("p", {"P1": raw_spec("P1", "fixture")})
    rows = predict_cases([case], provider, provider)
    predictions, manifest = tmp_path / "predictions.jsonl", tmp_path / "freeze.json"
    write_frozen_predictions(rows, predictions, manifest)
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps([{"problem_id": "P1", "specification": raw_spec("P1", "gold"), "answer": 2}]))
    missing = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        evaluate(predictions, missing, gold)
    predictions.write_text(predictions.read_text() + " ")
    with pytest.raises(ValueError, match="changed after freeze"):
        evaluate(predictions, manifest, gold)


def test_gold_change_cannot_change_frozen_prediction_bytes(tmp_path: Path) -> None:
    case = {"problem_id": "P1", "problem_text": "x is binary", "group_id": "G", "category": "test"}
    provider = FixtureProvider("p", {"P1": raw_spec("P1", "fixture")})
    predictions, manifest = tmp_path / "predictions.jsonl", tmp_path / "freeze.json"
    write_frozen_predictions(predict_cases([case], provider, provider), predictions, manifest)
    before = hashlib.sha256(predictions.read_bytes()).hexdigest()
    gold = tmp_path / "gold.json"
    for answer in (2, 1):
        gold.write_text(json.dumps([{"problem_id": "P1", "specification": raw_spec("P1", "gold"), "answer": answer}]))
        evaluate(predictions, manifest, gold)
        assert hashlib.sha256(predictions.read_bytes()).hexdigest() == before


def test_gold_derived_reference_never_flows_to_secondary() -> None:
    captured: list[str] = []

    class SecondarySpy(FixtureProvider):
        def generate(self, problem_id: str, problem_text: str):
            captured.append(problem_text)
            return super().generate(problem_id, problem_text)

    case = {"problem_id": "P1", "problem_text": "PUBLIC_TEXT", "group_id": "G", "category": "test"}
    predict_cases([case], FixtureProvider("p", {"P1": raw_spec("P1", "p")}),
                  SecondarySpy("s", {"P1": raw_spec("P1", "s")}))
    assert captured == ["PUBLIC_TEXT"]

