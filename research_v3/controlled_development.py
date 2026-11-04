from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any

from axiom_x.audit import audit_v2_1
from axiom_x.evaluation_v2 import _label, _mcnemar_exact, _measure, _strategy_metrics, evaluate
from axiom_x.providers import GenerationFailure, GenerationRecord
from axiom_x.semantic_v2_1 import parse_public_problem
from axiom_x.solver import compare_specifications_by_name, enumerate_specification, solve_z3
from axiom_x.spec import FormalSpecification
from axiom_x.v2_1 import predict_cases_v2_1, write_frozen_predictions_v2_1


ROOT = Path(__file__).resolve().parent
PROTOCOL = ROOT / "CONTROLLED_PROTOCOL.json"
PROMPT = ROOT / "ollama_formalizer_prompt.txt"
DEFAULT_EVIDENCE = ROOT / "evidence"


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def _spec(problem_id: str, variables: list[dict[str, Any]], constraints: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "problem_id": problem_id,
        "variables": variables,
        "constraints": constraints,
        "target": "count_solutions",
        "source": "controlled-formal-first-v1",
        "generation_id": f"reference-{problem_id}",
        "verification_status": "VALIDATED",
    }


def _range(names: list[str], lower: int, upper: int) -> list[dict[str, Any]]:
    return [{"name": name, "domain": list(range(lower, upper + 1))} for name in names]


@dataclass(frozen=True)
class Case:
    problem_id: str
    split: str
    family: str
    reference: dict[str, Any]
    text: str
    parser_expected: str


