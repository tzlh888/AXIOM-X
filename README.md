# AXIOM-X

AXIOM-X is a substantially AI-assisted research prototype for auditing language-model-generated specifications of finite counting problems. It studies the difference between computing correctly from a specification and preserving the meaning of a problem.

**V5 release candidate — prepared locally, awaiting human publication approval.** This tree contains the evidence required for the deterministic checks below; this statement does not imply that the candidate is already on GitHub.

## Method and scope

Explicit integer domains and constraints define finite solution sets. Python enumeration and Z3 cross-check formal objects. A deterministic parser supplies semantics only for a fixed controlled-language grammar. Set differences can produce counterexamples; unsupported text, unproved variable mapping or incomplete solving lead to abstention. Agreement between solvers does not independently validate human intent. The implementation is a bounded local research tool, not a hardened arbitrary-input service.

## Executed evidence

| Study | Result | Boundary |
|---|---|---|
| V4 controlled challenge | 72/72 injected errors rejected across nine predefined mechanisms; 8 ACCEPT / 72 REJECT / 16 ABSTAIN overall | 96 constructed cases; parser-conditioned eligibility and repeated families |
| V4 local-model run | Two named local models each received the same 48 controlled inputs. One produced four semantic errors, all rejected; the other produced no semantic-error opportunities | Saved model outputs, not a natural-language deployment sample |
| Simple rule baseline | Also rejected all four model errors; caught none of the 72 injected errors | Distinctness/nonzero syntax checks, with no dedicated modulo reasoning; no demonstrated added detection over this rule on the observed model errors |
| V5 source/Gold work | Four provisional textbook subquestions from one parent; zero completed independent reviewers | Independent human Gold and formal Held-out natural-language validation remain incomplete |

The four model errors involved fixed assignments and omitted constraints on modulo-themed tasks, not four demonstrated remainder substitutions. Three fixed assignments already imply distinctness: the baseline's missing-constraint syntax trigger alone does not establish semantic invalidity.

For `gpt-oss:20b`, AXIOM-X acceptance coverage is 43/48; FCR is N/A because no semantic errors occurred among valid outputs. For `deepseek-r1:14b`, acceptance coverage is 35/48 and FCR is 0/4, with nominal Wilson 95% upper bound 48.99%; paired McNemar versus Accept-all gives p=0.125. The simple rule accepts 40/48. Zero observed false certifications does not establish zero risk. Related cases and shared sources prevent natural-population inference. V3's earlier post-hoc four-error observation is separate and is not pooled with V4.

## Reproduce without model calls

See [installation and deterministic checks](REPRODUCE.md), [metrics](METRICS.md), [limitations](LIMITATIONS.md), [V5 corrections](research_v5/reports/V5_EXECUTION_REPORT.md), [challenge results](research_v4/analysis/challenge_results.json) and [model results](research_v4/analysis/model_results.json).

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-lock.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps .
.venv/bin/python release_verify.py
```

V3/V4 frozen evidence is preserved byte-for-byte. V5 uses a clearly labelled text-only textbook excerpt, not the original website snapshot; [provenance](RELEASE_PROVENANCE.md) explains the public derivative and its historical hashes. No model-generation command is needed to recompute the findings.

## Attribution and licenses

Planning, engineering, experiments, analysis, error investigation and writing received [substantial AI assistance](DISCLOSURE.md). Independent applicant implementation, sole invention, verified human-led development and independent human semantic review are not established. [Applicant contribution questions](APPLICANT_CONTRIBUTION.md) remain open; project descriptions use role-neutral wording.

Original project code retains its [MIT license](LICENSE). Licensed textbook excerpts/adaptations retain CC BY-SA 4.0 and their author/source/change notices; see [third-party notices](THIRD_PARTY_NOTICES.md). Complete webpage snapshots, scripts, branding, private materials and simulated assessments are [excluded](PRIVATE_EXCLUSIONS.md). The [evidence card](docs/admissions/FINAL_RESEARCH_EVIDENCE_CARD.md) and CV examples are review drafts, not claims of independently verified personal achievement.
