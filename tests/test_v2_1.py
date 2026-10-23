from __future__ import annotations

import inspect
import io
import json
import urllib.error
from pathlib import Path

import pytest

from axiom_x.audit import audit_v2_1
from axiom_x.providers import GenerationFailure, FixtureProvider, OpenAICompatibleProvider
from axiom_x.semantic_v2_1 import parse_public_problem
from axiom_x.solver import compare_specifications_by_name
from axiom_x.spec import FormalSpecification
from axiom_x.v2_1 import readiness_checks, require_ready, run_case_v2_1


ROOT = Path(__file__).parents[1]


def raw_spec(
    problem_id: str,
    variables: list[dict],
    constraints: list[dict],
    source: str = "v2.1-test",
) -> dict:
    return {
        "problem_id": problem_id,
        "variables": variables,
        "constraints": constraints,
        "target": "count_solutions",
        "source": source,
        "generation_id": "fixture-replaced",
        "verification_status": "UNVERIFIED",
    }


def record(name: str, problem_id: str, specification: dict):
    return FixtureProvider(name, {problem_id: specification}).generate(problem_id, "unused")


def decision(text: str, primary: dict, secondary: dict) -> dict:
    problem_id = primary["problem_id"]
    row = run_case_v2_1(
        {"problem_id": problem_id, "problem_text": text, "category": "v2.1-development"},
        record("primary", problem_id, primary),
        record("secondary", problem_id, secondary),
    )
    return row["strategies"]["B2_1"]


def test_b2_1_accepts_only_with_complete_public_text_equivalence() -> None:
    problem_id = "DEV21-A"
    text = (
        "Variables a, b, c each range over integers 0 through 4. All variables are distinct. "
        "Their sum is exactly 6. How many assignments satisfy all conditions?"
    )
    variables = [{"name": name, "domain": list(range(5))} for name in ("a", "b", "c")]
    correct = raw_spec(problem_id, variables, [
        {"kind": "all_different", "variables": ["a", "b", "c"]},
        {"kind": "sum_equal", "variables": ["a", "b", "c"], "value": 6},
    ])
    result = decision(text, correct, correct)
    assert result["decision"] == "ACCEPT"
    assert result["reason_code"] == "PRIMARY_PUBLIC_TEXT_EQUIVALENCE_PROVED"
    assert result["evidence"]["triggered_checks"] == ["VARIABLE_DOMAINS", "ALL_DIFFERENT", "SUM_EQUAL"]
    strengths = result["evidence"]["evidence_strength"]
    assert strengths["primary_public_set_relation"]["level"] == "FORMALLY_PROVEN"
    assert strengths["public_text_semantic_extraction"]["level"] == "DETERMINISTICALLY_CHECKED"
    assert strengths["overall_faithfulness_claim"]["level"] == "DETERMINISTICALLY_CHECKED"
    assert result["evidence"]["solver_output"]["primary"]["solution_set_sha256"]


def test_b2_1_does_not_blame_primary_for_wrong_secondary() -> None:
    problem_id = "DEV21-B"
    text = (
        "Variables x and y each range over integers 0 through 5. Require x to be nonzero. "
        "How many assignments are possible?"
    )
    variables = [{"name": name, "domain": list(range(6))} for name in ("x", "y")]
    correct = raw_spec(problem_id, variables, [{"kind": "not_equal", "variable": "x", "value": 0}])
    wrong = raw_spec(problem_id, variables, [])
    result = decision(text, correct, wrong)
    assert result["decision"] == "ACCEPT"
    assert result["evidence"]["specification_comparison"]["primary_secondary"]["status"] == "DIFFERENT"


def test_b2_1_secondary_failure_is_auxiliary_not_a_primary_failure() -> None:
    problem_id = "DEV21-B2"
    text = (
        "Variables x and y each range over integers 0 through 2. Require x < y. "
        "How many assignments are possible?"
    )
    correct = raw_spec(problem_id, [
        {"name": "x", "domain": [0, 1, 2]},
        {"name": "y", "domain": [0, 1, 2]},
    ], [{"kind": "less_than", "left": "x", "right": "y"}])
    row = run_case_v2_1(
        {"problem_id": problem_id, "problem_text": text, "category": "v2.1-development"},
        record("primary", problem_id, correct),
        None,
        secondary_error="transport failed",
    )
    result = row["strategies"]["B2_1"]
    assert result["decision"] == "ACCEPT"
    assert result["evidence"]["solver_status"]["secondary"] == "NOT_AVAILABLE"
    assert result["evidence"]["secondary_generation_error"] == "transport failed"


