# Frozen Evaluation Protocol

Status: conditional Development protocol FROZEN; execution BLOCKED by missing independent human Gold. No effectiveness results are available for V5.

## Sample and gates

The fixed source universe is the 13 exercises in the saved DMOI3 section 1.2 snapshot. Apply `SELECTION_PROTOCOL.json`. All four subquestions of provisionally compatible exercise 1.2.3 are retained in a single source group. No additional tasks, paraphrases, parameter changes, hard-task enrichment, or retries may be added after outcomes are viewed. If human review excludes a task, preserve the record and do not replace it. If none survives, stop.

Gold must be independently authored, adjudicated where possible, and frozen before predictions. Each task must have one-to-one named variables and an agreed domain mapping. Model prompts may include only original source context, question, and the neutral agreed variable naming convention; no reference constraints, counts, labels or system decisions. The convention must be approved with Gold before generation so that equivalent variable renaming is not mislabelled.

## Models and generation

Models: `gpt-oss:20b` local hash `9ba9cc2b4e02`; `deepseek-r1:14b` hash `c333b7232bdb`. Check installed hashes before execution; a mismatch blocks rather than silently changes the model. Prompt: unchanged V4 `ollama_formalizer_prompt.txt`, SHA-256 `2be19a815526cf140b5e0cee8bee278bfaee9b4c3a9c8e99a6421071b6376702`. Temperature 0, seed 20261105, maximum 1200 tokens, no retries, each task once per model. Budget is at most eight calls for the four candidates (selection protocol's broader 26-call ceiling is not a sample expansion permission). No paid API. Freeze all raw outputs before evaluation.

## Strategies

Same inputs, candidates, Gold, resource limits and failures for Accept-all-valid, Solver-only, unchanged `cheap_rule_decision`, and AXIOM-X B2.1. Accept-all accepts schema-valid outputs even if solver incomplete; Solver-only accepts only complete solving. Invalid outputs abstain for every strategy. Cheap-rule remains the literal distinct/nonzero baseline. Report rule trigger counts; lack of literal triggers is a limitation of this baseline, not evidence of superiority to all lightweight semantic methods.

Do not rewrite natural wording into the controlled parser grammar. AXIOM-X abstention on unsupported natural text is retained as a coverage result. No algorithm or prompt tuning is authorized within this frozen comparison.

## Metrics and analysis

Report per model: total N; valid/invalid outputs; correct/error/UNKNOWN reference relations; ACCEPT/REJECT/ABSTAIN; false certifications/error opportunities; acceptance coverage; decision coverage; selective risk over resolved accepted cases; false rejection/correct opportunities; and correct abstention/correct opportunities. Zero error opportunities makes FCR and detection N/A. Unknowns remain excluded from correctness denominators and their counts are explicit.

Compare false-certification decisions in pairs on the same error rows, including cheap-rule versus AXIOM-X. Report exact discordant counts and two-sided exact McNemar as a conditional descriptive calculation. Wilson 95% intervals may be included as nominal row-level summaries, explicitly warning that the four tasks share one parent and do not identify independent-sample population uncertainty. Do not pool two model outputs as independent tasks. With one group, no credible cluster-based population interval or power claim is available.

Observed error categories are assigned after inspection of predicted constraints versus frozen Gold: domain error, missing constraint, added constraint/overrestriction, fixed-witness substitution, operator/negation/equality error, variable mapping error, cardinality error, modulo error, or unresolved. Multi-label classification is permitted. Source task family is never substituted for observed error type.

AXIOM-X superiority to cheap-rule requires actual semantic errors rejected by AXIOM-X and accepted by cheap-rule, with exact counts and uncertainty. Otherwise report no demonstrated superiority. Stop when the fixed run is exhausted or errors/baseline differences are insufficient. Official Held-out remains prohibited.
