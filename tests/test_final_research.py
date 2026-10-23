from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from axiom_x.v2_1 import _review_receipt_complete


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_complete_human_receipt_requires_hash_matched_ledgers(tmp_path: Path) -> None:
    stage1 = tmp_path / "stage1.csv"
    stage2 = tmp_path / "stage2.csv"
    disagreements = tmp_path / "disagreements.csv"
    stage1_fields = [
        "anonymous_id", "problem_text", "reviewer_id", "review_date",
        "independence_disclosure", "independent_interpretation", "independent_derivation",
        "independent_result", "ambiguity_or_uncertainty", "confidence",
    ]
    with stage1.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=stage1_fields)
        writer.writeheader()
        for index in range(1, 41):
            writer.writerow({field: (
                f"Q{index:03d}" if field == "anonymous_id" else
                "reviewer-1" if field == "reviewer_id" else "completed"
            ) for field in stage1_fields})
    stage1_hash = _digest(stage1)
    stage2_fields = [
        "anonymous_id", "stage1_ledger_sha256", "reviewer_id", "review_date",
        "candidate_interpretation_faithful", "candidate_result_correct",
        "enumeration_correct", "ambiguity_found", "agreement_with_stage1", "confidence",
        "reason", "adjudication_required",
    ]
    with stage2.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=stage2_fields)
        writer.writeheader()
        for index in range(1, 41):
            writer.writerow({field: (
                f"Q{index:03d}" if field == "anonymous_id" else
                stage1_hash if field == "stage1_ledger_sha256" else
                "reviewer-1" if field == "reviewer_id" else "completed"
            ) for field in stage2_fields})
    disagreements.write_text("anonymous_id\n" + "".join(f"Q{index:03d}\n" for index in range(1, 41)))
    receipt = {
        "schema": "axiom-x-v2-1-human-gold-receipt-v1",
        "status": "COMPLETE",
        "independent_human_review": True,
        "row_count": 40,
        "public_dataset_sha256": "a" * 64,
        "candidate_gold_sha256": "b" * 64,
        "reviewers": [{
            "reviewer_id": "reviewer-1",
            "independence_disclosure": True,
            "stage1_locked_before_stage2": True,
            "stage1_ledger_path": stage1.name,
            "stage1_ledger_sha256": _digest(stage1),
            "stage2_ledger_path": stage2.name,
            "stage2_ledger_sha256": _digest(stage2),
        }],
        "disagreement_ledger_path": disagreements.name,
        "disagreement_ledger_sha256": _digest(disagreements),
        "unresolved_disagreements": 0,
        "completion_date": "2026-10-23",
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt))
    assert _review_receipt_complete(
        receipt_path,
        expected_dataset_sha256="a" * 64,
        expected_gold_sha256="b" * 64,
    )[0] is True
    assert _review_receipt_complete(
        receipt_path,
        expected_dataset_sha256="c" * 64,
        expected_gold_sha256="b" * 64,
    )[0] is False
    stage1.write_text("tampered")
    assert _review_receipt_complete(receipt_path)[0] is False
