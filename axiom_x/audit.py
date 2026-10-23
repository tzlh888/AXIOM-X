from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .semantic_v2_1 import parse_public_problem
from .solver import (
    compare_specifications,
    compare_specifications_by_name,
    enumerate_specification,
    solve_z3,
)
from .spec import FormalSpecification, SpecificationError


@dataclass(frozen=True)
class AuditDecision:
    decision: str
    reason_code: str
    evidence: dict[str, object]


def _solution_digest(solutions: frozenset[tuple[int, ...]] | None) -> str | None:
    if solutions is None:
        return None
    payload = json.dumps(sorted(solutions), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def audit(
    primary: FormalSpecification,
    secondary: FormalSpecification,
    *,
    proposed_answer: int | None = None,
    timeout_ms: int = 5_000,
) -> AuditDecision:
    comparison = compare_specifications(primary, secondary, timeout_ms=timeout_ms)
    if comparison.status == "INCONCLUSIVE":
        return AuditDecision("INCONCLUSIVE", "UNCOMPARABLE_OR_TIMEOUT", {"reason": comparison.reason})
    if comparison.status == "DIFFERENT":
        return AuditDecision(
            "FAIL", "SPECIFICATION_SET_DIFFERENCE",
            {"counterexample": comparison.counterexample, "count_equal": comparison.count_equal},
        )
    primary_result = solve_z3(primary, timeout_ms=timeout_ms)
    if primary_result.status != "COMPLETE":
        return AuditDecision("INCONCLUSIVE", "SOLVER_NOT_COMPLETE", {"reason": primary_result.reason})
    reference_result = enumerate_specification(primary)
    if reference_result.status != "COMPLETE":
        return AuditDecision("INCONCLUSIVE", "REFERENCE_NOT_COMPLETE", {"reason": reference_result.reason})
    if primary_result.solutions != reference_result.solutions:
        return AuditDecision(
            "INCONCLUSIVE", "SOLVER_DISAGREEMENT",
            {"z3_count": primary_result.count, "python_count": reference_result.count},
        )
    if proposed_answer is not None and proposed_answer != primary_result.count:
        return AuditDecision(
            "FAIL", "ANSWER_COUNT_MISMATCH",
            {"proposed_answer": proposed_answer, "verified_count": primary_result.count},
        )
    return AuditDecision(
        "PASS", "DEFINED_CHECKS_PASSED",
        {
            "verified_count": primary_result.count,
            "solver_cross_check": "Python enumeration and Z3 solution sets agree",
            "claim_boundary": "No claim of natural-language semantic fidelity",
        },
    )


def audit_v2_1(
    problem_text: str,
    primary: FormalSpecification,
    secondary: FormalSpecification | None,
    *,
    proposed_answer: int | None = None,
    timeout_ms: int = 5_000,
) -> AuditDecision:
    """Evidence-driven B2.1: peer agreement is recorded but never establishes faithfulness."""
    primary_result = solve_z3(primary, timeout_ms=timeout_ms)
    secondary_result = solve_z3(secondary, timeout_ms=timeout_ms) if secondary is not None else None
    peer_comparison = (
        compare_specifications_by_name(primary, secondary, timeout_ms=timeout_ms)
        if secondary is not None else None
    )
    semantic_error: str | None = None
    try:
        semantic = parse_public_problem(primary.problem_id, problem_text)
    except (SpecificationError, ValueError) as exc:
        semantic = None
        semantic_error = f"invalid public-text semantics: {type(exc).__name__}: {exc}"
    evidence: dict[str, object] = {
        "triggered_checks": list(semantic.triggered_checks) if semantic else [],
        "counterexample": None,
        "specification_comparison": {
            "primary_secondary": {
                "status": peer_comparison.status if peer_comparison else "NOT_AVAILABLE",
                "count_equal": peer_comparison.count_equal if peer_comparison else None,
                "counterexample": peer_comparison.counterexample if peer_comparison else None,
                "reason": peer_comparison.reason if peer_comparison else "secondary generation unavailable",
                "role": "auxiliary evidence only",
            },
            "primary_public_text_semantics": None,
        },
        "solver_status": {
            "primary": primary_result.status,
            "secondary": secondary_result.status if secondary_result else "NOT_AVAILABLE",
        },
        "solver_output": {
            "primary": {
                "status": primary_result.status,
                "count": primary_result.count,
                "solution_set_sha256": _solution_digest(primary_result.solutions),
            },
            "secondary": {
                "status": secondary_result.status,
                "count": secondary_result.count,
                "solution_set_sha256": _solution_digest(secondary_result.solutions),
            } if secondary_result else {
                "status": "NOT_AVAILABLE", "count": None, "solution_set_sha256": None,
            },
            "python_cross_check": None,
        },
        "evidence_strength": {
            "primary_candidate": {
                "level": "MODEL_INFERRED",
                "scope": "candidate specification only; not evidence of faithfulness",
            },
            "secondary_candidate": {
                "level": "MODEL_INFERRED" if secondary is not None else "UNVERIFIED",
                "scope": "auxiliary candidate only; never assigns fault",
            },
            "public_text_semantic_extraction": {
                "level": "UNVERIFIED",
                "scope": "pending full match of the fixed deterministic grammar",
            },
            "primary_public_set_relation": {
                "level": "UNVERIFIED",
                "scope": "not compared yet",
            },
            "solver_cross_check": {
                "level": "UNVERIFIED",
                "scope": "not compared yet",
            },
            "overall_faithfulness_claim": {
                "level": "UNVERIFIED",
                "scope": "no unrestricted natural-language correctness claim",
            },
        },
        "uncertainty_reason": None,
        "evidence_provenance": [
            "public_problem_text",
            "primary_specification",
            "secondary_specification",
            "deterministic_semantic_parser_v2_1",
            "z3_symmetric_difference",
            "python_exhaustive_cross_check",
        ],
        "claim_boundary": "ACCEPT is bounded to the fixed parser grammar and finite-domain semantics; it is not a proof of unrestricted natural-language faithfulness.",
    }
    if primary_result.status != "COMPLETE":
        evidence["uncertainty_reason"] = primary_result.reason
        return AuditDecision("INCONCLUSIVE", "PRIMARY_SOLVER_NOT_COMPLETE", evidence)
    if semantic is None:
        evidence["uncertainty_reason"] = semantic_error
        return AuditDecision("INCONCLUSIVE", "SEMANTIC_EVIDENCE_INSUFFICIENT", evidence)
    if semantic.status != "COMPLETE" or semantic.specification is None:
        evidence["uncertainty_reason"] = semantic.reason
        return AuditDecision("INCONCLUSIVE", "SEMANTIC_EVIDENCE_INSUFFICIENT", evidence)
    evidence["evidence_strength"]["public_text_semantic_extraction"] = {
        "level": "DETERMINISTICALLY_CHECKED",
        "scope": "entire text matched one fixed controlled-language grammar; parser correctness is not formally proved",
    }
    semantic_comparison = compare_specifications_by_name(
        primary, semantic.specification, timeout_ms=timeout_ms
    )
    evidence["specification_comparison"]["primary_public_text_semantics"] = {
        "status": semantic_comparison.status,
        "count_equal": semantic_comparison.count_equal,
        "counterexample": semantic_comparison.counterexample,
        "reason": semantic_comparison.reason,
        "parser_status": semantic.status,
    }
    if semantic_comparison.status in {"EQUIVALENT", "DIFFERENT"}:
        evidence["evidence_strength"]["primary_public_set_relation"] = {
            "level": "FORMALLY_PROVEN",
            "scope": "finite solution-set relation under exact-name mapping, conditional on both formalizations",
        }
    if semantic_comparison.status == "INCONCLUSIVE":
        evidence["uncertainty_reason"] = semantic_comparison.reason
        return AuditDecision("INCONCLUSIVE", "SEMANTIC_MAPPING_OR_COMPARISON_UNPROVED", evidence)
    if semantic_comparison.status == "DIFFERENT":
        evidence["counterexample"] = semantic_comparison.counterexample
        evidence["evidence_strength"]["overall_faithfulness_claim"] = {
            "level": "DETERMINISTICALLY_CHECKED",
            "scope": "Primary contradicts the fixed grammar interpretation; this is not a proof for unrestricted English",
        }
        return AuditDecision("FAIL", "PRIMARY_PUBLIC_TEXT_SET_DIFFERENCE", evidence)
    reference_result = enumerate_specification(primary)
    if reference_result.status != "COMPLETE":
        evidence["uncertainty_reason"] = reference_result.reason
        return AuditDecision("INCONCLUSIVE", "REFERENCE_NOT_COMPLETE", evidence)
    if primary_result.solutions != reference_result.solutions:
        evidence["uncertainty_reason"] = "Z3 and Python solution sets disagree"
        return AuditDecision("INCONCLUSIVE", "SOLVER_DISAGREEMENT", evidence)
    evidence["solver_output"]["python_cross_check"] = {
        "status": reference_result.status,
        "count": reference_result.count,
        "solution_set_sha256": _solution_digest(reference_result.solutions),
    }
    evidence["evidence_strength"]["solver_cross_check"] = {
        "level": "DETERMINISTICALLY_CHECKED",
        "scope": "Python exhaustive enumeration matches the Z3-enumerated finite solution set",
    }
    if proposed_answer is not None and proposed_answer != primary_result.count:
        evidence["counterexample"] = {
            "proposed_answer": proposed_answer,
            "verified_count": primary_result.count,
        }
        return AuditDecision("FAIL", "ANSWER_COUNT_MISMATCH", evidence)
    evidence["evidence_strength"]["overall_faithfulness_claim"] = {
        "level": "DETERMINISTICALLY_CHECKED",
        "scope": "passed the fixed parser and formal checks; unrestricted natural-language faithfulness remains unproved",
    }
    return AuditDecision("PASS", "PRIMARY_PUBLIC_TEXT_EQUIVALENCE_PROVED", evidence)
