from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .audit import audit
from .providers import GenerationFailure, GenerationRecord, OpenAICompatibleProvider, Provider
from .solver import solve_z3


DECISION_MAP = {"PASS": "ACCEPT", "FAIL": "REJECT", "INCONCLUSIVE": "ABSTAIN"}
FORBIDDEN_PUBLIC_KEYS = {"answer", "gold", "label", "labels", "reference_specification", "specification"}


def validate_public_cases(public_cases: list[dict[str, Any]]) -> None:
    if not isinstance(public_cases, list) or not public_cases:
        raise ValueError("public dataset must be a non-empty list")
    required = {"problem_id", "problem_text"}
    ids: list[str] = []
    for case in public_cases:
        if not isinstance(case, dict) or not required <= set(case):
            raise ValueError("each public case requires problem_id and problem_text")
        forbidden = FORBIDDEN_PUBLIC_KEYS & {key.casefold() for key in case}
        if forbidden:
            raise ValueError(f"Gold-bearing public field blocked: {sorted(forbidden)}")
        ids.append(str(case["problem_id"]))
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate public problem IDs")


def _generation(record: GenerationRecord) -> dict[str, Any]:
    value = asdict(record)
    value["specification"] = record.specification.to_dict()
    return value


def _constraint_key(item: dict[str, Any]) -> str:
    return json.dumps(item, sort_keys=True, separators=(",", ":"))


def cheap_rule_decision(problem_text: str, specification: dict[str, Any], solver_status: str) -> dict[str, str]:
    if solver_status != "COMPLETE":
        return {"decision": "ABSTAIN", "reason_code": "PRIMARY_SOLVER_NOT_COMPLETE"}
    constraints = {_constraint_key(item) for item in specification["constraints"]}
    names = [item["name"] for item in specification["variables"]]
    lower = problem_text.casefold()
    if "all variables are distinct" in lower:
        required = _constraint_key({"kind": "all_different", "variables": names})
        if required not in constraints:
            return {"decision": "REJECT", "reason_code": "RULE_MISSING_ALL_DIFFERENT"}
    for name in names:
        if re.search(rf"\b{re.escape(name)} is nonzero\b", lower):
            required = _constraint_key({"kind": "not_equal", "variable": name, "value": 0})
            if required not in constraints:
                return {"decision": "REJECT", "reason_code": "RULE_MISSING_NONZERO"}
    return {"decision": "ACCEPT", "reason_code": "RULES_PASSED"}


def backtranslation(specification: dict[str, Any]) -> str:
    variables = ", ".join(item["name"] for item in specification["variables"])
    clauses = [
        f"{item['name']} in {{{','.join(map(str, item['domain']))}}}"
        for item in specification["variables"]
    ]
    for item in specification["constraints"]:
        kind = item["kind"]
        if kind == "all_different":
            clauses.append(f"distinct({','.join(item['variables'])})")
        elif kind in {"equal", "not_equal"}:
            op = "=" if kind == "equal" else "!="
            clauses.append(f"{item['variable']}{op}{item['value']}")
        elif kind in {"less_than", "less_equal"}:
            op = "<" if kind == "less_than" else "<="
            clauses.append(f"{item['left']}{op}{item['right']}")
        elif kind.startswith("sum_"):
            op = {"sum_equal": "=", "sum_at_least": ">=", "sum_at_most": "<="}[kind]
            clauses.append(f"sum({','.join(item['variables'])}){op}{item['value']}")
        elif kind.startswith("count_"):
            op = {"count_equal": "=", "count_at_least": ">=", "count_at_most": "<="}[kind]
            clauses.append(
                f"count({','.join(item['variables'])};value={item['value']}){op}{item['count']}"
            )
        elif kind == "number_mod":
            clauses.append(
                f"base{item['base']}({','.join(item['variables'])}) mod {item['modulus']}={item['remainder']}"
            )
    return f"Count assignments to {variables} satisfying " + "; ".join(clauses)


def backtranslation_decision(problem_text: str, specification: dict[str, Any], solver_status: str) -> dict[str, str]:
    if solver_status != "COMPLETE":
        return {"decision": "ABSTAIN", "reason_code": "PRIMARY_SOLVER_NOT_COMPLETE"}
    rules = cheap_rule_decision(problem_text, specification, solver_status)
    if rules["decision"] == "REJECT":
        return {"decision": "REJECT", "reason_code": "BACKTRANSLATION_SEMANTIC_MISMATCH"}
    rendered = backtranslation(specification)
    if not rendered:
        return {"decision": "ABSTAIN", "reason_code": "BACKTRANSLATION_EMPTY"}
    return {"decision": "ACCEPT", "reason_code": "BACKTRANSLATION_NO_MISMATCH"}