def _case(cycle: int, family: int, split: str) -> Case:
    prefix = "D" if split == "development" else "C"
    problem_id = f"CTRL-{prefix}-{family + 1:02d}-{cycle + 1}"
    suffix = f"{prefix.lower()}{cycle + 1}"
    lower = -2 + cycle
    upper = 3 + cycle
    names3 = [f"a{suffix}", f"b{suffix}", f"c{suffix}"]
    names2 = names3[:2]
    parser_expected = "COMPLETE"

    if family == 0:
        constraints = [
            {"kind": "all_different", "variables": names3},
            {"kind": "sum_equal", "variables": names3, "value": 3 + 3 * cycle},
        ]
        variables = _range(names3, lower, upper)
        text = (
            f"Variables {', '.join(names3)} each range over integers {lower} through {upper}. "
            f"All variables are distinct. Their sum is exactly {3 + 3 * cycle}. "
            "How many assignments satisfy all conditions?"
        )
    elif family == 1:
        variables = _range(names3, 0, 4 + cycle)
        constraints = [{"kind": "all_different", "variables": names3}]
        text = (
            f"Variables {', '.join(names3)} each range over integers 0 through {4 + cycle}. "
            "All variables are distinct. How many assignments are possible?"
        )
    elif family == 2:
        variables = _range(names2, lower, upper)
        constraints = [{"kind": "less_than", "left": names2[0], "right": names2[1]}]
        text = (
            f"Variables {names2[0]} and {names2[1]} each range over integers {lower} through {upper}. "
            f"Require {names2[0]} < {names2[1]}. How many ordered assignments are possible?"
        )
    elif family == 3:
        variables = _range(names2, lower, upper)
        constraints = [{"kind": "less_equal", "left": names2[0], "right": names2[1]}]
        text = (
            f"Variables {names2[0]} and {names2[1]} each range over integers {lower} through {upper}. "
            f"Require {names2[0]} <= {names2[1]}. How many ordered assignments are possible?"
        )
    elif family == 4:
        variables = _range(names2, -2, 4 + cycle)
        constraints = [
            {"kind": "less_than", "left": names2[0], "right": names2[1]},
            {"kind": "not_equal", "variable": names2[0], "value": 0},
        ]
        text = (
            f"Variables {names2[0]} and {names2[1]} each range over integers -2 through {4 + cycle}. "
            f"Require {names2[0]} < {names2[1]}, and {names2[0]} is nonzero. "
            "How many ordered assignments are possible?"
        )
    elif family == 5:
        variables = _range(names2, 0, 5 + cycle)
        constraints = [
            {"kind": "sum_at_least", "variables": names2, "value": 3 + cycle},
            {"kind": "sum_at_most", "variables": names2, "value": 7 + cycle},
        ]
        text = (
            f"Variables {names2[0]} and {names2[1]} each range over integers 0 through {5 + cycle}. "
            f"Their sum is at least {3 + cycle} and at most {7 + cycle}. "
            "How many ordered assignments satisfy both bounds?"
        )
    elif family == 6:
        variables = _range(names2, -1, 5 + cycle)
        constraints = [{"kind": "sum_at_most", "variables": names2, "value": 4 + cycle}]
        text = (
            f"Variables {names2[0]} and {names2[1]} each range over integers -1 through {5 + cycle}. "
            f"Their sum is at most {4 + cycle}. How many assignments are possible?"
        )
    elif family == 7:
        variables = _range(names2, -2, 4 + cycle)
        value = 2 + cycle
        constraints = [{"kind": "equal", "variable": names2[1], "value": value}]
        text = (
            f"Variables {names2[0]} and {names2[1]} each range over integers -2 through {4 + cycle}. "
            f"Require {names2[1]} = {value}. How many assignments are possible?"
        )
    elif family == 8:
        variables = _range(names2, -2, 3 + cycle)
        constraints = [{"kind": "not_equal", "variable": names2[1], "value": 0}]
        text = (
            f"Variables {names2[0]} and {names2[1]} each range over integers -2 through {3 + cycle}. "
            f"Require {names2[1]} to be nonzero. How many assignments are possible?"
        )
    elif family == 9:
        name = f"z{suffix}"
        variables = _range([name], -3, 4 + cycle)
        constraints = [{"kind": "not_equal", "variable": name, "value": 0}]
        text = (
            f"Variable {name} ranges over integers -3 through {4 + cycle} and {name} is nonzero. "
            "How many values are possible?"
        )
    elif family in {10, 11, 12}:
        binary_names = [f"q{index}{suffix}" for index in range(5)]
        variables = _range(binary_names, 0, 1)
        kind = {10: "count_equal", 11: "count_at_least", 12: "count_at_most"}[family]
        word = {10: "Exactly", 11: "At least", 12: "At most"}[family]
        count = {10: 2 + cycle, 11: 3, 12: 2 + cycle}[family]
        constraints = [{"kind": kind, "variables": binary_names, "value": 1, "count": count}]
        text = (
            f"Variables {', '.join(binary_names)} are each either 0 or 1. {word} {count} of them equal 1. "
            "How many assignments satisfy this?"
        )
    elif family == 13:
        digit_names = [f"d{index}{suffix}" for index in range(3)]
        variables = _range(digit_names, 0, 9)
        remainder = cycle + 1
        constraints = [
            {"kind": "not_equal", "variable": digit_names[0], "value": 0},
            {"kind": "all_different", "variables": digit_names},
            {
                "kind": "number_mod",
                "variables": digit_names,
                "base": 10,
                "modulus": 4,
                "remainder": remainder,
            },
        ]
        text = (
            f"Digits {', '.join(digit_names)} each range from 0 through 9 and form a three-digit "
            f"base-10 number in that order. {digit_names[0]} is nonzero. All variables are distinct. "
            f"The number has remainder {remainder} modulo 4. How many such numbers exist?"
        )
    elif family == 14:
        variables = _range(names2, 0, 6 + cycle)
        forbidden, total = 2 + cycle, 6 + cycle
        constraints = [
            {"kind": "not_equal", "variable": names2[0], "value": forbidden},
            {"kind": "sum_equal", "variables": names2, "value": total},
        ]
        text = (
            f"Variables {names2[0]} and {names2[1]} each range over integers 0 through {6 + cycle}. "
            f"Variable {names2[0]} must not equal {forbidden}, and {names2[0]} + {names2[1]} must equal {total}. "
            "How many ordered assignments satisfy both conditions?"
        )
    else:
        values = [0, 2 + cycle, 5 + cycle]
        variables = [{"name": name, "domain": values} for name in names2]
        constraints = [{"kind": "less_than", "left": names2[0], "right": names2[1]}]
        text = (
            f"Variables {names2[0]} and {names2[1]} each take values from "
            f"{{{', '.join(map(str, values))}}}. Require {names2[0]} < {names2[1]}. "
            "How many ordered assignments are possible?"
        )
        parser_expected = "UNSUPPORTED"

    return Case(problem_id, split, f"family_{family + 1:02d}", _spec(problem_id, variables, constraints), text, parser_expected)


