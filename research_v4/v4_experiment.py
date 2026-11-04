from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from axiom_x.audit import audit_v2_1
from axiom_x.evaluation_v2 import _mcnemar_exact, _measure
from axiom_x.providers import GenerationFailure
from axiom_x.semantic_v2_1 import parse_public_problem
from axiom_x.solver import compare_specifications_by_name, enumerate_specification, solve_z3
from axiom_x.spec import FormalSpecification
from axiom_x.v2 import cheap_rule_decision
from research_v3.controlled_development import OllamaProvider


ROOT = Path(__file__).resolve().parent
PROTOCOL = ROOT / "PROTOCOL.json"
TAXONOMY = ROOT / "ERROR_TAXONOMY.json"
PROMPT = ROOT / "ollama_formalizer_prompt.txt"
EVIDENCE = ROOT / "evidence"
ANALYSIS = ROOT / "analysis"


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(_json_bytes(value) if not isinstance(value, bytes) else value)


def _spec(case_id: str, variables: list[dict[str, Any]], constraints: list[dict[str, Any]], source: str) -> dict[str, Any]:
    return {
        "problem_id": case_id,
        "variables": variables,
        "constraints": constraints,
        "target": "count_solutions",
        "source": source,
        "generation_id": f"{source}-{case_id}",
        "verification_status": "VALIDATED" if source == "v4-reference" else "UNVERIFIED",
    }


def _range(names: list[str], lower: int, upper: int) -> list[dict[str, Any]]:
    return [{"name": name, "domain": list(range(lower, upper + 1))} for name in names]


@dataclass(frozen=True)
class ChallengeCase:
    case_id: str
    mechanism: str
    label: str
    text: str
    reference: dict[str, Any]
    candidate: dict[str, Any]
    parser_expected: str
    source_group: str


