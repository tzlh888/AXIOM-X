from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

from .audit import audit_v2_1
from .providers import GenerationFailure, GenerationRecord, OpenAICompatibleProvider, Provider
from .v2 import DECISION_MAP, run_case, validate_public_cases


ROOT = Path(__file__).parents[1]
CONFIG_SCHEMA = "axiom-x-v2-1-run-config-v1"
FREEZE_SCHEMA = "axiom-x-v2-1-freeze-v1"
APPROVED_API_URL = "https://api.openai.com/v1/chat/completions"


def _abstain_evidence(reason: str) -> dict[str, Any]:
    return {
        "triggered_checks": [],
        "counterexample": None,
        "specification_comparison": None,
        "solver_status": None,
        "uncertainty_reason": reason,
        "evidence_provenance": ["generation_pipeline"],
    }


def run_case_v2_1(
    public_case: dict[str, Any],
    primary: GenerationRecord | None,
    secondary: GenerationRecord | None,
    *,
    primary_error: str | None = None,
    secondary_error: str | None = None,
    primary_failure: dict[str, Any] | None = None,
    secondary_failure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = run_case(
        public_case,
        primary,
        secondary,
        primary_error=primary_error,
        secondary_error=secondary_error,
        primary_failure=primary_failure,
        secondary_failure=secondary_failure,
    )
    if primary is None:
        b2_1 = {
            "decision": "ABSTAIN",
            "reason_code": "PRIMARY_GENERATION_FAILED",
            "evidence": _abstain_evidence(primary_error or "Primary generation failed"),
        }
    else:
        result = audit_v2_1(
            public_case["problem_text"],
            primary.specification,
            secondary.specification if secondary else None,
            proposed_answer=row["answer"],
        )
        b2_1 = {
            "decision": DECISION_MAP[result.decision],
            "reason_code": result.reason_code,
            "evidence": result.evidence,
        }
        if secondary_error:
            b2_1["evidence"]["secondary_generation_error"] = secondary_error
    row["strategies"]["B2_1"] = b2_1
    row["experiment_variant"] = "AXIOM-X-V2.1"
    return row


def predict_cases_v2_1(
    public_cases: list[dict[str, Any]], primary: Provider, secondary: Provider
) -> list[dict[str, Any]]:
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
        except Exception as exc:
            primary_error = f"{type(exc).__name__}: {exc}"
        try:
            secondary_record = secondary.generate(case["problem_id"], case["problem_text"])
        except GenerationFailure as exc:
            secondary_error, secondary_failure = f"{type(exc).__name__}: {exc}", exc.record
        except Exception as exc:
            secondary_error = f"{type(exc).__name__}: {exc}"
        predictions.append(run_case_v2_1(
            case,
            primary_record,
            secondary_record,
            primary_error=primary_error,
            secondary_error=secondary_error,
            primary_failure=primary_failure,
            secondary_failure=secondary_failure,
        ))
    return predictions


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _completed_ledger(
    path: Path,
    *,
    stage: str,
    reviewer_id: str,
    expected_row_count: int,
    stage1_sha256: str | None = None,
) -> tuple[bool, str]:
    required = {
        "stage1": {
            "anonymous_id", "problem_text", "reviewer_id", "review_date",
            "independence_disclosure", "independent_interpretation",
            "independent_derivation", "independent_result",
            "ambiguity_or_uncertainty", "confidence",
        },
        "stage2": {
            "anonymous_id", "stage1_ledger_sha256", "reviewer_id", "review_date",
            "candidate_interpretation_faithful", "candidate_result_correct",
            "enumeration_correct", "ambiguity_found", "agreement_with_stage1",
            "confidence", "reason", "adjudication_required",
        },
    }[stage]
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not required <= set(reader.fieldnames):
                return False, f"{stage} ledger lacks required columns"
            rows = list(reader)
        if len(rows) != expected_row_count:
            return False, f"{stage} ledger has {len(rows)} rows, expected {expected_row_count}"
        expected_ids = {f"Q{index:03d}" for index in range(1, expected_row_count + 1)}
        if {row.get("anonymous_id", "").strip() for row in rows} != expected_ids:
            return False, f"{stage} ledger anonymous IDs are incomplete or duplicated"
        for row in rows:
            if any(not str(row.get(field, "")).strip() for field in required):
                return False, f"{stage} ledger contains incomplete required fields"
            if row["reviewer_id"].strip() != reviewer_id:
                return False, f"{stage} ledger reviewer ID mismatch"
            if stage == "stage2" and row["stage1_ledger_sha256"].strip() != stage1_sha256:
                return False, "stage2 ledger is not bound to the frozen stage1 ledger"
        return True, f"{len(rows)} complete rows"
    except (OSError, csv.Error, UnicodeError) as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _review_receipt_complete(
    path: Path,
    *,
    expected_dataset_sha256: str | None = None,
    expected_gold_sha256: str | None = None,
    expected_row_count: int = 40,
) -> tuple[bool, str]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if receipt.get("schema") != "axiom-x-v2-1-human-gold-receipt-v1":
            return False, "invalid receipt schema"
        if receipt.get("status") != "COMPLETE" or receipt.get("independent_human_review") is not True:
            return False, "receipt is not COMPLETE independent human review"
        if receipt.get("row_count") != expected_row_count:
            return False, "receipt row count does not match the formal dataset"
        public_hash = receipt.get("public_dataset_sha256")
        gold_hash = receipt.get("candidate_gold_sha256")
        if not isinstance(public_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", public_hash):
            return False, "receipt lacks a valid public dataset hash"
        if not isinstance(gold_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", gold_hash):
            return False, "receipt lacks a valid candidate Gold hash"
        if expected_dataset_sha256 is not None and public_hash != expected_dataset_sha256:
            return False, "receipt is for a different public dataset"
        if expected_gold_sha256 is not None and gold_hash != expected_gold_sha256:
            return False, "receipt is for a different candidate Gold file"
        reviewers = receipt.get("reviewers")
        if not isinstance(reviewers, list) or not reviewers:
            return False, "no reviewer ledger records"
        reviewer_ids: set[str] = set()
        base = path.parent.resolve()
        for reviewer in reviewers:
            if not isinstance(reviewer, dict):
                return False, "invalid reviewer record"
            reviewer_id = reviewer.get("reviewer_id")
            if not isinstance(reviewer_id, str) or not reviewer_id.strip() or reviewer_id in reviewer_ids:
                return False, "reviewer IDs must be non-empty and unique"
            reviewer_ids.add(reviewer_id)
            if reviewer.get("independence_disclosure") is not True:
                return False, f"reviewer {reviewer_id} lacks independence disclosure"
            if reviewer.get("stage1_locked_before_stage2") is not True:
                return False, f"reviewer {reviewer_id} did not attest stage ordering"
            ledgers: dict[str, tuple[Path, str]] = {}
            for stage in ("stage1", "stage2"):
                relative = reviewer.get(f"{stage}_ledger_path")
                expected = reviewer.get(f"{stage}_ledger_sha256")
                if not isinstance(relative, str) or not relative or not isinstance(expected, str):
                    return False, f"reviewer {reviewer_id} lacks {stage} ledger provenance"
                ledger = (base / relative).resolve()
                if not ledger.is_relative_to(base) or not ledger.is_file() or _sha256(ledger) != expected:
                    return False, f"reviewer {reviewer_id} {stage} ledger hash mismatch"
                ledgers[stage] = (ledger, expected)
            stage1_valid, stage1_detail = _completed_ledger(
                ledgers["stage1"][0],
                stage="stage1",
                reviewer_id=reviewer_id,
                expected_row_count=expected_row_count,
            )
            if not stage1_valid:
                return False, f"reviewer {reviewer_id}: {stage1_detail}"
            stage2_valid, stage2_detail = _completed_ledger(
                ledgers["stage2"][0],
                stage="stage2",
                reviewer_id=reviewer_id,
                expected_row_count=expected_row_count,
                stage1_sha256=ledgers["stage1"][1],
            )
            if not stage2_valid:
                return False, f"reviewer {reviewer_id}: {stage2_detail}"
        disagreement_relative = receipt.get("disagreement_ledger_path")
        disagreement_hash = receipt.get("disagreement_ledger_sha256")
        if not isinstance(disagreement_relative, str) or not isinstance(disagreement_hash, str):
            return False, "missing disagreement ledger provenance"
        disagreement = (base / disagreement_relative).resolve()
        if not disagreement.is_relative_to(base) or not disagreement.is_file():
            return False, "disagreement ledger unavailable"
        if _sha256(disagreement) != disagreement_hash:
            return False, "disagreement ledger hash mismatch"
        with disagreement.open(encoding="utf-8", newline="") as handle:
            disagreement_rows = list(csv.DictReader(handle))
        expected_ids = {f"Q{index:03d}" for index in range(1, expected_row_count + 1)}
        if (
            len(disagreement_rows) != expected_row_count
            or {row.get("anonymous_id", "").strip() for row in disagreement_rows} != expected_ids
        ):
            return False, "disagreement ledger rows do not match the formal dataset"
        if receipt.get("unresolved_disagreements") != 0:
            return False, "unresolved disagreements remain"
        if not isinstance(receipt.get("completion_date"), str) or not receipt["completion_date"].strip():
            return False, "missing completion date"
        return True, f"{len(reviewers)} reviewer record(s), all ledger hashes verified"
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _heldout_lock_complete(dataset: Path) -> tuple[bool, str]:
    lock_path = dataset.parent / "LOCK.json"
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        valid = (
            lock.get("schema") == "axiom-x-v2-1-heldout-lock-v1"
            and lock.get("status") == "FROZEN_PUBLIC_ONLY_PENDING_GOLD"
            and lock.get("dataset_sha256") == _sha256(dataset)
            and lock.get("gold_included") is False
            and isinstance(lock.get("custodian_id"), str)
            and bool(lock.get("custodian_id", "").strip())
        )
        return valid, (
            f"lock={lock_path.name}, count={lock.get('row_count')}, custodian={lock.get('custodian_id')}"
            if valid else "lock fields/hash are invalid"
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _cost_upper_bound(
    public_cases: list[dict[str, Any]], config: dict[str, Any], primary_prompt: str, secondary_prompt: str
) -> float:
    input_bytes = 0
    for case in public_cases:
        user_prompt = f"problem_id={case['problem_id']}\nproblem={case['problem_text']}"
        input_bytes += len((primary_prompt + "\n" + user_prompt).encode())
        input_bytes += len((secondary_prompt + "\n" + user_prompt).encode())
    calls = 2 * len(public_cases) * (1 + int(config["max_retries"]))
    input_token_upper_bound = input_bytes * (1 + int(config["max_retries"])) + 64 * calls
    maximum_output_tokens = calls * int(config["max_completion_tokens"])
    return (
        input_token_upper_bound * float(config["input_price_usd_per_million"])
        + maximum_output_tokens * float(config["output_price_usd_per_million"])
    ) / 1_000_000


def readiness_checks(
    *,
    dataset: Path,
    config: dict[str, Any],
    mode: str,
    review_receipt: Path | None,
    environ: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    environ = os.environ if environ is None else environ
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": passed, "detail": detail})

    add("config_schema", config.get("schema") == CONFIG_SCHEMA, str(config.get("schema")))
    add("config_frozen", config.get("status") == "FROZEN_FOR_RUN", str(config.get("status")))
    add("api_key", bool(environ.get("OPENAI_API_KEY")), "present" if environ.get("OPENAI_API_KEY") else "missing")
    add("mode", mode in {"interface-smoke", "development", "heldout"}, mode)
    add("api_url", config.get("api_url") == APPROVED_API_URL, str(config.get("api_url")))
    add("service_tier", config.get("service_tier") == "default", str(config.get("service_tier")))
    for key in ("primary_model", "secondary_model"):
        add(key, isinstance(config.get(key), str) and bool(config.get(key, "").strip()), str(config.get(key)))
    add(
        "validated_response_mode",
        config.get("response_mode") == "json_object" and (
            mode == "interface-smoke" or config.get("development_interface_validated") is True
        ),
        f"mode={config.get('response_mode')}, dev_validated={config.get('development_interface_validated')}",
    )
    add("retry_limit", config.get("max_retries") in {0, 1}, str(config.get("max_retries")))
    maximum_tokens = config.get("max_completion_tokens")
    add("max_completion_tokens", type(maximum_tokens) is int and maximum_tokens > 0, str(maximum_tokens))
    maximum_cost = config.get("max_cost_usd")
    add(
        "cost_cap",
        isinstance(maximum_cost, (int, float)) and 0 < maximum_cost <= 10,
        str(maximum_cost),
    )
    for key in ("input_price_usd_per_million", "output_price_usd_per_million"):
        price = config.get(key)
        add(key, isinstance(price, (int, float)) and price > 0, str(price))
    add(
        "pricing_source",
        isinstance(config.get("pricing_source"), str) and config.get("pricing_source", "").startswith("https://"),
        str(config.get("pricing_source")),
    )
    add(
        "pricing_checked_on",
        isinstance(config.get("pricing_checked_on"), str) and len(config.get("pricing_checked_on", "")) == 10,
        str(config.get("pricing_checked_on")),
    )
    primary_prompt = ROOT / "prompts/v2_primary.txt"
    secondary_prompt = ROOT / "prompts/v2_secondary.txt"
    add(
        "primary_prompt_hash",
        config.get("primary_prompt_sha256") == _sha256(primary_prompt),
        _sha256(primary_prompt),
    )
    add(
        "secondary_prompt_hash",
        config.get("secondary_prompt_sha256") == _sha256(secondary_prompt),
        _sha256(secondary_prompt),
    )
    try:
        public_cases = json.loads(dataset.read_text(encoding="utf-8"))
        validate_public_cases(public_cases)
        dataset_valid = True
        dataset_detail = f"{len(public_cases)} public rows"
    except Exception as exc:
        public_cases = []
        dataset_valid = False
        dataset_detail = f"{type(exc).__name__}: {exc}"
    add("public_dataset", dataset_valid, dataset_detail)
    if mode == "interface-smoke":
        add(
            "smoke_dataset_size",
            dataset_valid and len(public_cases) == 1,
            f"{len(public_cases)} rows; exactly one is required",
        )
    if dataset_valid and all(
        isinstance(config.get(key), (int, float)) and config.get(key, 0) > 0
        for key in ("max_completion_tokens", "input_price_usd_per_million", "output_price_usd_per_million")
    ):
        estimate = _cost_upper_bound(
            public_cases,
            config,
            primary_prompt.read_text(encoding="utf-8"),
            secondary_prompt.read_text(encoding="utf-8"),
        )
        add("worst_case_cost", isinstance(maximum_cost, (int, float)) and estimate <= maximum_cost, f"USD {estimate:.6f}")
    else:
        add("worst_case_cost", False, "cannot calculate until token and price fields are valid")
    if mode == "heldout":
        add("formal_heldout_authorized", config.get("formal_heldout_authorized") is True, str(config.get("formal_heldout_authorized")))
        add("pristine_v2_1_heldout", config.get("pristine_v2_1_heldout") is True, str(config.get("pristine_v2_1_heldout")))
        dataset_hash = _sha256(dataset) if dataset.exists() and dataset.is_file() else "unavailable"
        add("heldout_dataset_hash", dataset_valid and config.get("dataset_sha256") == dataset_hash, dataset_hash)
        gold_hash = config.get("gold_sha256")
        gold_hash_valid = isinstance(gold_hash, str) and bool(re.fullmatch(r"[0-9a-f]{64}", gold_hash))
        add("heldout_gold_hash", gold_hash_valid, "frozen" if gold_hash_valid else "missing/invalid")
        lock_complete, lock_detail = _heldout_lock_complete(dataset) if dataset_valid else (False, "invalid dataset")
        add("independent_heldout_lock", lock_complete, lock_detail)
        complete, detail = (
            _review_receipt_complete(
                review_receipt,
                expected_dataset_sha256=dataset_hash,
                expected_gold_sha256=gold_hash,
                expected_row_count=len(public_cases),
            )
            if review_receipt and review_receipt.exists() else (False, "missing receipt")
        )
        add("independent_human_gold", complete, detail)
    return checks


def require_ready(checks: list[dict[str, Any]]) -> None:
    failed = [item for item in checks if not item["passed"]]
    if failed:
        summary = "; ".join(f"{item['check']}: {item['detail']}" for item in failed)
        raise RuntimeError(f"V2.1 experiment blocked: {summary}")


def _resource_summary(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    generations = [
        row.get(key) or row.get(f"{key}_failure")
        for row in rows for key in ("primary", "secondary")
        if row.get(key) or row.get(f"{key}_failure")
    ]
    input_tokens = sum(item.get("input_tokens") or 0 for item in generations)
    output_tokens = sum(item.get("output_tokens") or 0 for item in generations)
    latency_ms = sum(item.get("latency_ms") or 0 for item in generations)
    cost = (
        input_tokens * float(config["input_price_usd_per_million"])
        + output_tokens * float(config["output_price_usd_per_million"])
    ) / 1_000_000
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
        "actual_cost_usd": cost,
        "pricing_source": config["pricing_source"],
        "pricing_checked_on": config["pricing_checked_on"],
        "input_price_usd_per_million": config["input_price_usd_per_million"],
        "output_price_usd_per_million": config["output_price_usd_per_million"],
    }


def write_frozen_predictions_v2_1(
    rows: list[dict[str, Any]], output: Path, manifest: Path, config: dict[str, Any]
) -> dict[str, Any]:
    if output.exists() or manifest.exists():
        raise FileExistsError("refusing to overwrite frozen V2.1 experiment evidence")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    output.write_text(payload, encoding="utf-8")
    receipt = {
        "schema": FREEZE_SCHEMA,
        "prediction_file": output.name,
        "sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "row_count": len(rows),
        "variant": "B2_1",
        "models": {
            "primary": config["primary_model"],
            "secondary": config["secondary_model"],
        },
        "resource_use": _resource_summary(rows, config),
    }
    manifest.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Gold-blind AXIOM-X V2.1 prediction only")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--mode", choices=("interface-smoke", "development", "heldout"), required=True)
    parser.add_argument("--review-receipt", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.manifest.exists():
        raise FileExistsError("refusing to overwrite frozen V2.1 experiment evidence")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    checks = readiness_checks(
        dataset=args.dataset,
        config=config,
        mode=args.mode,
        review_receipt=args.review_receipt,
    )
    require_ready(checks)
    public_cases = json.loads(args.dataset.read_text(encoding="utf-8"))
    primary_prompt = (ROOT / "prompts/v2_primary.txt").read_text(encoding="utf-8")
    secondary_prompt = (ROOT / "prompts/v2_secondary.txt").read_text(encoding="utf-8")
    provider_options = {
        "api_url": config["api_url"],
        "max_retries": config["max_retries"],
        "max_completion_tokens": config["max_completion_tokens"],
        "service_tier": config["service_tier"],
    }
    rows = predict_cases_v2_1(
        public_cases,
        OpenAICompatibleProvider(model=config["primary_model"], system_prompt=primary_prompt, **provider_options),
        OpenAICompatibleProvider(model=config["secondary_model"], system_prompt=secondary_prompt, **provider_options),
    )
    resources = _resource_summary(rows, config)
    if resources["actual_cost_usd"] > config["max_cost_usd"]:
        raise RuntimeError(
            "V2.1 experiment cost cap exceeded; predictions remain in memory and were not written"
        )
    receipt = write_frozen_predictions_v2_1(rows, args.output, args.manifest, config)
    print(json.dumps({"status": "FROZEN_V2_1_PREDICTIONS", "checks": checks, "receipt": receipt}, indent=2))


if __name__ == "__main__":
    main()
