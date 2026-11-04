# Installation and deterministic reproduction

Use Python 3.11 or newer. The candidate was prepared for a fresh local environment; recorded results are in the release-candidate verification report supplied for human approval. No API key, model weights or model call is needed for these commands.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-lock.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps .
.venv/bin/python release_verify.py
```

The lock includes the reviewed build backend and test dependencies as well as Z3. Its wheel hashes were checked against official PyPI metadata. Other supported operating systems must still pass their own installation/verification; a macOS run does not establish Linux or Windows success. No dependencies are vendored in the candidate.

`release_verify.py` checks `SHA256SUMS`, all three research verification commands and the unchanged existing pytest suite. Individually:

```bash
python -m research_v3.controlled_development verify
python -m research_v4.v4_experiment verify
python -m research_v5.prepare_evidence verify
python -m pytest -q -p no:cacheprovider
python -m axiom_x.demo
```

Run from the checkout root, since research namespace modules and frozen data are source-tree artifacts; package installation installs the `axiom_x` runtime and CLI. The full source distribution is needed for research verification. A runtime-only wheel is not the evidence release.

V3/V4 verification reuses saved outputs, regenerates deterministic data and analyses and compares hashes. It does not regenerate model outputs. V5 verification reads the explicitly labelled `binom_excerpt.html` fixture and the new public-derivative `MANIFEST.json`. The original initial V5 manifest is preserved as `HISTORICAL_MANIFEST.json` for provenance; its excluded webpage hashes cannot be verified solely from this public tree.

The text-only fixture contains exactly the 13 original recorded normalized exercise statements, without scripts, styles, branding, answers or interactive components. Its extraction matches the existing candidate screen byte-for-byte at the statement level. This does not prove original website-byte identity, independent human meaning or independent reference Gold. Public audit results remain internal reproducibility evidence.

Do not run `freeze`, `run`, `run-models`, `prepare`, prediction-provider commands or official Held-out procedures to reproduce this release. Generation is a separate gated research activity and is not part of the verification path.