def cases() -> list[Case]:
    development = [_case(cycle, family, "development") for cycle in range(2) for family in range(16)]
    confirmation = [_case(2, family, "controlled_confirmation") for family in range(16)]
    return development + confirmation


def freeze(evidence: Path) -> dict[str, Any]:
    if evidence.exists():
        raise FileExistsError(f"refusing to overwrite evidence directory: {evidence}")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol["status"] != "FROZEN_BEFORE_MODEL_CALLS":
        raise ValueError("protocol is not frozen")
    all_cases = cases()
    if len(all_cases) != protocol["row_count"]:
        raise AssertionError("protocol row count mismatch")
    public_rows: list[dict[str, Any]] = []
    gold_rows: list[dict[str, Any]] = []
    template_rows: list[dict[str, Any]] = []
    for case in all_cases:
        reference = FormalSpecification.from_dict(case.reference)
        python_result, z3_result = enumerate_specification(reference), solve_z3(reference)
        if python_result.status != "COMPLETE" or python_result.solutions != z3_result.solutions:
            raise AssertionError(f"reference solver disagreement: {case.problem_id}")
        parsed = parse_public_problem(case.problem_id, case.text)
        if parsed.status != case.parser_expected:
            raise AssertionError(f"parser expectation mismatch: {case.problem_id}")
        if parsed.specification is not None and compare_specifications_by_name(reference, parsed.specification).status != "EQUIVALENT":
            raise AssertionError(f"template changed semantics: {case.problem_id}")
        public_rows.append({
            "problem_id": case.problem_id,
            "problem_text": case.text,
            "group_id": case.split,
            "category": case.family,
        })
        gold_rows.append({
            "problem_id": case.problem_id,
            "specification": case.reference,
            "answer": python_result.count,
            "reference_origin": "formal-specification-created-before-text-rendering",
            "human_review": False,
        })
        template_rows.append({
            "problem_id": case.problem_id,
            "split": case.split,
            "family": case.family,
            "parser_expected": case.parser_expected,
        })
    _write_new(evidence / "public_dataset.json", _json_bytes(public_rows))
    _write_new(evidence / "automatic_reference.json", _json_bytes(gold_rows))
    _write_new(evidence / "template_registry.json", _json_bytes(template_rows))
    manifest = {
        "schema": "axiom-x-controlled-dataset-freeze-v1",
        "status": "FROZEN",
        "row_count": len(all_cases),
        "split_counts": {
            name: sum(case.split == name for case in all_cases)
            for name in ("development", "controlled_confirmation")
        },
        "parser_expected_counts": {
            name: sum(case.parser_expected == name for case in all_cases)
            for name in ("COMPLETE", "UNSUPPORTED")
        },
        "formal_reference_precedes_text": True,
        "human_gold": False,
        "natural_distribution": False,
        "protocol_sha256": _sha256(PROTOCOL),
        "prompt_sha256": _sha256(PROMPT),
        "files": {
            name: _sha256(evidence / name)
            for name in ("public_dataset.json", "automatic_reference.json", "template_registry.json")
        },
    }
    _write_new(evidence / "dataset_manifest.json", _json_bytes(manifest))
    return manifest