def _build_case(mechanism: str, index: int) -> ChallengeCase:
    case_id = f"V4-{mechanism.upper().replace('_', '-')}-{index + 1:02d}"
    tag = f"{mechanism[:2]}{index + 1}"
    x, y, z = f"x{tag}", f"y{tag}", f"z{tag}"
    label, parser_expected = "ERROR", "COMPLETE"

    if mechanism == "incorrect_numerical_bounds":
        upper = 4 + index % 3
        variables = _range([x, y], 0, upper)
        constraints = [{"kind": "less_than", "left": x, "right": y}]
        candidate_variables = _range([x, y], 0, upper + 1)
        candidate_constraints = constraints
        text = f"Variables {x} and {y} each range over integers 0 through {upper}. Require {x} < {y}. How many ordered assignments are possible?"
    elif mechanism == "missing_constraint":
        upper, total = 5 + index % 2, 6 + index % 3
        variables = _range([x, y, z], 0, upper)
        constraints = [
            {"kind": "all_different", "variables": [x, y, z]},
            {"kind": "sum_equal", "variables": [x, y, z], "value": total},
        ]
        candidate_variables, candidate_constraints = variables, constraints[:1]
        text = f"Variables {x}, {y}, {z} each range over integers 0 through {upper}. All variables are distinct. Their sum is exactly {total}. How many assignments satisfy all conditions?"
    elif mechanism == "added_constraint":
        upper = 5 + index % 3
        variables = _range([x, y], 0, upper)
        constraints = [{"kind": "sum_at_most", "variables": [x, y], "value": upper + 1}]
        candidate_variables = variables
        candidate_constraints = constraints + [{"kind": "not_equal", "variable": x, "value": index % (upper + 1)}]
        text = f"Variables {x} and {y} each range over integers 0 through {upper}. Their sum is at most {upper + 1}. How many assignments are possible?"
    elif mechanism == "incorrect_logical_operator":
        upper = 4 + index % 4
        variables = _range([x, y], -1, upper)
        constraints = [{"kind": "less_than", "left": x, "right": y}]
        candidate_variables = variables
        candidate_constraints = [{"kind": "less_equal", "left": x, "right": y}]
        text = f"Variables {x} and {y} each range over integers -1 through {upper}. Require {x} < {y}. How many ordered assignments are possible?"
    elif mechanism == "incorrect_negation":
        upper = 3 + index % 4
        variables = _range([x, y], -2, upper)
        constraints = [{"kind": "not_equal", "variable": y, "value": 0}]
        candidate_variables = variables
        candidate_constraints = [{"kind": "equal", "variable": y, "value": 0}]
        text = f"Variables {x} and {y} each range over integers -2 through {upper}. Require {y} to be nonzero. How many assignments are possible?"
    elif mechanism == "incorrect_equality":
        upper, value = 5 + index % 3, 1 + index % 3
        variables = _range([x, y], 0, upper)
        constraints = [{"kind": "equal", "variable": y, "value": value}]
        candidate_variables = variables
        candidate_constraints = [{"kind": "not_equal", "variable": y, "value": value}]
        text = f"Variables {x} and {y} each range over integers 0 through {upper}. Require {y} = {value}. How many assignments are possible?"
    elif mechanism == "variable_mapping_error":
        upper, value = 4 + index % 4, 1 + index % 2
        variables = _range([x, y], 0, upper)
        constraints = [{"kind": "equal", "variable": y, "value": value}]
        candidate_variables = variables
        candidate_constraints = [{"kind": "equal", "variable": x, "value": value}]
        text = f"Variables {x} and {y} each range over integers 0 through {upper}. Require {y} = {value}. How many assignments are possible?"
    elif mechanism == "cardinality_mistake":
        names = [f"b{n}{tag}" for n in range(5)]
        count = 1 + index % 3
        variables = _range(names, 0, 1)
        constraints = [{"kind": "count_equal", "variables": names, "value": 1, "count": count}]
        candidate_variables = variables
        candidate_constraints = [{"kind": "count_equal", "variables": names, "value": 1, "count": count + 1}]
        text = f"Variables {', '.join(names)} are each either 0 or 1. Exactly {count} of them equal 1. How many assignments satisfy this?"
    elif mechanism == "modulo_remainder_error":
        names = [f"d{n}{tag}" for n in range(3)]
        remainder = index % 4
        variables = _range(names, 0, 9)
        constraints = [
            {"kind": "not_equal", "variable": names[0], "value": 0},
            {"kind": "all_different", "variables": names},
            {"kind": "number_mod", "variables": names, "base": 10, "modulus": 4, "remainder": remainder},
        ]
        candidate_variables = variables
        candidate_constraints = constraints[:2] + [
            {"kind": "number_mod", "variables": names, "base": 10, "modulus": 4, "remainder": (remainder + 1) % 4}
        ]
        text = f"Digits {', '.join(names)} each range from 0 through 9 and form a three-digit base-10 number in that order. {names[0]} is nonzero. All variables are distinct. The number has remainder {remainder} modulo 4. How many such numbers exist?"
    elif mechanism == "correct_specification":
        label = "CORRECT"
        lower, upper = -1, 5 + index % 3
        variables = _range([x, y], lower, upper)
        constraints = [
            {"kind": "sum_at_least", "variables": [x, y], "value": 2 + index % 2},
            {"kind": "sum_at_most", "variables": [x, y], "value": 6 + index % 2},
        ]
        candidate_variables, candidate_constraints = variables, constraints
        text = f"Variables {x} and {y} each range over integers {lower} through {upper}. Their sum is at least {2 + index % 2} and at most {6 + index % 2}. How many ordered assignments satisfy both bounds?"
    elif mechanism == "unsupported_grammar":
        label, parser_expected = "CORRECT", "UNSUPPORTED"
        values = [0, 2 + index, 7 + index]
        variables = [{"name": name, "domain": values} for name in (x, y)]
        constraints = [{"kind": "less_than", "left": x, "right": y}]
        candidate_variables, candidate_constraints = variables, constraints
        text = f"Variables {x} and {y} each take values from {{{', '.join(map(str, values))}}}. Require {x} < {y}. How many ordered assignments are possible?"
    elif mechanism == "ambiguous_text":
        label, parser_expected = "UNRESOLVED", "UNSUPPORTED"
        names = [f"a{n}{tag}" for n in range(4)]
        variables = _range(names, 0, 1)
        constraints = [{"kind": "count_equal", "variables": names, "value": 1, "count": 2}]
        candidate_variables, candidate_constraints = variables, constraints
        text = f"Variables {', '.join(names)} are binary. Exactly two of them are 1 or 0. How many assignments are possible?"
    else:
        raise AssertionError(mechanism)

    reference = _spec(case_id, variables, constraints, "v4-reference")
    candidate = _spec(case_id, candidate_variables, candidate_constraints, f"v4-{mechanism}")
    return ChallengeCase(case_id, mechanism, label, text, reference, candidate, parser_expected, case_id)