def test_b2_1_rejects_primary_error_and_common_omission() -> None:
    problem_id = "DEV21-C"
    text = (
        "Variables a, b, c each range over integers 0 through 5. All variables are distinct. "
        "How many assignments are possible?"
    )
    variables = [{"name": name, "domain": list(range(6))} for name in ("a", "b", "c")]
    correct = raw_spec(problem_id, variables, [{"kind": "all_different", "variables": ["a", "b", "c"]}])
    omitted = raw_spec(problem_id, variables, [])
    primary_wrong = decision(text, omitted, correct)
    common_wrong = decision(text, omitted, omitted)
    assert primary_wrong["decision"] == "REJECT"
    assert common_wrong["decision"] == "REJECT"
    assert common_wrong["reason_code"] == "PRIMARY_PUBLIC_TEXT_SET_DIFFERENCE"
    assert common_wrong["evidence"]["counterexample"] is not None


def test_b2_1_rejects_explicit_domain_error() -> None:
    problem_id = "DEV21-D"
    text = "Variable z ranges over integers 1 through 4 and z is nonzero. How many values are possible?"
    correct = raw_spec(problem_id, [{"name": "z", "domain": [1, 2, 3, 4]}], [
        {"kind": "not_equal", "variable": "z", "value": 0}
    ])
    wrong = raw_spec(problem_id, [{"name": "z", "domain": [1, 2, 3, 4, 5]}], [
        {"kind": "not_equal", "variable": "z", "value": 0}
    ])
    result = decision(text, wrong, correct)
    assert result["decision"] == "REJECT"
    assert result["evidence"]["counterexample"] == {"z": 5}


def test_b2_1_abstains_when_public_semantics_are_not_fully_parsed() -> None:
    problem_id = "DEV21-E"
    text = "Choose a pleasant pair of small numbers and count the acceptable outcomes."
    specification = raw_spec(problem_id, [
        {"name": "x", "domain": [0, 1]},
        {"name": "y", "domain": [0, 1]},
    ], [])
    result = decision(text, specification, specification)
    assert result["decision"] == "ABSTAIN"
    assert result["reason_code"] == "SEMANTIC_EVIDENCE_INSUFFICIENT"


def test_b2_1_abstains_on_invalid_matched_domain_instead_of_crashing() -> None:
    problem_id = "DEV21-E2"
    text = (
        "Variables x and y each range over integers 3 through 1. Require x < y. "
        "How many assignments are possible?"
    )
    specification = raw_spec(problem_id, [
        {"name": "x", "domain": [1, 2, 3]},
        {"name": "y", "domain": [1, 2, 3]},
    ], [{"kind": "less_than", "left": "x", "right": "y"}])
    result = decision(text, specification, specification)
    assert result["decision"] == "ABSTAIN"
    assert result["reason_code"] == "SEMANTIC_EVIDENCE_INSUFFICIENT"
    assert "invalid public-text semantics" in result["evidence"]["uncertainty_reason"]


def test_exact_name_mapping_allows_order_not_renaming() -> None:
    left = FormalSpecification.from_dict(raw_spec("MAP", [
        {"name": "x", "domain": [0, 1]},
        {"name": "y", "domain": [0, 1]},
    ], [{"kind": "less_than", "left": "x", "right": "y"}]))
    reordered = FormalSpecification.from_dict(raw_spec("MAP", [
        {"name": "y", "domain": [0, 1]},
        {"name": "x", "domain": [0, 1]},
    ], [{"kind": "less_than", "left": "x", "right": "y"}]))
    renamed = FormalSpecification.from_dict(raw_spec("MAP", [
        {"name": "u", "domain": [0, 1]},
        {"name": "v", "domain": [0, 1]},
    ], [{"kind": "less_than", "left": "u", "right": "v"}]))
    assert compare_specifications_by_name(left, reordered).status == "EQUIVALENT"
    assert compare_specifications_by_name(left, renamed).status == "INCONCLUSIVE"


def test_equivalent_constraint_forms_and_equal_count_different_sets() -> None:
    variables = [
        {"name": "x", "domain": [0, 1]},
        {"name": "y", "domain": [0, 1]},
    ]
    exactly_one = FormalSpecification.from_dict(raw_spec("EQ", variables, [
        {"kind": "count_equal", "variables": ["x", "y"], "value": 1, "count": 1}
    ]))
    all_different = FormalSpecification.from_dict(raw_spec("EQ", variables, [
        {"kind": "all_different", "variables": ["x", "y"]}
    ]))
    x_zero = FormalSpecification.from_dict(raw_spec("EQ", variables, [
        {"kind": "equal", "variable": "x", "value": 0}
    ]))
    x_one = FormalSpecification.from_dict(raw_spec("EQ", variables, [
        {"kind": "equal", "variable": "x", "value": 1}
    ]))
    assert compare_specifications_by_name(exactly_one, all_different).status == "EQUIVALENT"
    different = compare_specifications_by_name(x_zero, x_one)
    assert different.status == "DIFFERENT"
    assert different.count_equal is True


def test_v2_1_audit_interface_and_evidence_have_no_gold() -> None:
    assert "gold" not in inspect.signature(audit_v2_1).parameters
    parse = parse_public_problem(
        "P",
        "Variables x and y each range over integers 0 through 2. Require x < y. How many ordered assignments are possible?",
    )
    assert parse.status == "COMPLETE"
    assert parse.specification is not None
    assert "gold" not in parse.specification.source.casefold()


