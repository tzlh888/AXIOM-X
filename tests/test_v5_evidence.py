import json
from pathlib import Path

from research_v5.extract_source import extract

ROOT = Path(__file__).parents[1] / 'research_v5'


def test_blind_review_records_are_complete_and_have_no_gold():
    source = {r['source_id']: r for r in extract()}
    parent = source['ww-binom-subsets-vs']['original_wording']
    for slot in ['A', 'B']:
        packet = json.loads((ROOT / f'evidence/reviewer_{slot}_BLANK.json').read_text())
        assert packet['reviewer_id'] is None
        assert packet['independent_human_attestation'] is None
        assert len(packet['records']) == 4
        for record in packet['records']:
            assert record['reference_specification'] is None
            assert record['full_parent_wording'] == parent
            assert set(record) == {'problem_id', 'source', 'original_wording', 'full_parent_wording',
                'domain_context', 'reference_specification', 'ambiguity_status', 'rationale', 'disagreement_note'}


def test_task_family_is_not_mistaken_for_observed_error_mechanism():
    audit = json.loads((ROOT / 'evidence/V4_AUDIT.json').read_text())
    rows = audit['corrected_natural_error_attribution']
    assert len(rows) == 4
    assert all(r['cheap_rule']['reason_code'] == 'RULE_MISSING_ALL_DIFFERENT' for r in rows)
    assert sum(r['modulo_constraint_present'] for r in rows) == 1
    assert len(audit['direct_mathematical_reference_checks']) == 88


def test_gold_gate_blocks_unexecuted_results():
    gate = json.loads((ROOT / 'evidence/GOLD_GATE_STATUS.json').read_text())
    assert gate['completed_reviewers'] == 0
    assert gate['model_calls_executed'] == 0
    assert gate['natural_evaluation_executed'] is False
    assert gate['baseline_comparison_executed'] is False