MECHANISMS = (
    "incorrect_numerical_bounds", "missing_constraint", "added_constraint",
    "incorrect_logical_operator", "incorrect_negation", "incorrect_equality",
    "variable_mapping_error", "cardinality_mistake", "modulo_remainder_error",
    "correct_specification", "unsupported_grammar", "ambiguous_text",
)


def cases() -> list[ChallengeCase]:
    return [_build_case(mechanism, index) for mechanism in MECHANISMS for index in range(8)]


def _validate_case(case: ChallengeCase) -> dict[str, Any]:
    reference = FormalSpecification.from_dict(case.reference)
    candidate = FormalSpecification.from_dict(case.candidate)
    reference_python, reference_z3 = enumerate_specification(reference), solve_z3(reference)
    candidate_python, candidate_z3 = enumerate_specification(candidate), solve_z3(candidate)
    if reference_python.solutions != reference_z3.solutions or candidate_python.solutions != candidate_z3.solutions:
        raise AssertionError(f"solver disagreement: {case.case_id}")
    comparison = compare_specifications_by_name(reference, candidate)
    expected = "DIFFERENT" if case.label == "ERROR" else "EQUIVALENT"
    if comparison.status != expected:
        raise AssertionError(f"candidate eligibility failed: {case.case_id}: {comparison.status}")
    parsed = parse_public_problem(case.case_id, case.text)
    if parsed.status != case.parser_expected:
        raise AssertionError(f"parser boundary mismatch: {case.case_id}")
    if parsed.specification is not None and compare_specifications_by_name(reference, parsed.specification).status != "EQUIVALENT":
        raise AssertionError(f"template semantics mismatch: {case.case_id}")
    return {
        "reference_count": reference_python.count,
        "candidate_count": candidate_python.count,
        "candidate_relation": comparison.status,
        "counterexample": comparison.counterexample,
    }


def freeze(evidence: Path) -> dict[str, Any]:
    if evidence.exists():
        raise FileExistsError(f"refusing to overwrite {evidence}")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    all_cases = cases()
    if len(all_cases) != protocol["challenge_rows"] or len(taxonomy["mechanisms"]) != len(MECHANISMS):
        raise AssertionError("protocol/taxonomy shape mismatch")
    public, references, candidates, validation = [], [], [], []
    for case in all_cases:
        checked = _validate_case(case)
        public.append({
            "problem_id": case.case_id,
            "problem_text": case.text,
            "group_id": case.source_group,
            "category": case.mechanism,
        })
        references.append({
            "problem_id": case.case_id,
            "specification": case.reference,
            "reference_status": "UNRESOLVED" if case.label == "UNRESOLVED" else "AUTOMATIC_DUAL_SOLVER_VALIDATED",
            "expected_label": case.label,
            "human_review": False,
            "answer": checked["reference_count"] if case.label != "UNRESOLVED" else None,
        })
        candidates.append({
            "problem_id": case.case_id,
            "mechanism": case.mechanism,
            "candidate": case.candidate,
            "candidate_origin": "SYNTHETIC_INJECTED_ERROR" if case.label == "ERROR" else "CONTROL",
        })
        validation.append({"problem_id": case.case_id, "parser_expected": case.parser_expected, **checked})
    natural_ids = {
        case.case_id
        for case in all_cases
        if case.mechanism != "ambiguous_text" and (
            case.case_id.endswith(("-01", "-02", "-03", "-04"))
            or (case.mechanism == "correct_specification" and case.case_id.endswith(("-05", "-06", "-07", "-08")))
        )
    }
    natural_public = [row for row in public if row["problem_id"] in natural_ids]
    if len(natural_public) != protocol["natural_model_tasks"]:
        raise AssertionError(f"natural task count mismatch: {len(natural_public)}")
    _write_new(evidence / "challenge_public.json", public)
    _write_new(evidence / "automatic_references.json", references)
    _write_new(evidence / "challenge_candidates.json", candidates)
    _write_new(evidence / "eligibility_validation.json", validation)
    _write_new(evidence / "natural_model_public.json", natural_public)
    manifest = {
        "schema": "axiom-x-v4-dataset-freeze-v1",
        "status": "FROZEN",
        "challenge_rows": len(public),
        "natural_model_tasks": len(natural_public),
        "error_opportunities": sum(row["expected_label"] == "ERROR" for row in references),
        "correct_controls": sum(row["expected_label"] == "CORRECT" for row in references),
        "unresolved_controls": sum(row["expected_label"] == "UNRESOLVED" for row in references),
        "protocol_sha256": _sha256(PROTOCOL),
        "taxonomy_sha256": _sha256(TAXONOMY),
        "prompt_sha256": _sha256(PROMPT),
        "files": {
            path.name: _sha256(path)
            for path in sorted(evidence.iterdir()) if path.is_file()
        },
    }
    _write_new(evidence / "dataset_manifest.json", manifest)
    return manifest


