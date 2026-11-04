from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from itertools import combinations
from pathlib import Path
from typing import Any

from .solver import compare_specifications_by_name
from .spec import FormalSpecification


STRATEGY_ORDER = ("B0", "B1", "B2", "B2_1", "B3")
FREEZE_SCHEMAS = {"axiom-x-v2-freeze-v1", "axiom-x-v2-1-freeze-v1"}

def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _wilson(numerator: int, denominator: int, z: float = 1.959963984540054) -> list[float] | None:
    if denominator == 0:
        return None
    p = numerator / denominator
    scale = 1 + z * z / denominator
    centre = (p + z * z / (2 * denominator)) / scale
    radius = z * math.sqrt(p * (1 - p) / denominator + z * z / (4 * denominator * denominator)) / scale
    return [max(0.0, centre - radius), min(1.0, centre + radius)]


def _measure(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": _ratio(numerator, denominator),
        "wilson_95": _wilson(numerator, denominator),
        "status": "DEFINED" if denominator else "N/A_ZERO_DENOMINATOR",
    }


def _read_frozen(predictions: Path, manifest: Path) -> list[dict[str, Any]]:
    receipt = json.loads(manifest.read_text(encoding="utf-8"))
    payload = predictions.read_bytes()
    if receipt.get("schema") not in FREEZE_SCHEMAS:
        raise ValueError("missing or invalid prediction freeze receipt")
    if receipt.get("sha256") != hashlib.sha256(payload).hexdigest():
        raise ValueError("predictions changed after freeze")
    rows = [json.loads(line) for line in payload.decode().splitlines() if line]
    if len(rows) != receipt.get("row_count"):
        raise ValueError("prediction row count differs from freeze receipt")
    return rows


