from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class FrozenPrediction:
    case_id: str
    group_id: str
    strategy: str
    decision: str
    answer: int | None


def freeze_predictions(predictions: list[FrozenPrediction]) -> tuple[str, str]:
    payload = json.dumps([asdict(item) for item in predictions], sort_keys=True, separators=(",", ":"))
    return payload, hashlib.sha256(payload.encode()).hexdigest()


def evaluate_frozen(
    frozen_payload: str, expected_sha256: str, gold: dict[str, int]
) -> dict[str, Any]:
    if hashlib.sha256(frozen_payload.encode()).hexdigest() != expected_sha256:
        raise ValueError("predictions changed after freeze")
    rows = json.loads(frozen_payload)
    if any(set(row) != {"case_id", "group_id", "strategy", "decision", "answer"} for row in rows):
        raise ValueError("frozen prediction schema contains evaluation-only fields")
    if set(gold) != {row["case_id"] for row in rows}:
        raise ValueError("Gold IDs and frozen prediction IDs differ")
    opportunities = sum(row["answer"] != gold[row["case_id"]] for row in rows if row["answer"] is not None)
    false_certifications = sum(
        row["decision"] == "PASS" and row["answer"] != gold[row["case_id"]]
        for row in rows if row["answer"] is not None
    )
    decisions = sum(row["decision"] != "INCONCLUSIVE" for row in rows)
    correct = [row for row in rows if row["answer"] == gold[row["case_id"]]]
    false_positives = sum(
        row["decision"] == "FAIL" and row["answer"] == gold[row["case_id"]]
        for row in rows if row["answer"] is not None
    )
    evaluated_correct = sum(row["answer"] == gold[row["case_id"]] for row in rows if row["answer"] is not None)
    return {
        "n": len(rows),
        "wrong_answer_opportunities": opportunities,
        "false_certifications": false_certifications,
        "false_certification_rate": false_certifications / opportunities if opportunities else None,
        "false_certification_rate_status": "DEFINED" if opportunities else "UNDEFINED_ZERO_DENOMINATOR",
        "false_negatives": false_certifications,
        "false_positive_count": false_positives,
        "false_positive_rate": false_positives / evaluated_correct if evaluated_correct else None,
        "classification_definition": "FAIL predicts an answer error; PASS predicts no detected error; INCONCLUSIVE is excluded from FP/FN counts but retained in coverage",
        "decision_coverage": decisions / len(rows) if rows else None,
        "abstention_rate": (len(rows) - decisions) / len(rows) if rows else None,
        "correct_answer_acceptance_rate": (
            sum(row["decision"] == "PASS" for row in correct) / len(correct) if correct else None
        ),
    }


def evaluate_strategies(
    frozen_payload: str, expected_sha256: str, gold: dict[str, int]
) -> dict[str, dict[str, Any]]:
    if hashlib.sha256(frozen_payload.encode()).hexdigest() != expected_sha256:
        raise ValueError("predictions changed after freeze")
    rows = json.loads(frozen_payload)
    strategies = sorted({str(row["strategy"]) for row in rows})
    output: dict[str, dict[str, Any]] = {}
    for strategy in strategies:
        selected = [row for row in rows if row["strategy"] == strategy]
        selected_payload = json.dumps(selected, sort_keys=True, separators=(",", ":"))
        selected_gold = {row["case_id"]: gold[row["case_id"]] for row in selected}
        output[strategy] = evaluate_frozen(
            selected_payload, hashlib.sha256(selected_payload.encode()).hexdigest(), selected_gold
        )
    return output


def grouped_bootstrap_difference(
    rows: list[dict[str, Any]], metric: Callable[[list[dict[str, Any]]], float],
    *, left: str, right: str, replicates: int = 2_000, seed: int = 20261022,
) -> dict[str, float | int]:
    groups = sorted({str(row["group_id"]) for row in rows})
    if not groups or replicates < 1:
        raise ValueError("non-empty groups and positive replicates are required")
    by_group = {group: [row for row in rows if str(row["group_id"]) == group] for group in groups}
    rng = random.Random(seed)
    deltas: list[float] = []
    for _ in range(replicates):
        sample = [row for group in rng.choices(groups, k=len(groups)) for row in by_group[group]]
        deltas.append(metric([row for row in sample if row["strategy"] == left]) - metric([row for row in sample if row["strategy"] == right]))
    deltas.sort()
    return {
        "replicates": replicates, "seed": seed,
        "p2_5": deltas[math.floor(0.025 * (replicates - 1))],
        "p50": deltas[math.floor(0.5 * (replicates - 1))],
        "p97_5": deltas[math.floor(0.975 * (replicates - 1))],
    }