def run_models(evidence: Path) -> dict[str, Any]:
    output, manifest_path = evidence / "natural_model_predictions.jsonl", evidence / "natural_model_prediction_manifest.json"
    if output.exists() or manifest_path.exists():
        raise FileExistsError("refusing to overwrite frozen V4 model evidence")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    dataset_manifest = json.loads((evidence / "dataset_manifest.json").read_text(encoding="utf-8"))
    if dataset_manifest["protocol_sha256"] != _sha256(PROTOCOL):
        raise ValueError("protocol changed after data freeze")
    tasks = json.loads((evidence / "natural_model_public.json").read_text(encoding="utf-8"))
    prompt = PROMPT.read_text(encoding="utf-8")
    rows: list[dict[str, Any]] = []
    for model in protocol["model_order"]:
        provider = OllamaProvider(model, protocol, prompt)
        for task in tasks:
            record, failure = None, None
            try:
                record = provider.generate(task["problem_id"], task["problem_text"])
            except GenerationFailure as exc:
                failure = {"error": str(exc), **exc.record}
            if record is None:
                solver = {"status": "NOT_RUN", "count": None}
            else:
                solved = solve_z3(record.specification)
                solver = {"status": solved.status, "count": solved.count}
            rows.append({
                "model": model,
                "case_id": task["problem_id"],
                "generation": asdict(record) | {"specification": record.specification.to_dict()} if record else None,
                "failure": failure,
                "solver": solver,
            })
    payload = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows).encode()
    output.write_bytes(payload)
    manifest = {
        "schema": "axiom-x-v4-natural-model-freeze-v1",
        "status": "FROZEN",
        "row_count": len(rows),
        "task_count": len(tasks),
        "models": protocol["model_order"],
        "sha256": hashlib.sha256(payload).hexdigest(),
        "protocol_sha256": _sha256(PROTOCOL),
        "prompt_sha256": _sha256(PROMPT),
    }
    _write_new(manifest_path, manifest)
    return manifest


def _decision(text: str, candidate: FormalSpecification, answer: int | None) -> dict[str, str]:
    result = audit_v2_1(text, candidate, None, proposed_answer=answer)
    return {
        "decision": {"PASS": "ACCEPT", "FAIL": "REJECT", "INCONCLUSIVE": "ABSTAIN"}[result.decision],
        "reason": result.reason_code,
    }


def _metrics(rows: list[dict[str, Any]], strategy: str) -> dict[str, Any]:
    decisions = [row["decisions"][strategy] for row in rows]
    errors = [row for row in rows if row["label"] == "ERROR"]
    correct = [row for row in rows if row["label"] == "CORRECT"]
    labelled_accepts = [row for row in rows if row["label"] in {"ERROR", "CORRECT"} and row["decisions"][strategy] == "ACCEPT"]
    accepted = decisions.count("ACCEPT")
    rejected = decisions.count("REJECT")
    abstained = decisions.count("ABSTAIN")
    false_certifications = sum(row["decisions"][strategy] == "ACCEPT" for row in errors)
    detected = sum(row["decisions"][strategy] == "REJECT" for row in errors)
    false_rejects = sum(row["decisions"][strategy] == "REJECT" for row in correct)
    correct_abstains = sum(row["decisions"][strategy] == "ABSTAIN" for row in correct)
    return {
        "n": len(rows),
        "counts": {"accepted": accepted, "rejected": rejected, "abstained": abstained},
        "error_opportunities": len(errors),
        "correct_opportunities": len(correct),
        "unresolved": sum(row["label"] == "UNRESOLVED" for row in rows),
        "specification_false_certification_rate": _measure(false_certifications, len(errors)),
        "error_detection_rate": _measure(detected, len(errors)),
        "acceptance_coverage": _measure(accepted, len(rows)),
        "decision_coverage": _measure(accepted + rejected, len(rows)),
        "selective_risk": _measure(false_certifications, len(labelled_accepts)),
        "false_rejection_rate": _measure(false_rejects, len(correct)),
        "correct_specification_abstention_rate": _measure(correct_abstains, len(correct)),
    }


