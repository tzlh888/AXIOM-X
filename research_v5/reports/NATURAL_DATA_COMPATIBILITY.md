# Natural Data Compatibility

Status: source collection and automatic compatibility screening COMPLETED; semantic eligibility PROVISIONAL pending independent human review.

Source: Oscar Levin, *Discrete Mathematics: An Open Introduction*, third edition, [section 1.2](https://discrete.openmathbooks.org/dmoi3/sec_counting-binom.html). The [official colophon](https://discrete.openmathbooks.org/dmoi3/front-colophon.html) identifies Oscar Levin and CC BY-SA 4.0. Complete webpage snapshots remain in the original local research record and are excluded from this candidate. Their hashes are retained in RELEASE_PROVENANCE.json; this candidate supplies explicitly marked text-only derivatives, without website presentation components. Extracted/adapted textbook material in this package is distributed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); changes comprise HTML/solution removal, whitespace normalization, metadata, subquestion segmentation, and proposed encodings. This is a license provenance check, not legal advice.

## Fixed screening result

| Exercise | Decision | Reason |
|---|---|---|
| 1.2.1 | Excluded | 15 subset indicators exceed eight-variable DSL limit; no validated alternative |
| 1.2.2 | Excluded | 10 indicators exceed limit; no validated alternative |
| 1.2.3 | Provisional | All four subset-count subquestions fit four binary indicators |
| 1.2.4 | Excluded | 14 positions and disjunctive wording |
| 1.2.5 | Excluded | Total coin inventory across arrangements differs from count-solution target |
| 1.2.6 | Excluded | 10 bit positions exceed limit |
| 1.2.7 | Excluded | 10 subset indicators exceed limit |
| 1.2.8–9 | Excluded | Weighted polynomial coefficients unsupported |
| 1.2.10–11 | Excluded | 18-step direct route representation exceeds limit; no validated compact alternative |
| 1.2.12 | Excluded | Mixed counts and explanation target under fixed whole-exercise rule |
| 1.2.13 | Excluded | Explanation/proof target |

These are conservative eligibility decisions for this study, not impossibility theorems about every possible encoding. Original values and wording were not simplified to gain eligibility.

## Eligible parent and four provisional tasks

Parent: `ww-binom-subsets-vs`, exercise 1.2.3, set A={1,2,3,4}. Questions ask for all subsets, three-element subsets, subsets containing only even numbers, and subsets of even cardinality. Complete recorded parent wording is preserved in `research_v5/evidence/natural_candidates.json` and the blind packet.

A subset corresponds bijectively to four membership indicators. Unconstrained membership, cardinality, and exclusion of odd elements are directly expressible. For even cardinality, a base-3 `number_mod` constraint modulo 2 is lossless because each power of 3 is odd, so the encoded integer has the same parity as the sum of indicators. This proposed encoding was checked against direct subset enumeration and both solvers; it remains AI feasibility evidence, not Gold. Reviewers should create their own specifications and validate the bijection.

There are four tasks but **one source group**. The rendered exercises use WebWork parameters; only the templates have human authorship provenance. Model training exposure is unknown. Normalized exact wording overlap with 144 historical public V3/V4 Development rows is zero. Semantic overlap with earlier binary/cardinality controls is substantial and disclosed. No Held-out texts were read.

The source is newly acquired natural textbook material, but there is still **NO INDEPENDENTLY HUMAN-VERIFIED NATURAL EVALUATION**. Published worked solutions were stripped from reviewer records, are not treated as formal annotations, and do not establish independent reference semantics.