def run_case(
    public_case: dict[str, Any], primary: GenerationRecord | None,
    secondary: GenerationRecord | None, *, primary_error: str | None = None,
    secondary_error: str | None = None, primary_failure: dict[str, Any] | None = None,
    secondary_failure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case_id = str(public_case["problem_id"])
    base = {
        "case_id": case_id,
        "group_id": str(public_case.get("group_id", case_id)),
        "category": str(public_case.get("category", "unspecified")),
        "primary": _generation(primary) if primary else None,
        "secondary": _generation(secondary) if secondary else None,
        "primary_error": primary_error,
        "secondary_error": secondary_error,
        "primary_failure": primary_failure,
        "secondary_failure": secondary_failure,
    }
    if primary is None:
        base.update({
            "answer": None,
            "primary_solver": {"status": "NOT_RUN", "count": None, "reason": primary_error},
            "secondary_solver": {"status": "NOT_RUN", "count": None, "reason": secondary_error},
            "backtranslation": None,
            "strategies": {
                name: {"decision": "ABSTAIN", "reason_code": "PRIMARY_GENERATION_FAILED"}
                for name in ("B0", "B1", "B2", "B3")
            },
        })
        return base
    primary_solver = solve_z3(primary.specification)
    answer = primary_solver.count if primary_solver.status == "COMPLETE" else None
    b0 = {
        "decision": "ACCEPT" if primary_solver.status == "COMPLETE" else "ABSTAIN",
        "reason_code": "PRIMARY_Z3_COMPLETE" if primary_solver.status == "COMPLETE" else "PRIMARY_SOLVER_NOT_COMPLETE",
    }
    b1 = cheap_rule_decision(public_case["problem_text"], primary.specification.to_dict(), primary_solver.status)
    if secondary is None:
        secondary_solver = None
        b2 = {"decision": "ABSTAIN", "reason_code": "SECONDARY_GENERATION_FAILED"}
    else:
        secondary_solver = solve_z3(secondary.specification)
        result = audit(primary.specification, secondary.specification, proposed_answer=answer)
        b2 = {"decision": DECISION_MAP[result.decision], "reason_code": result.reason_code, "evidence": result.evidence}
    b3 = backtranslation_decision(
        public_case["problem_text"], primary.specification.to_dict(), primary_solver.status
    )
    base.update({
        "answer": answer,
        "primary_solver": {"status": primary_solver.status, "count": primary_solver.count, "reason": primary_solver.reason},
        "secondary_solver": (
            {"status": secondary_solver.status, "count": secondary_solver.count, "reason": secondary_solver.reason}
            if secondary_solver else {"status": "NOT_RUN", "count": None, "reason": secondary_error}
        ),
        "backtranslation": backtranslation(primary.specification.to_dict()),
        "strategies": {"B0": b0, "B1": b1, "B2": b2, "B3": b3},
    })
    return base


def predict_cases(public_cases: list[dict[str, Any]], primary: Provider, secondary: Provider) -> list[dict[str, Any]]:
    validate_public_cases(public_cases)
    predictions: list[dict[str, Any]] = []
    for case in public_cases:
        primary_record = secondary_record = None
        primary_error = secondary_error = None
        primary_failure = secondary_failure = None
        try:
            primary_record = primary.generate(case["problem_id"], case["problem_text"])
        except GenerationFailure as exc:
            primary_error, primary_failure = f"{type(exc).__name__}: {exc}", exc.record
        except Exception as exc:  # retain every failed formal sample
            primary_error = f"{type(exc).__name__}: {exc}"
        try:
            secondary_record = secondary.generate(case["problem_id"], case["problem_text"])
        except GenerationFailure as exc:
            secondary_error, secondary_failure = f"{type(exc).__name__}: {exc}", exc.record
        except Exception as exc:  # retain every failed formal sample
            secondary_error = f"{type(exc).__name__}: {exc}"
        predictions.append(run_case(case, primary_record, secondary_record,
                                    primary_error=primary_error, secondary_error=secondary_error,
                                    primary_failure=primary_failure,
                                    secondary_failure=secondary_failure))
    return predictions


def write_frozen_predictions(rows: list[dict[str, Any]], output: Path, manifest: Path) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    output.write_text(payload, encoding="utf-8")
    receipt = {
        "schema": "axiom-x-v2-freeze-v1",
        "prediction_file": output.name,
        "sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "row_count": len(rows),
    }
    manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Gold-blind AXIOM-X V2 prediction only")
    parser.add_argument("--dataset", type=Path, required=True, help="public JSON; must contain no Gold")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--primary-model", required=True)
    parser.add_argument("--secondary-model", required=True)
    parser.add_argument("--estimated-cost-usd", required=True, type=float)
    parser.add_argument("--max-cost-usd", type=float, default=10.0)
    args = parser.parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is unavailable; formal prediction is blocked")
    if args.estimated_cost_usd < 0 or args.estimated_cost_usd > args.max_cost_usd:
        raise RuntimeError("estimated API cost is invalid or exceeds the configured cap")
    if args.output.exists() or args.manifest.exists():
        raise FileExistsError("refusing to overwrite frozen experiment evidence")
    public_cases = json.loads(args.dataset.read_text(encoding="utf-8"))
    validate_public_cases(public_cases)
    primary_prompt = Path("prompts/v2_primary.txt").read_text(encoding="utf-8")
    secondary_prompt = Path("prompts/v2_secondary.txt").read_text(encoding="utf-8")
    rows = predict_cases(
        public_cases,
        OpenAICompatibleProvider(model=args.primary_model, system_prompt=primary_prompt),
        OpenAICompatibleProvider(model=args.secondary_model, system_prompt=secondary_prompt),
    )
    receipt = write_frozen_predictions(rows, args.output, args.manifest)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