def _paired(rows: list[dict[str, Any]], baseline: str, tested: str) -> dict[str, Any]:
    errors = [row for row in rows if row["label"] == "ERROR"]
    b = sum(row["decisions"][baseline] == "ACCEPT" and row["decisions"][tested] != "ACCEPT" for row in errors)
    c = sum(row["decisions"][baseline] != "ACCEPT" and row["decisions"][tested] == "ACCEPT" for row in errors)
    return {"baseline_only_false_certification": b, "tested_only_false_certification": c, "discordant": b + c, "mcnemar_exact_p": _mcnemar_exact(b, c)}


def analyse(evidence: Path, analysis: Path) -> dict[str, Any]:
    if analysis.exists():
        raise FileExistsError(f"refusing to overwrite {analysis}")
    analysis.mkdir(parents=True)
    public = {row["problem_id"]: row for row in json.loads((evidence / "challenge_public.json").read_text())}
    references = {row["problem_id"]: row for row in json.loads((evidence / "automatic_references.json").read_text())}
    candidates = {row["problem_id"]: row for row in json.loads((evidence / "challenge_candidates.json").read_text())}
    challenge_rows: list[dict[str, Any]] = []
    for case_id, candidate_row in candidates.items():
        candidate = FormalSpecification.from_dict(candidate_row["candidate"])
        solved = solve_z3(candidate)
        axiom = _decision(public[case_id]["problem_text"], candidate, solved.count)
        cheap = cheap_rule_decision(public[case_id]["problem_text"], candidate.to_dict(), solved.status)
        challenge_rows.append({
            "case_id": case_id,
            "mechanism": candidate_row["mechanism"],
            "label": references[case_id]["expected_label"],
            "candidate_origin": candidate_row["candidate_origin"],
            "decisions": {
                "ACCEPT_ALL_VALID": "ACCEPT",
                "SOLVER_ONLY": "ACCEPT" if solved.status == "COMPLETE" else "ABSTAIN",
                "CHEAP_RULE_ABLATION": cheap["decision"],
                "AXIOM_X_B2_1": axiom["decision"],
            },
            "axiom_reason": axiom["reason"],
        })
    strategies = ("ACCEPT_ALL_VALID", "SOLVER_ONLY", "CHEAP_RULE_ABLATION", "AXIOM_X_B2_1")
    challenge_results = {
        "schema": "axiom-x-v4-challenge-results-v1",
        "origin": "PROSPECTIVE_CONTROLLED_PERTURBATIONS",
        "strategies": {strategy: _metrics(challenge_rows, strategy) for strategy in strategies},
        "paired_accept_all_vs_axiom": _paired(challenge_rows, "ACCEPT_ALL_VALID", "AXIOM_X_B2_1"),
        "mechanisms": {
            mechanism: {strategy: _metrics([row for row in challenge_rows if row["mechanism"] == mechanism], strategy) for strategy in strategies}
            for mechanism in MECHANISMS
        },
    }

    model_rows_raw = [json.loads(line) for line in (evidence / "natural_model_predictions.jsonl").read_text().splitlines() if line]
    model_rows: list[dict[str, Any]] = []
    for row in model_rows_raw:
        case_id = row["case_id"]
        if row["generation"] is None:
            label = "UNKNOWN"
            decisions = {strategy: "ABSTAIN" for strategy in strategies}
            axiom_reason = "GENERATION_FAILED"
        else:
            candidate = FormalSpecification.from_dict(row["generation"]["specification"])
            reference = FormalSpecification.from_dict(references[case_id]["specification"])
            relation = compare_specifications_by_name(candidate, reference).status
            label = {"EQUIVALENT": "CORRECT", "DIFFERENT": "ERROR", "INCONCLUSIVE": "UNKNOWN"}[relation]
            axiom = _decision(public[case_id]["problem_text"], candidate, row["solver"]["count"])
            cheap = cheap_rule_decision(public[case_id]["problem_text"], candidate.to_dict(), row["solver"]["status"])
            decisions = {
                "ACCEPT_ALL_VALID": "ACCEPT",
                "SOLVER_ONLY": "ACCEPT" if row["solver"]["status"] == "COMPLETE" else "ABSTAIN",
                "CHEAP_RULE_ABLATION": cheap["decision"],
                "AXIOM_X_B2_1": axiom["decision"],
            }
            axiom_reason = axiom["reason"]
        model_rows.append({
            "case_id": case_id,
            "source_group": case_id,
            "model": row["model"],
            "mechanism_family": public[case_id]["category"],
            "label": label,
            "candidate_origin": "NATURAL_MODEL_GENERATED",
            "valid_output": row["generation"] is not None,
            "decisions": decisions,
            "axiom_reason": axiom_reason,
        })
    models = json.loads(PROTOCOL.read_text())["model_order"]
    model_results = {
        "schema": "axiom-x-v4-natural-model-results-v1",
        "origin": "PROSPECTIVE_LOCAL_MODEL_GENERATION",
        "shared_task_warning": "Models share 48 source tasks; pooled model rows are not independent confirmation samples.",
        "models": {
            model: {
                "valid_outputs": sum(row["model"] == model and row["valid_output"] for row in model_rows),
                "invalid_outputs": sum(row["model"] == model and not row["valid_output"] for row in model_rows),
                "strategies": {strategy: _metrics([row for row in model_rows if row["model"] == model], strategy) for strategy in strategies},
                "paired_accept_all_vs_axiom": _paired([row for row in model_rows if row["model"] == model], "ACCEPT_ALL_VALID", "AXIOM_X_B2_1"),
            }
            for model in models
        },
    }
    _write_new(analysis / "challenge_results.json", challenge_results)
    _write_new(analysis / "model_results.json", model_results)
    _write_new(analysis / "challenge_rows.json", challenge_rows)
    _write_new(analysis / "model_rows.json", model_rows)
    manifest = {"schema": "axiom-x-v4-analysis-manifest-v1", "files": {path.name: _sha256(path) for path in sorted(analysis.iterdir())}}
    _write_new(analysis / "manifest.json", manifest)
    return {
        "challenge_error_opportunities": challenge_results["strategies"]["AXIOM_X_B2_1"]["error_opportunities"],
        "challenge_axiom_false_certifications": challenge_results["strategies"]["AXIOM_X_B2_1"]["specification_false_certification_rate"]["numerator"],
        "models": {model: model_results["models"][model]["strategies"]["AXIOM_X_B2_1"] for model in models},
    }