def test_v2_1_preflight_blocks_without_api_key(tmp_path: Path) -> None:
    config = {
        "schema": "axiom-x-v2-1-run-config-v1",
        "status": "DRAFT_BLOCKED",
        "api_url": "https://api.openai.com/v1/chat/completions",
        "primary_model": None,
        "secondary_model": None,
        "response_mode": "json_object",
        "development_interface_validated": False,
        "max_retries": 1,
        "max_completion_tokens": 256,
        "max_cost_usd": 10,
        "input_price_usd_per_million": 2,
        "output_price_usd_per_million": 10,
        "pricing_source": "https://developers.openai.com/api/docs/pricing",
        "pricing_checked_on": "2026-10-23",
        "primary_prompt_sha256": "",
        "secondary_prompt_sha256": "",
    }
    dataset = tmp_path / "public.json"
    dataset.write_text(json.dumps([{
        "problem_id": "P1",
        "problem_text": (
            "Variables x and y each range over integers 0 through 2. "
            "Require x < y. How many ordered assignments are possible?"
        ),
        "category": "public-test",
    }]))
    checks = readiness_checks(
        dataset=dataset,
        config=config,
        mode="development",
        review_receipt=None,
        environ={},
    )
    assert next(item for item in checks if item["check"] == "api_key")["passed"] is False
    with pytest.raises(RuntimeError, match="experiment blocked"):
        require_ready(checks)


@pytest.mark.parametrize(
    ("quantifier", "expected_check"),
    [
        ("Exactly", "CARDINALITY_EXACTLY"),
        ("At least", "CARDINALITY_AT_LEAST"),
        ("At most", "CARDINALITY_AT_MOST"),
    ],
)
def test_cardinality_grammars_require_a_complete_match(quantifier: str, expected_check: str) -> None:
    text = (
        "Variables p, q, r are each either 0 or 1. "
        f"{quantifier} 2 of them equal 1. How many assignments satisfy this?"
    )
    parsed = parse_public_problem("CARD", text)
    assert parsed.status == "COMPLETE"
    assert expected_check in parsed.triggered_checks
    partial = parse_public_problem("CARD", text + " Also apply an unstated preference.")
    assert partial.status == "UNSUPPORTED"


@pytest.mark.parametrize(
    ("wording", "kind", "check"),
    [
        ("x to be strictly less than y", "less_than", "STRICT_INEQUALITY"),
        ("x to be less than or equal to y", "less_equal", "NONSTRICT_INEQUALITY"),
    ],
)
def test_controlled_inequality_paraphrases(wording: str, kind: str, check: str) -> None:
    parsed = parse_public_problem(
        "INEQ",
        f"Variables x and y each range over integers 0 through 3. Require {wording}. "
        "How many assignments are possible?",
    )
    assert parsed.status == "COMPLETE"
    assert parsed.specification.constraints[0]["kind"] == kind
    assert check in parsed.triggered_checks


def test_provider_retries_only_a_transient_http_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    specification = raw_spec(
        "API-1",
        [{"name": "x", "domain": [0, 1]}],
        [{"kind": "equal", "variable": "x", "value": 1}],
    )
    body = json.dumps({
        "id": "response-1",
        "model": "gpt-test-snapshot",
        "choices": [{"message": {"content": json.dumps(specification)}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 34},
    }).encode()

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    attempts = 0

    def fake_urlopen(_request, timeout):
        nonlocal attempts
        assert timeout == 60
        attempts += 1
        if attempts == 1:
            raise urllib.error.HTTPError("url", 429, "rate limited", {}, None)
        return Response(body)

    monkeypatch.setenv("OPENAI_API_KEY", "test-only-not-a-real-key")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OpenAICompatibleProvider(
        model="gpt-test", system_prompt="return JSON", max_retries=1, max_completion_tokens=128
    )
    generated = provider.generate("API-1", "public problem")
    assert generated.attempts == 2
    assert generated.requested_model == "gpt-test"
    assert generated.model == "gpt-test-snapshot"
    assert generated.response_id == "response-1"
    assert generated.retry_log == ("attempt 1: HTTP 429",)
    assert '"response-1"' in generated.raw_response


def test_provider_preserves_unparseable_real_response(monkeypatch: pytest.MonkeyPatch) -> None:
    body = json.dumps({
        "id": "bad-response",
        "model": "gpt-test-snapshot",
        "choices": [{"message": {"content": "{not-json"}}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2},
    }).encode()

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    monkeypatch.setenv("OPENAI_API_KEY", "test-only-not-a-real-key")
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: Response(body))
    provider = OpenAICompatibleProvider(model="gpt-test", system_prompt="return JSON")
    with pytest.raises(GenerationFailure) as caught:
        provider.generate("API-BAD", "public problem")
    failure = caught.value.record
    assert failure["raw_output"] == "{not-json"
    assert failure["response_id"] == "bad-response"
    assert failure["attempts"] == 1
