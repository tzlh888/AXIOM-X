# Dependency license inventory

This file records a release-engineering check, not legal advice. Dependencies
are installed from their upstream distributions; their source is not vendored.

| Component | Use | Version/range | Upstream license | Compatibility finding |
|---|---|---|---|---|
| Z3 / `z3-solver` | runtime solver | `4.15.4.0` | MIT | Compatible with the project MIT license |
| pytest | tests | `9.0.3` | MIT | Compatible; development/test only |
| iniconfig | pytest dependency | `2.3.1` | MIT | Compatible; development/test only |
| packaging | pytest dependency | `26.3` | Apache-2.0 OR BSD-2-Clause | Compatible; development/test only |
| pluggy | pytest dependency | `1.7.0` | MIT | Compatible; development/test only |
| Pygments | pytest dependency | `2.21.0` | BSD-2-Clause | Compatible; development/test only |
| setuptools | build backend | `>=77` | MIT | Compatible; build-time only |
| `actions/checkout` | CI | `v7` | MIT | Referenced action, not vendored |
| `actions/setup-python` | CI | `v7` | MIT | Referenced action, not vendored |

Primary upstream references:

- https://github.com/Z3Prover/z3
- https://github.com/pytest-dev/pytest
- https://github.com/pytest-dev/iniconfig
- https://github.com/pypa/packaging
- https://github.com/pytest-dev/pluggy
- https://github.com/pygments/pygments
- https://github.com/pypa/setuptools
- https://github.com/actions/checkout
- https://github.com/actions/setup-python

These upstream licenses are not replaced by the project `LICENSE`. The
project-content rights boundary is recorded separately in `COPYRIGHT_REVIEW.md`.
