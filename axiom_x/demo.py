from __future__ import annotations

import json
from typing import Any

from .audit import audit
from .providers import FixtureProvider, generate_isolated


def digit_spec(problem_id: str, constraints: list[dict[str, Any]], source: str) -> dict[str, Any]:
    return {
        "problem_id": problem_id,
        "variables": [
            {"name": "d0", "domain": [0, 1, 2]},
            {"name": "d1", "domain": [0, 1, 2]},
        ],
        "constraints": constraints,
        "target": "count_solutions",
        "source": source,
        "generation_id": "replaced-by-provider",
        "verification_status": "UNVERIFIED",
    }


def main() -> None:
    cases = {
        "correct": (
            digit_spec("correct", [{"kind": "not_equal", "variable": "d0", "value": 0}, {"kind": "all_different", "variables": ["d0", "d1"]}], "fixture-primary"),
            digit_spec("correct", [{"kind": "not_equal", "variable": "d0", "value": 0}, {"kind": "all_different", "variables": ["d0", "d1"]}], "fixture-secondary"),
            4,
        ),
        "secondary-detects-omission": (
            digit_spec("secondary-detects-omission", [{"kind": "all_different", "variables": ["d0", "d1"]}], "fixture-primary"),
            digit_spec("secondary-detects-omission", [{"kind": "not_equal", "variable": "d0", "value": 0}, {"kind": "all_different", "variables": ["d0", "d1"]}], "fixture-secondary"),
            6,
        ),
    }
    output: list[dict[str, Any]] = []
    for case_id, (primary_raw, secondary_raw, answer) in cases.items():
        primary, secondary = generate_isolated(
            case_id, "deterministic synthetic fixture",
            FixtureProvider("primary", {case_id: primary_raw}),
            FixtureProvider("secondary", {case_id: secondary_raw}),
        )
        result = audit(primary.specification, secondary.specification, proposed_answer=answer)
        output.append({
            "case_id": case_id, "decision": result.decision,
            "reason_code": result.reason_code, "evidence": result.evidence,
        })
    print(json.dumps({
        "status": "DETERMINISTIC_SYNTHETIC_DEMO",
        "scientific_claim": "mechanism check only; no real-LLM reliability claim",
        "results": output,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
