# Public reproduction

## Supported environment

- Python 3.11 or newer (CI uses Python 3.12)
- No API key
- No private Gold, review packet, raw prediction, or recording

From a fresh clone:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-extension.txt
python -m pip install --no-deps .
pytest -q
python -m axiom_x.demo
```

## What this reproduces

- deterministic unit and integration tests for the bounded DSL;
- Python/Z3 finite-solver agreement on synthetic fixtures;
- Gold-isolation and frozen-payload controls using temporary test fixtures;
- a deterministic synthetic demonstration.

## What this cannot publicly reproduce

- historical V2 candidate-Gold or V2.1 candidate-Gold evaluation;
- Gold review-packet construction or private reviewer evidence;
- raw model predictions or experiments based on non-public data;
- a completed natural LLM experiment;
- independently validated Gold or a pristine held-out study.
- historical aggregate-statistics recomputation, because the two source CSV
  tables remain private until their redistribution rights are confirmed.

These limits are intentional. Passing public tests is software evidence, not a
claim of real-model validation.