def verify(evidence: Path, analysis: Path) -> dict[str, Any]:
    dataset_manifest = json.loads((evidence / "dataset_manifest.json").read_text())
    dataset_ok = all(_sha256(evidence / name) == digest for name, digest in dataset_manifest["files"].items())
    prediction_manifest = json.loads((evidence / "natural_model_prediction_manifest.json").read_text())
    predictions_ok = _sha256(evidence / "natural_model_predictions.jsonl") == prediction_manifest["sha256"]
    analysis_manifest = json.loads((analysis / "manifest.json").read_text())
    analysis_ok = all(_sha256(analysis / name) == digest for name, digest in analysis_manifest["files"].items())
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        regenerated_evidence = temp_root / "evidence"
        regenerated_dataset = freeze(regenerated_evidence)
        dataset_regenerated = regenerated_dataset["files"] == dataset_manifest["files"]
        for name in ("natural_model_predictions.jsonl", "natural_model_prediction_manifest.json"):
            (regenerated_evidence / name).write_bytes((evidence / name).read_bytes())
        regenerated_analysis = temp_root / "analysis"
        analyse(regenerated_evidence, regenerated_analysis)
        analysis_regenerated = all(_sha256(regenerated_analysis / name) == digest for name, digest in analysis_manifest["files"].items())
    return {
        "status": "VERIFIED" if all((dataset_ok, predictions_ok, analysis_ok, dataset_regenerated, analysis_regenerated)) else "FAILED",
        "dataset_hashes_ok": dataset_ok,
        "prediction_hash_ok": predictions_ok,
        "analysis_hashes_ok": analysis_ok,
        "dataset_regeneration_byte_identical": dataset_regenerated,
        "analysis_regeneration_byte_identical": analysis_regenerated,
        "model_generation_rerun": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("freeze", "run-models", "analyse", "verify"))
    parser.add_argument("--evidence", type=Path, default=EVIDENCE)
    parser.add_argument("--analysis", type=Path, default=ANALYSIS)
    args = parser.parse_args()
    if args.command == "freeze":
        result = freeze(args.evidence)
    elif args.command == "run-models":
        result = run_models(args.evidence)
    elif args.command == "analyse":
        result = analyse(args.evidence, args.analysis)
    else:
        result = verify(args.evidence, args.analysis)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
