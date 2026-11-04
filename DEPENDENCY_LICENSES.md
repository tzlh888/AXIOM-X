# Dependency inventory

Dependencies are not vendored. The wheel artifacts used for the clean environment were matched to official PyPI SHA-256 metadata before installation. Project MIT terms do not replace upstream licenses.

| Distribution | Candidate verification pin | Role | Upstream license |
|---|---|---|---|
| z3-solver | 4.15.4.0 | Runtime | MIT |
| pytest | 9.0.3 | Test | MIT |
| setuptools | 80.9.0 | Build backend | MIT |
| wheel | 0.45.1 | Wheel tooling | MIT |
| iniconfig | 2.3.1 | Test dependency | MIT |
| packaging | 26.3 | Test/tool dependency | Apache-2.0 OR BSD-2-Clause |
| pluggy | 1.7.0 | Test dependency | MIT |
| Pygments | 2.21.0 | Test dependency | BSD-2-Clause |

The hash-locked [requirements](requirements-lock.txt) include all wheel-distribution hashes offered by official PyPI for these versions. [Artifact receipts](DEPENDENCY_ARTIFACTS.json) identify the particular wheels checked locally and their source metadata. A fresh environment is separate from the historical model-run environment; these pins do not establish which wheels were present at original generation time.

Python is a separately installed platform under its upstream license and is not redistributed. The build backend requires setuptools >=77; the candidate verification uses 80.9.0. CI references `actions/checkout@v7` and `actions/setup-python@v7`, whose upstream code is not included. Local verification does not assert a remote CI run or guarantee absence of all dependency vulnerabilities.
