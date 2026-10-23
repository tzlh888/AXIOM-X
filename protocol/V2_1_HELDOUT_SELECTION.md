# V2.1 independent Held-out selection protocol

Status: **READY FOR AN INDEPENDENT DATA CUSTODIAN; DATASET NOT YET CREATED**

The original 40 V2 questions are Historical Development / Regression Data. They must
not be edited, re-sampled, or relabelled as a fresh V2.1 confirmatory set.

## Custodian procedure

An independent custodian who has not inspected B2.1 source rules should select exactly
40 bounded finite-domain mathematical counting problems. AXIOM-X developers must not
see the candidate pool, rejected items, Gold, or final questions before the public split
is frozen.

Prespecified strata should cover integer domains; strict and non-strict inequalities;
exact/at-least/at-most cardinality; conjunction; exclusion/negation; distinctness;
permutations/combinations; boundary conditions; and at least five deliberately
ambiguous or unsupported formulations retained for coverage/abstention analysis.
No stratum may be added or removed after model output is observed.

Include each item only when it:

1. has a finite domain and an independently solvable count;
2. has a traceable source reference and redistribution permission;
3. was not copied or paraphrased from V1/V2 data or prompt examples;
4. is not an exact or near duplicate of another selected item;
5. fits the declared sampling frame without consulting AXIOM-X decisions.

Do not exclude an item after generation because a model failed, an audit abstained, or
the result harms a hypothesis. Pre-run exclusions are limited to provenance,
permission, duplication, non-finite scope, and irreparable ambiguity discovered before
any model call; every exclusion and reason must be retained privately by the custodian.

## Public import record

Each JSON row must contain exactly:

- `problem_id`
- `problem_text`
- `category`
- `selection_stratum`
- `source_reference`
- `license_or_permission`

Run `code/prepare_v2_1_heldout.py` locally. It rejects non-40 inputs, forbidden extra
fields, duplicate IDs, and mechanically detected near duplicates within the candidate
set or against all 52 historical V2 public problems. The 0.92 normalized
`SequenceMatcher` screen is only a triage heuristic; the custodian must also perform a
semantic duplicate review.

The tool writes `public.json` and `LOCK.json` to a new directory and refuses overwrite.
It never accepts or writes Gold. Send only the public file and lock receipt to the model
experiment operator. Keep candidate Gold, selection ledger, rejected pool, reviewer
identities, and completed review ledgers outside the public repository.

## Gold and release boundary

After public freeze, independent reviewer(s) complete Stage 1 without candidate Gold.
Only after Stage 1 ledgers are hash-locked may Stage 2 reveal candidate specifications
and counts. A completion receipt must hash the real ledgers. Until then Gold status is
PENDING and formal evaluation is prohibited.