class OllamaProvider:
    def __init__(self, model: str, protocol: dict[str, Any], prompt: str) -> None:
        self.model, self.protocol, self.prompt = model, protocol, prompt

    def generate(self, problem_id: str, problem_text: str) -> GenerationRecord:
        user_prompt = f"problem_id={problem_id}\nproblem={problem_text}"
        full_prompt = self.prompt + "\n\n" + user_prompt
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "format": "json",
            "think": False,
            "options": {
                "temperature": self.protocol["temperature"],
                "seed": self.protocol["seed"],
                "num_predict": self.protocol["max_output_tokens"],
            },
        }
        request = urllib.request.Request(
            self.protocol["ollama_endpoint"],
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        started = monotonic()
        raw_response = ""
        raw_output = ""
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                body = json.load(response)
            raw_response = json.dumps(body, sort_keys=True, separators=(",", ":"))
            raw_output = body["response"]
            candidate = json.loads(raw_output)
            if not isinstance(candidate, dict) or set(candidate) != {"variables", "constraints"}:
                raise ValueError("model JSON must contain exactly variables and constraints")
            specification = FormalSpecification.from_dict({
                "problem_id": problem_id,
                "variables": candidate["variables"],
                "constraints": candidate["constraints"],
                "target": "count_solutions",
                "source": f"local-ollama-{self.model}",
                "generation_id": f"{self.model}-{problem_id}",
                "verification_status": "UNVERIFIED",
            })
        except Exception as exc:
            raise GenerationFailure(
                f"local model generation failed: {type(exc).__name__}: {exc}",
                {
                    "requested_model": self.model,
                    "attempts": 1,
                    "raw_response": raw_response,
                    "raw_output": raw_output,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "latency_ms": round((monotonic() - started) * 1000),
                },
            ) from exc
        return GenerationRecord(
            provider="local-ollama",
            model=self.model,
            generation_id=specification.generation_id,
            generated_at="2026-11-03T00:00:00+01:00",
            specification=specification,
            prompt_sha256=hashlib.sha256(full_prompt.encode()).hexdigest(),
            raw_output=raw_output,
            raw_response=raw_response,
            input_tokens=body.get("prompt_eval_count"),
            output_tokens=body.get("eval_count"),
            latency_ms=round((monotonic() - started) * 1000),
            requested_model=self.model,
            requested_service_tier="local",
            response_service_tier="local",
            response_id="",
            attempts=1,
        )


def run(evidence: Path) -> dict[str, Any]:
    predictions = evidence / "predictions.jsonl"
    receipt = evidence / "prediction_manifest.json"
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    dataset_manifest = json.loads((evidence / "dataset_manifest.json").read_text(encoding="utf-8"))
    if dataset_manifest["protocol_sha256"] != _sha256(PROTOCOL):
        raise ValueError("protocol changed after dataset freeze")
    public_rows = json.loads((evidence / "public_dataset.json").read_text(encoding="utf-8"))
    prompt = PROMPT.read_text(encoding="utf-8")
    rows = predict_cases_v2_1(
        public_rows,
        OllamaProvider(protocol["primary_model"], protocol, prompt),
        OllamaProvider(protocol["secondary_model"], protocol, prompt),
    )
    config = {
        "primary_model": protocol["primary_model"],
        "secondary_model": protocol["secondary_model"],
        "input_price_usd_per_million": 0,
        "output_price_usd_per_million": 0,
        "pricing_source": "local://ollama/no-paid-api",
        "pricing_checked_on": protocol["frozen_on"],
    }
    result = write_frozen_predictions_v2_1(rows, predictions, receipt, config)
    result["protocol_sha256"] = _sha256(PROTOCOL)
    result["prompt_sha256"] = _sha256(PROMPT)
    receipt.write_bytes(_json_bytes(result))
    return result


def analyse(evidence: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    metrics, paired = evaluate(
        evidence / "predictions.jsonl",
        evidence / "prediction_manifest.json",
        evidence / "automatic_reference.json",
    )
    rows = [json.loads(line) for line in (evidence / "predictions.jsonl").read_text(encoding="utf-8").splitlines() if line]
    gold_rows = json.loads((evidence / "automatic_reference.json").read_text(encoding="utf-8"))
    gold = {row["problem_id"]: row for row in gold_rows}
    labelled = [{**row, "labels": _label(row, gold[row["case_id"]])} for row in rows]
    split_metrics = {
        split: {
            strategy: _strategy_metrics([row for row in labelled if row["group_id"] == split], strategy)
            for strategy in metrics["strategies"]
        }
        for split in ("development", "controlled_confirmation")
    }
    failures = [
        {
            "case_id": row["case_id"],
            "group_id": row["group_id"],
            "primary_error": row["primary_error"],
            "secondary_error": row["secondary_error"],
            "b2_1_decision": row["strategies"]["B2_1"]["decision"],
            "b2_1_reason": row["strategies"]["B2_1"]["reason_code"],
            "specification_label": row["labels"]["specification"],
            "answer_label": row["labels"]["answer"],
        }
        for row in labelled
        if row["primary_error"] or row["secondary_error"] or row["strategies"]["B2_1"]["decision"] != "ACCEPT"
    ]
    summary = {
        "schema": "axiom-x-controlled-analysis-v1",
        "n": len(labelled),
        "primary_generation_failures": sum(row["primary"] is None for row in labelled),
        "secondary_generation_failures": sum(row["secondary"] is None for row in labelled),
        "known_specification_errors": sum(row["labels"]["specification"] == "ERROR" for row in labelled),
        "known_answer_errors": sum(row["labels"]["answer"] == "ERROR" for row in labelled),
        "claim_boundary": "Controlled-language local-model evidence only; no natural-distribution or human-Gold claim.",
    }
    (output / "metrics.json").write_bytes(_json_bytes(metrics))
    with (output / "paired.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(paired[0]))
        writer.writeheader()
        writer.writerows(paired)
    (output / "split_metrics.json").write_bytes(_json_bytes(split_metrics))
    (output / "failure_records.json").write_bytes(_json_bytes(failures))
    (output / "summary.json").write_bytes(_json_bytes(summary))
    manifest = {
        "schema": "axiom-x-controlled-analysis-manifest-v1",
        "files": {path.name: _sha256(path) for path in sorted(output.iterdir()) if path.is_file()},
    }
    (output / "manifest.json").write_bytes(_json_bytes(manifest))
    return summary


def verify(evidence: Path, analysis: Path) -> dict[str, Any]:
    dataset_manifest = json.loads((evidence / "dataset_manifest.json").read_text(encoding="utf-8"))
    dataset_hashes_ok = all(_sha256(evidence / name) == digest for name, digest in dataset_manifest["files"].items())
    prediction_manifest = json.loads((evidence / "prediction_manifest.json").read_text(encoding="utf-8"))
    predictions_ok = _sha256(evidence / "predictions.jsonl") == prediction_manifest["sha256"]
    analysis_manifest = json.loads((analysis / "manifest.json").read_text(encoding="utf-8"))
    analysis_hashes_ok = all(_sha256(analysis / name) == digest for name, digest in analysis_manifest["files"].items())
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        regenerated_evidence = temp_root / "evidence"
        regenerated_manifest = freeze(regenerated_evidence)
        regenerated_dataset_ok = regenerated_manifest["files"] == dataset_manifest["files"]
        regenerated_analysis = temp_root / "analysis"
        analyse(evidence, regenerated_analysis)
        regenerated_analysis_ok = all(
            _sha256(regenerated_analysis / name) == digest
            for name, digest in analysis_manifest["files"].items()
        )
    result = {
        "status": "VERIFIED" if all((dataset_hashes_ok, predictions_ok, analysis_hashes_ok, regenerated_dataset_ok, regenerated_analysis_ok)) else "FAILED",
        "dataset_hashes_ok": dataset_hashes_ok,
        "predictions_hash_ok": predictions_ok,
        "analysis_hashes_ok": analysis_hashes_ok,
        "dataset_regeneration_byte_identical": regenerated_dataset_ok,
        "analysis_regeneration_byte_identical": regenerated_analysis_ok,
        "model_generation_rerun": False,
        "model_generation_note": "Frozen local-model outputs were not regenerated; deterministic evaluation was recomputed byte-for-byte.",
    }
    return result


def explore_secondary(evidence: Path, output: Path) -> dict[str, Any]:
    """Post-hoc symmetric role reversal; never substitutes for the frozen primary estimand."""
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    public = {
        row["problem_id"]: row
        for row in json.loads((evidence / "public_dataset.json").read_text(encoding="utf-8"))
    }
    gold = {
        row["problem_id"]: row
        for row in json.loads((evidence / "automatic_reference.json").read_text(encoding="utf-8"))
    }
    rows = [
        json.loads(line)
        for line in (evidence / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    audited: list[dict[str, Any]] = []
    for row in rows:
        case_id = row["case_id"]
        if row["secondary"] is None:
            label, decision, reason = "UNKNOWN", "ABSTAIN", "SECONDARY_GENERATION_FAILED"
        else:
            secondary = FormalSpecification.from_dict(row["secondary"]["specification"])
            primary = FormalSpecification.from_dict(row["primary"]["specification"]) if row["primary"] else None
            result = audit_v2_1(
                public[case_id]["problem_text"],
                secondary,
                primary,
                proposed_answer=row["secondary_solver"]["count"],
            )
            decision = {"PASS": "ACCEPT", "FAIL": "REJECT", "INCONCLUSIVE": "ABSTAIN"}[result.decision]
            reason = result.reason_code
            label = _label(
                {"primary": row["secondary"], "answer": row["secondary_solver"]["count"]},
                gold[case_id],
            )["specification"]
        audited.append({
            "case_id": case_id,
            "split": row["group_id"],
            "specification_label": label,
            "baseline_decision": "ACCEPT" if row["secondary"] is not None else "ABSTAIN",
            "axiom_x_decision": decision,
            "axiom_x_reason": reason,
        })
    errors = [row for row in audited if row["specification_label"] == "ERROR"]
    correct = [row for row in audited if row["specification_label"] == "CORRECT"]
    accepts = sum(row["axiom_x_decision"] == "ACCEPT" for row in audited)
    rejects = sum(row["axiom_x_decision"] == "REJECT" for row in audited)
    abstains = sum(row["axiom_x_decision"] == "ABSTAIN" for row in audited)
    baseline_fc = sum(row["baseline_decision"] == "ACCEPT" for row in errors)
    axiom_fc = sum(row["axiom_x_decision"] == "ACCEPT" for row in errors)
    detected = sum(row["axiom_x_decision"] == "REJECT" for row in errors)
    false_rejects = sum(row["axiom_x_decision"] == "REJECT" for row in correct)
    result = {
        "schema": "axiom-x-posthoc-secondary-role-reversal-v1",
        "status": "EXPLORATORY_NOT_PREREGISTERED",
        "trigger": "The frozen primary path produced zero semantic error opportunities.",
        "model_outputs_changed": False,
        "primary_estimand_replaced": False,
        "n": len(audited),
        "secondary_generation_failures": sum(row["specification_label"] == "UNKNOWN" for row in audited),
        "specification_error_opportunities": len(errors),
        "baseline_specification_fcr": _measure(baseline_fc, len(errors)),
        "axiom_x_specification_fcr": _measure(axiom_fc, len(errors)),
        "axiom_x_error_detection_rate": _measure(detected, len(errors)),
        "axiom_x_false_rejection_rate": _measure(false_rejects, len(correct)),
        "axiom_x_acceptance_coverage": _measure(accepts, len(audited)),
        "axiom_x_decision_coverage": _measure(accepts + rejects, len(audited)),
        "axiom_x_abstention_rate": _measure(abstains, len(audited)),
        "paired_baseline_vs_axiom_x": {
            "baseline_only_false_certification": baseline_fc - axiom_fc,
            "axiom_x_only_false_certification": 0,
            "discordant": baseline_fc - axiom_fc,
            "mcnemar_exact_p": _mcnemar_exact(baseline_fc - axiom_fc, 0),
        },
        "error_rows": [row for row in audited if row["specification_label"] != "CORRECT"],
        "claim_boundary": "Post-hoc mechanism evidence on the frozen auxiliary model path; not confirmation and not natural-distribution evidence.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_json_bytes(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("freeze", "run", "analyse", "verify", "explore-secondary"))
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--analysis", type=Path, default=ROOT / "analysis")
    parser.add_argument("--secondary-analysis", type=Path, default=ROOT / "secondary_path_exploratory.json")
    args = parser.parse_args()
    if args.command == "freeze":
        result = freeze(args.evidence)
    elif args.command == "run":
        result = run(args.evidence)
    elif args.command == "analyse":
        result = analyse(args.evidence, args.analysis)
    elif args.command == "verify":
        result = verify(args.evidence, args.analysis)
    else:
        result = explore_secondary(args.evidence, args.secondary_analysis)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
