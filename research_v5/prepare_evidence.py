"""AI-assisted source triage and V4 audit. No models or private Held-out used."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

from axiom_x.spec import FormalSpecification
from axiom_x.solver import enumerate_specification, solve_z3
from axiom_x.v2 import cheap_rule_decision
from research_v5.extract_source import extract

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        handle.write(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spec(case, variables, constraints):
    return FormalSpecification.from_dict(dict(problem_id=case, variables=variables,
        constraints=constraints, target='count_solutions', source='V5_AI_FEASIBILITY_ONLY',
        generation_id=case, verification_status='UNVERIFIED'))


def audit_v4():
    source = REPO / 'research_v4'
    public = {r['problem_id']: r for r in json.loads((source/'evidence/challenge_public.json').read_text())}
    errors = {r['case_id'] for r in json.loads((source/'analysis/model_rows.json').read_text()) if r['label']=='ERROR'}
    rows = []
    for line in (source/'evidence/natural_model_predictions.jsonl').read_text().splitlines():
        row = json.loads(line)
        if row['case_id'] in errors and row['model']=='deepseek-r1:14b':
            candidate = row['generation']['specification']
            rules = cheap_rule_decision(public[row['case_id']]['problem_text'], candidate, row['solver']['status'])
            constraints = candidate['constraints']
            rows.append(dict(case_id=row['case_id'], constraints=constraints, cheap_rule=rules,
                source_task_family='modulo_remainder_error',
                observed_output_mechanisms=['fixed_assignment_instead_of_full_solution_set',
                    'missing_all_different', 'missing_explicit_nonzero'],
                modulo_constraint_present=any(c['kind']=='number_mod' for c in constraints)))
    assert len(rows)==4
    assert all(r['cheap_rule']['reason_code']=='RULE_MISSING_ALL_DIFFERENT' for r in rows)
    refs = json.loads((source/'evidence/automatic_references.json').read_text())
    # This oracle uses direct mathematics for each frozen family, not the DSL
    # constraint interpreter. It is source-aware AI audit, not external validation.
    oracle=[]
    for row in refs:
        cid=row['problem_id']; s=FormalSpecification.from_dict(row['specification'])
        family=public[cid]['category']; index=int(cid.rsplit('-',1)[1])-1
        expected=set()
        domains=[v.domain for v in s.variables]
        for values in itertools.product(*domains):
            x,y=values[:2]
            if family in {'incorrect_numerical_bounds','incorrect_logical_operator','unsupported_grammar'}: keep=x<y
            elif family=='missing_constraint': keep=len(set(values))==3 and sum(values)==6+index%3
            elif family=='added_constraint': keep=x+y<=max(domains[0])+1
            elif family=='incorrect_negation': keep=y!=0
            elif family=='incorrect_equality': keep=y==1+index%3
            elif family=='variable_mapping_error': keep=y==1+index%2
            elif family=='cardinality_mistake': keep=sum(values)==1+index%3
            elif family=='modulo_remainder_error': keep=values[0]!=0 and len(set(values))==3 and (100*values[0]+10*values[1]+values[2])%4==index%4
            elif family=='correct_specification': keep=2+index%2<=sum(values)<=6+index%2
            else: continue  # ambiguous rows have no unique intended semantics
            if keep: expected.add(values)
        if family=='ambiguous_text': continue
        actual=enumerate_specification(s)
        # solver solutions are tuples in declaration order
        assert expected==set(actual.solutions), (cid, actual.solutions)
        oracle.append(dict(case_id=cid, count=len(expected), matches=True))
    assert len(oracle)==88
    return dict(status='V4_COUNTS_REPRODUCE_WITH_INTERPRETATION_CORRECTIONS',
        human_independent_validation=False, corrected_natural_error_attribution=rows,
        direct_mathematical_reference_checks=oracle,
        selection_finding='freeze._validate_case consults parse_public_problem and checks reference equivalence before inclusion; parser-conditioned eligibility, not independent semantic selection',
        baseline_finding='same inputs and solver status; frozen cheap-rule is a weak syntactic baseline checking only all_different/nonzero; it has no modulo logic',
        uncertainty_finding='Wilson and exact McNemar arithmetic reproduce, but repeated families/parameter settings make iid population inference unwarranted',
        systematic_risk='formal-first templates, parser and DSL share intended semantics; Python and Z3 agreement cannot establish intended natural meaning')


REASONS = {
 'ww-binom-subsets-all': ('EXCLUDED','15 membership variables exceed 8; no validated compact lossless encoding'),
 'ww-binom-subsets-card': ('EXCLUDED','10 membership variables exceed 8; no validated compact lossless encoding'),
 'ww-binom-subsets-vs': ('PROVISIONAL_REVIEW_CANDIDATE','All four subparts are finite subset counts, with a four-indicator bijection; even cardinality can use base-3 number_mod modulo 2'),
 'ww-binom-bitstrings': ('EXCLUDED','14 positions exceed 8; disjunction also outside direct DSL grammar'),
 'ww-binom-coin-rows': ('EXCLUDED','Asks total coin inventory across every row, not number of assignments; count multiplication would change target'),
 'ww-binom-bitstrings-ormore': ('EXCLUDED','10 positions exceed 8; no validated alternative encoding'),
 'ww-binom-subsets-ormore': ('EXCLUDED','10 membership positions exceed 8; no validated alternative encoding'),
 'ww-binom-coef-simple': ('EXCLUDED','Weighted polynomial coefficient target unsupported'),
 'ww-binom-coef-comb': ('EXCLUDED','Sum of weighted polynomial coefficients unsupported'),
 'ww-binom-lattice-paths': ('EXCLUDED','18-step direct encoding exceeds 8; no validated compact encoding'),
 'ww-binom-gridtown': ('EXCLUDED','18-step routes and path avoidance require an unvalidated compact encoding'),
 'ww-binom-pizza': ('EXCLUDED','Includes a conceptual explanation target; frozen rule excludes mixed-target parent exercises'),
 'exercises_counting-binom-13': ('EXCLUDED','Explanation/proof target unsupported')
}


def prepare():
    out=ROOT/'evidence'
    if out.exists(): raise FileExistsError('Frozen evidence already exists')
    rows=extract(); assert set(REASONS)=={r['source_id'] for r in rows}
    for row in rows:
        status,reason=REASONS[row['source_id']]
        row.update(source='https://discrete.openmathbooks.org/dmoi3/sec_counting-binom.html#'+row['source_id'],
            license='CC-BY-SA-4.0', author='Oscar Levin', compatibility=status, reason=reason,
            ambiguity_status='PENDING_INDEPENDENT_REVIEW', expected_logical_structure=reason,
            domain='four membership indicators in {0,1}' if status.startswith('PROVISIONAL') else 'See original wording; not changed',
            previous_exposure_risk='public textbook; model pretraining contamination cannot be excluded; fixed WebWork rendering parameters, not newly human-written items')
    dump(out/'candidate_screen.json',rows)
    parent=next(r for r in rows if r['compatibility'].startswith('PROVISIONAL'))
    # All four questions retained together; no result-dependent subpart selection.
    lines=parent['original_wording'].splitlines(); assert len(lines)==5
    candidates=[]; feasibility=[]
    for i in range(4):
        cid=f'V5-LEVIN-1.2.3-{i+1}'
        names=['b1','b2','b3','b4']
        variables=[dict(name=n,domain=[0,1]) for n in names]
        constraints=[[],[dict(kind='count_equal',variables=names,value=1,count=3)],
            [dict(kind='equal',variable='b1',value=0),dict(kind='equal',variable='b3',value=0)],
            [dict(kind='number_mod',variables=names,base=3,modulus=2,remainder=0)]][i]
        candidate=spec(cid,variables,constraints)
        python=enumerate_specification(candidate); z3=solve_z3(candidate)
        mathematical=[set(itertools.product([0,1],repeat=4)),
            {v for v in itertools.product([0,1],repeat=4) if sum(v)==3},
            {v for v in itertools.product([0,1],repeat=4) if v[0]==v[2]==0},
            {v for v in itertools.product([0,1],repeat=4) if sum(v)%2==0}][i]
        assert set(python.solutions)==set(z3.solutions)==mathematical
        candidates.append(dict(problem_id=cid,group_id=parent['source_id'],source=parent['source'],
            original_wording=lines[0]+'\n'+lines[i+1], full_parent_wording=parent['original_wording'],
            domain_context='Membership indicators b1,b2,b3,b4 refer in order to elements 1,2,3,4; each is 0 or 1. Reviewer must verify this bijection.',
            license='CC-BY-SA-4.0',compatibility='PROVISIONAL_AI_CHECKED_NOT_HUMAN_GOLD',
            ambiguity_status='PENDING',previous_exposure_risk=parent['previous_exposure_risk']))
        feasibility.append(dict(problem_id=cid,proposal=candidate.to_dict(),count=python.count,dual_solver_and_direct_math_agree=True,human_gold=False))
    dump(out/'natural_candidates.json',candidates)
    dump(out/'AI_FEASIBILITY_NOT_GOLD.json',feasibility)
    dump(out/'V4_AUDIT.json',audit_v4())
    # Only inspect past public Development texts; no Held-out read.
    old=[]
    for file in [REPO/'research_v3/evidence/public_dataset.json',REPO/'research_v4/evidence/challenge_public.json']:
        old.extend(json.loads(file.read_text()))
    normalize=lambda t:' '.join(t.casefold().split())
    overlaps=[c['problem_id'] for c in candidates if any(normalize(c['original_wording'])==normalize(r['problem_text']) for r in old)]
    assert not overlaps
    dump(out/'DEDUPLICATION.json',dict(normalized_exact_overlap=overlaps,
        historical_public_rows=len(old), candidate_rows=4,independent_source_groups=1,
        semantic_family_overlap='Subset membership/cardinality is related to earlier binary controls; no claim of novel mathematics or no pretraining exposure'))
    for reviewer in ['A','B']:
        packet=dict(schema='axiom-v5-blind-review-v1', reviewer_id=None,independent_human_attestation=None,
            reviewer_slot=reviewer,records=[dict(problem_id=c['problem_id'],source=c['source'],
                original_wording=c['original_wording'],full_parent_wording=c['full_parent_wording'],
                domain_context=c['domain_context'],reference_specification=None,ambiguity_status=None,
                rationale=None,disagreement_note=None) for c in candidates])
        dump(out/f'reviewer_{reviewer}_BLANK.json',packet)
    dump(out/'GOLD_GATE_STATUS.json',dict(status='BLOCKED_NO_INDEPENDENT_HUMAN_GOLD',
        completed_reviewers=0,required_reviewers=2,model_calls_executed=0,
        natural_evaluation_executed=False,baseline_comparison_executed=False))
    manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in str(p) and p.name!='MANIFEST.json'}
    dump(ROOT/'MANIFEST.json',manifest)
    print(json.dumps(dict(screened=13,excluded=12,provisional_subquestions=4,source_groups=1,gold_gate='BLOCKED')))


def verify():
    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    assert all(sha(ROOT/p)==digest for p,digest in manifest.items())
    assert extract()==[{k:r[k] for k in ['source_id','original_wording']} for r in json.loads((ROOT/'evidence/candidate_screen.json').read_text())]
    assert audit_v4()==json.loads((ROOT/'evidence/V4_AUDIT.json').read_text())
    for slot in ['A','B']:
        packet=json.loads((ROOT/f'evidence/reviewer_{slot}_BLANK.json').read_text())
        assert packet['reviewer_id'] is None
        assert all(r['reference_specification'] is None for r in packet['records'])
    print('VERIFIED: source extraction, all frozen hashes, V4 audit regeneration, and blank blind packets; Gold remains blocked')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','verify'])
    args=parser.parse_args()
    prepare() if args.command=='prepare' else verify()
