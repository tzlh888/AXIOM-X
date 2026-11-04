# V5 Execution Report

Date: 2026-11-03. Status: automated audit and preparation COMPLETED; independent natural evaluation BLOCKED at the human-Gold gate. All new engineering is substantially AI-assisted.

## Executed evidence

The V4 frozen-data and analysis verifier passed again, without model regeneration. The original 81-test suite and three new targeted V5 checks passed: **84 passed**. All 96 challenge rows, 72 injected errors, 16 correct controls, eight ambiguous controls, 96 local-model records, and four erroneous model outputs remain reproducible. V4 FCR is erroneous ACCEPTs / actual semantic-error opportunities; acceptance coverage is ACCEPT/all rows, decision coverage is (ACCEPT+REJECT)/all rows, and selective risk excludes unresolved ACCEPTs from its denominator.

A separate source-aware mathematical enumeration checked all 88 unambiguous V4 reference sets against the implementation. All agreed. This is new internal audit evidence, not independent human validation. The eight ambiguous rows were deliberately excluded from semantic checks.

## Corrections to V4 interpretation

1. The four model errors occurred on tasks whose generator family was `modulo_remainder_error`. That field is task metadata, not an observed error diagnosis. Inspection of raw predictions reveals fixed singleton assignments, omitted explicit nonzero and all-different constraints, and absent modulo constraints on three of four rows. The third includes the requested modulo constraint but fixes digits to 123, inconsistent with remainder 2; its candidate solution set is empty. Therefore the V4 description of four modular-remainder substitutions is inaccurate.
2. Cheap-rule rejected all four with `RULE_MISSING_ALL_DIFFERENT`. It checks literal distinctness/nonzero clauses and serialized constraints; it contains no modulo logic. V4's description of a targeted modular rule is corrected here. Three fixed assignments already imply distinctness and a nonzero first digit, so absence of those serialized constraints is not itself proof of a missing semantic condition. The cheap rule happens to reject these wrong candidates through a syntactic trigger; their actual error is established by reference solution-set comparison.
3. `_validate_case` calls AXIOM-X's `parse_public_problem` and asserts parser status plus parser/reference equivalence before admission. The protocol was frozen first and there is no evidence of result-driven replacement, but eligibility is parser-conditioned. This is weaker than selection independent of the tested system.
4. Families repeat parameter settings under different names. Nominal Wilson intervals and exact McNemar arithmetic reproduce, but treating them as iid natural-population inference is unjustified. The tiny injected-challenge p-value is descriptive conditional on the constructed rows.

Historical V4 files and frozen predictions were preserved. No production algorithm changed.

## New source work

The original local study downloaded and hashed Oscar Levin's DMOI3 section 1.2 and its official colophon. This release instead includes explicitly marked text-only derivatives; complete website snapshots remain excluded. The source grants CC BY-SA 4.0. A selection protocol was committed before compatibility triage. All 13 rendered exercises were extracted without solutions and screened; 12 were excluded under fixed criteria. One parent exercise supplies four count subquestions provisionally compatible through a four-indicator bijection. All four were retained with their full parent context; none was selected using AXIOM-X decisions.

These are pre-existing textbook questions with human-authored exercise templates and fixed WebWork rendering parameters. They are not new human annotations, a natural deployment sample, or four independent sources. Public pretraining exposure cannot be excluded.

Prepared two blank reviewer records, reviewer instructions, disagreement/adjudication rules, machine-readable provenance, deduplication results, AI feasibility evidence stored outside the blind packet, and a frozen conditional evaluation protocol. No completed reviewer identity or Gold record was supplied. Model calls: 0. Independent natural evaluation: not run. Accordingly no `BASELINE_COMPARISON.md` was created.

## Decision

The V5 interpretation corrects independence and error-attribution claims. Formal Held-out was not run, paid APIs were not used, and the branch was neither pushed nor merged. The useful next step is independent review; additional synthetic expansion has been stopped.

Evidence files are in `research_v5/evidence/`: `V4_AUDIT.json`, `candidate_screen.json`, `natural_candidates.json`, `AI_FEASIBILITY_NOT_GOLD.json`, `DEDUPLICATION.json`, `GOLD_GATE_STATUS.json`, and manifests. Only the contents of `research_v5/reviewer_only/` should be supplied to blind annotators.

## Reproduction

This candidate contains the research modules, evidence and unchanged tests. Follow the root REPRODUCE.md and run `python release_verify.py` from the candidate root. Public V5 verification checks the new derivative manifest, re-extracts the 13 recorded statements from the text-only fixture, regenerates the internal audit, and checks blank reviewer forms. It does not call a model or verify excluded original webpage bytes. HISTORICAL_MANIFEST.json preserves the initial local freeze, while MANIFEST.json and the root SHA256SUMS describe the public derivative. Original commit IDs are provenance identifiers rather than proof of public availability.

Public derivative notice: this copy omits an internal simulated assessment. Historical experiment records are unchanged. Original narrative identity and source-snapshot hashes are retained in release provenance. The source-only excerpt verifies recorded statement extraction, not original website bytes.