def _label(prediction: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    if prediction["primary"] is None:
        specification_label = "UNKNOWN"
    else:
        primary = FormalSpecification.from_dict(prediction["primary"]["specification"])
        reference = FormalSpecification.from_dict(gold["specification"])
        comparison = compare_specifications_by_name(primary, reference)
        specification_label = {
            "EQUIVALENT": "CORRECT", "DIFFERENT": "ERROR", "INCONCLUSIVE": "UNKNOWN"
        }[comparison.status]
    answer = prediction.get("answer")
    answer_label = "UNKNOWN" if answer is None else ("CORRECT" if answer == gold["answer"] else "ERROR")
    return {"specification": specification_label, "answer": answer_label}


def _strategy_metrics(
    rows: list[dict[str, Any]], strategy: str, pricing: dict[str, Any] | None = None
) -> dict[str, Any]:
    def generation(row: dict[str, Any], name: str) -> dict[str, Any]:
        return row.get(name) or row.get(f"{name}_failure") or {}

    decisions = [(row["strategies"][strategy]["decision"], row["labels"]) for row in rows]
    n = len(rows)
    accepted = sum(decision == "ACCEPT" for decision, _ in decisions)
    rejected = sum(decision == "REJECT" for decision, _ in decisions)
    abstained = sum(decision == "ABSTAIN" for decision, _ in decisions)
    spec_labelled = sum(labels["specification"] != "UNKNOWN" for _, labels in decisions)
    answer_labelled = sum(labels["answer"] != "UNKNOWN" for _, labels in decisions)
    spec_errors = sum(labels["specification"] == "ERROR" for _, labels in decisions)
    answer_errors = sum(labels["answer"] == "ERROR" for _, labels in decisions)
    spec_correct = sum(labels["specification"] == "CORRECT" for _, labels in decisions)
    answer_correct = sum(labels["answer"] == "CORRECT" for _, labels in decisions)
    accepted_labelled_spec = sum(decision == "ACCEPT" and labels["specification"] != "UNKNOWN" for decision, labels in decisions)
    accepted_labelled_answer = sum(decision == "ACCEPT" and labels["answer"] != "UNKNOWN" for decision, labels in decisions)
    spec_fc = sum(decision == "ACCEPT" and labels["specification"] == "ERROR" for decision, labels in decisions)
    answer_fc = sum(decision == "ACCEPT" and labels["answer"] == "ERROR" for decision, labels in decisions)
    spec_detected = sum(decision == "REJECT" and labels["specification"] == "ERROR" for decision, labels in decisions)
    answer_detected = sum(decision == "REJECT" and labels["answer"] == "ERROR" for decision, labels in decisions)
    spec_false_reject = sum(decision == "REJECT" and labels["specification"] == "CORRECT" for decision, labels in decisions)
    answer_false_reject = sum(decision == "REJECT" and labels["answer"] == "CORRECT" for decision, labels in decisions)
    use_secondary = strategy in {"B2", "B2_1"}
    primary_input_tokens = sum(generation(row, "primary").get("input_tokens") or 0 for row in rows)
    primary_output_tokens = sum(generation(row, "primary").get("output_tokens") or 0 for row in rows)
    secondary_input_tokens = (
        sum(generation(row, "secondary").get("input_tokens") or 0 for row in rows)
        if use_secondary else 0
    )
    secondary_output_tokens = (
        sum(generation(row, "secondary").get("output_tokens") or 0 for row in rows)
        if use_secondary else 0
    )
    input_tokens = primary_input_tokens + secondary_input_tokens
    output_tokens = primary_output_tokens + secondary_output_tokens
    latency_ms = sum(
        generation(row, "primary").get("latency_ms") or 0 for row in rows
    ) + (
        sum(generation(row, "secondary").get("latency_ms") or 0 for row in rows)
        if use_secondary else 0
    )
    model_calls = sum(
        generation(row, "primary").get("attempts", 1)
        for row in rows
    )
    if use_secondary:
        model_calls += sum(
            generation(row, "secondary").get("attempts", 1)
            for row in rows
        )
    peer_comparisons = [
        row["strategies"][strategy].get("evidence", {}).get("specification_comparison", {}).get("primary_secondary")
        for row in rows
        if isinstance(row["strategies"][strategy].get("evidence", {}).get("specification_comparison"), dict)
    ]
    peer_comparisons = [item for item in peer_comparisons if isinstance(item, dict)]
    peer_differences = sum(item.get("status") == "DIFFERENT" for item in peer_comparisons)
    common_error_rows = [
        row for row in rows
        if row["category"] == "common_mode_error" and row["labels"]["specification"] == "ERROR"
    ]
    common_errors_rejected = sum(
        row["strategies"][strategy]["decision"] == "REJECT" for row in common_error_rows
    )
    correct_specifications_accepted = sum(
        decision == "ACCEPT" and labels["specification"] == "CORRECT"
        for decision, labels in decisions
    )
    common_errors_missed = len(common_error_rows) - common_errors_rejected
    if pricing and all(
        isinstance(pricing.get(key), (int, float))
        for key in ("input_price_usd_per_million", "output_price_usd_per_million")
    ):
        cost_usd = (
            input_tokens * pricing["input_price_usd_per_million"]
            + output_tokens * pricing["output_price_usd_per_million"]
        ) / 1_000_000
        cost_status = "CALCULATED_FROM_FROZEN_PRICES"
    else:
        cost_usd, cost_status = None, "N/A_PROVIDER_PRICING_NOT_FROZEN"
    return {
        "n": n,
        "acceptance_coverage": _measure(accepted, n),
        "decision_coverage": _measure(accepted + rejected, n),
        "abstention_rate": _measure(abstained, n),
        "correct_specification_acceptance_rate": _measure(
            correct_specifications_accepted, spec_correct
        ),
        "specification_false_certification_rate": _measure(spec_fc, spec_errors),
        "answer_false_certification_rate": _measure(answer_fc, answer_errors),
        "specification_error_detection_rate": _measure(spec_detected, spec_errors),
        "answer_error_detection_rate": _measure(answer_detected, answer_errors),
        "specification_false_rejection_rate": _measure(spec_false_reject, spec_correct),
        "answer_false_rejection_rate": _measure(answer_false_reject, answer_correct),
        "specification_selective_risk": _measure(spec_fc, accepted_labelled_spec),
        "answer_selective_risk": _measure(answer_fc, accepted_labelled_answer),
        "specification_error_rate": _measure(spec_errors, spec_labelled),
        "answer_error_rate": _measure(answer_errors, answer_labelled),
        "specification_disagreement_rate": (
            _measure(peer_differences, len(peer_comparisons)) if peer_comparisons
            else {"numerator": None, "denominator": 0, "value": None,
                  "wilson_95": None, "status": "N/A_NOT_RECORDED"}
        ),
        "common_error_detection_rate": _measure(common_errors_rejected, len(common_error_rows)),
        "common_error_miss_rate": _measure(common_errors_missed, len(common_error_rows)),
        "counts": {"accepted": accepted, "rejected": rejected, "abstained": abstained,
                   "specification_unknown": n - spec_labelled, "answer_unknown": n - answer_labelled},
        "resource_use": {
            "model_calls": model_calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "tokens": input_tokens + output_tokens,
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
            "cost_status": cost_status,
        },
    }


def _mcnemar_exact(b: int, c: int) -> float | None:
    n = b + c
    if n == 0:
        return None
    tail = sum(math.comb(n, k) for k in range(0, min(b, c) + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def paired_comparisons(
    rows: list[dict[str, Any]], strategies: tuple[str, ...] | None = None
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    if strategies is None:
        strategies = tuple(name for name in STRATEGY_ORDER if all(name in row["strategies"] for row in rows))
    for left, right in combinations(strategies, 2):
        b = c = 0
        for row in rows:
            if row["labels"]["specification"] != "ERROR":
                continue
            left_fc = row["strategies"][left]["decision"] == "ACCEPT"
            right_fc = row["strategies"][right]["decision"] == "ACCEPT"
            b += left_fc and not right_fc
            c += right_fc and not left_fc
        output.append({"left": left, "right": right, "left_only_false_certification": b,
                       "right_only_false_certification": c, "discordant": b + c,
                       "mcnemar_exact_p": _mcnemar_exact(b, c)})
    return output


def evaluate(predictions: Path, manifest: Path, gold_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    predictions_rows = _read_frozen(predictions, manifest)
    receipt = json.loads(manifest.read_text(encoding="utf-8"))
    pricing = receipt.get("resource_use") if isinstance(receipt.get("resource_use"), dict) else None
    gold_rows = json.loads(gold_path.read_text(encoding="utf-8"))
    gold = {row["problem_id"]: row for row in gold_rows}
    if set(gold) != {row["case_id"] for row in predictions_rows}:
        raise ValueError("Gold IDs and prediction IDs differ")
    labelled = []
    for row in predictions_rows:
        labelled.append({**row, "labels": _label(row, gold[row["case_id"]])})
    strategies = tuple(name for name in STRATEGY_ORDER if all(name in row["strategies"] for row in labelled))
    metrics = {
        "schema": "axiom-x-v2-metrics-v1",
        "metric_note": "Every proportion includes raw numerator/denominator; zero denominators are N/A.",
        "strategy_descriptions": {
            "B0": "Primary plus Z3",
            "B1": "Primary plus Z3 and deterministic simple rules",
            "B2": "original independent-generation comparison",
            "B2_1": "evidence-driven deterministic public-text audit",
            "B3": "deterministic rule-based back-translation baseline; not an LLM back-translation",
        },
        "strategies": {name: _strategy_metrics(labelled, name, pricing) for name in strategies},
        "error_types": {
            category: {
                name: _strategy_metrics(
                    [row for row in labelled if row["category"] == category], name, pricing
                )
                for name in strategies
            }
            for category in sorted({row["category"] for row in labelled})
        },
    }
    return metrics, paired_comparisons(labelled, strategies)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate already frozen AXIOM-X V2 predictions")
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--paired", type=Path, required=True)
    args = parser.parse_args()
    metrics, paired = evaluate(args.predictions, args.manifest, args.gold)
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    args.metrics.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with args.paired.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(paired[0]))
        writer.writeheader()
        writer.writerows(paired)
    print(json.dumps({"status": "EVALUATED_FROZEN_PREDICTIONS", "n": next(iter(metrics["strategies"].values()))["n"]}, indent=2))


if __name__ == "__main__":
    main()
