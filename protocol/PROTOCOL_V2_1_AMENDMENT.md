# AXIOM-X V2.1 protocol amendment

Date: 2026-10-23 (Europe/Budapest)  
Status: **FROZEN FOR V2.1 ENGINEERING VALIDATION; FORMAL HELD-OUT RUN NOT AUTHORIZED**

This amendment adds a new strategy, `B2_1`. It does not alter `PROTOCOL_V2.md`, the
historical `B2` implementation, or any V2 evidence.

## Motivation and disclosed diagnostic reuse

The 16 V2 synthetic controls exposed three failures: peer agreement certified the
common omissions in `SYN-06`/`SYN-14`; peer disagreement rejected correct Primaries
in `SYN-08`/`SYN-16`; and exact domain mapping made `SYN-04`/`SYN-12` inconclusive.
Those cases participated directly in diagnosis. All V2.1 results on them are therefore
exploratory regression results, never independent performance evidence.

The original 40 V2 Held-out questions and their candidate references have also been
inspected during V2/V2.1 engineering and Gold-packet construction. Several V2.1
grammars overlap their authored templates. They remain valid material for human
semantic auditing of the legacy candidates, but they are **not a pristine confirmatory
Held-out set for V2.1**. A new blind set must be authored and sequestered before a
formal V2.1 effectiveness claim.

## B2.1 evidence channel

`B2_1` adds a deterministic, Gold-blind public-text semantic channel. It receives only
the public problem ID and text. It uses a closed set of full-string grammars for bounded
domains and explicitly expressed constraints: distinctness, exact/at-least/at-most
cardinality, strict inequality, equality, sum bounds/equality, exclusions, and the
supported digit/modular construction. A keyword or partial match is insufficient.

This channel is not a general natural-language theorem prover. Its output is a bounded
formal interpretation whose provenance is recorded as
`v2.1-deterministic-public-text-parser`. Unsupported or partial text yields ABSTAIN.
It never reads Gold, reviewer files, candidate references, or model outputs when
constructing the public-text specification.

## Decision rules

- **ACCEPT** only when the Primary parses, its solver completes, the entire public text
  matches a supported grammar, exact-name variable mapping is established, Z3 proves
  the Primary and public-text solution sets equivalent, and Python enumeration agrees
  with Z3. The claim is limited to the fixed grammar and finite-domain semantics.
- **REJECT** only when Z3 finds a symmetric-difference witness between the Primary and
  the independently extracted public-text specification, or the proposed answer
  disagrees with the verified Primary count.
- **ABSTAIN** on unsupported/partial language, unproved mapping, Primary generation or
  parse failure, solver timeout/unknown, or solver cross-check failure.

Primary/Secondary agreement or disagreement is auxiliary evidence only. A missing or
bad Secondary cannot by itself ACCEPT or REJECT the Primary and does not block a
decision supported independently by the public text.

## Mapping and equivalence policy

Variable order and constraint order may differ. Equivalence is a finite-domain
symmetric-difference query, not a count comparison, so equal counts with different
solution sets remain different. Domains with the same variable names can be compared
over their union, allowing a concrete extra/missing-value witness. Renaming, guessed
isomorphisms, auxiliary variables, and unproved scope correspondence remain UNKNOWN.
No name-similarity heuristic is allowed.

## Evidence record

Each `B2_1` decision stores decision, reason code, triggered checks, counterexample,
Primary/Secondary comparison, Primary/public-text comparison, solver status,
uncertainty reason, evidence provenance, and an explicit claim boundary. Generation
records add requested and returned model IDs, response ID, attempt count, token usage,
and latency when the provider supplies them.

Every material claim is classified as one of four levels:

- `FORMALLY_PROVEN`: only a finite-set relation or witness between already formalized
  artifacts under an established mapping.
- `DETERMINISTICALLY_CHECKED`: parser output, exhaustive enumeration, hash verification,
  or other repeatable software check.
- `MODEL_INFERRED`: content proposed by a model without independent certification.
- `UNVERIFIED`: unsupported, incomplete, or not yet checked.

The public-text parser is `DETERMINISTICALLY_CHECKED`, not a formal proof of English
meaning. Consequently an overall B2.1 ACCEPT is also only
`DETERMINISTICALLY_CHECKED`; Z3's `FORMALLY_PROVEN` label applies to the conditional
relationship between the two formal artifacts, not to natural-language faithfulness.

## Evaluation changes

V2.1 retains all V2 metrics and adds specification-disagreement rate, common-error
detection rate, common-error miss rate, and correct-specification acceptance rate, each
with numerator and denominator. `B2_1` is reported beside, not in place of, B0–B3. B3
is a deterministic rule-based renderer/checker, not an LLM back-translation baseline.
Paired tests remain exploratory. Coverage, abstention, false rejection, and selective
risk must accompany false-certification rates; abstaining on nearly all rows is not a
success criterion.

## Validation and formal-run boundary

The new rules are tested on newly written mechanism/edge cases for correct/correct,
correct/wrong, wrong/correct, common omission, unsupported semantics, exact/at-least/
at-most, strict mapping, equivalent expressions, and equal-count/different-set cases.
These tests validate implementation behavior, not population performance.

Before any real run: an independent custodian must select exactly 40 public-only rows
under `V2_1_HELDOUT_SELECTION.md`, pass the duplicate screen, and create a hash lock
with `prepare_v2_1_heldout.py`. Then freeze exact model IDs and prices; perform a
one-item interface smoke test and Development validation; keep the USD 10 cap; retain
all successes and failures; complete real independent two-stage human Gold review. The
completion receipt must be bound to the exact public/Gold hashes, verify 40 completed
rows per reviewer and stage, bind Stage 2 rows to the locked Stage 1 hash, and report no
unresolved disagreements. Then freeze the Gold hash in the formal run config; obtain
explicit authorization for the formal run; and write only to new, non-existing
V2.1 paths. The legacy 40 remain historical/regression material and cannot be relabelled
as a pristine V2.1 sample. Without all gates, natural-model metrics are N/A.

