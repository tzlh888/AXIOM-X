# Copyright and redistribution review

Status: **MIT configuration confirmed; final publication approval pending**.
This is a provenance and release-engineering review, not legal advice.

Confirmed license configuration:

- License: MIT License
- Copyright year: 2026
- Copyright holder: TANG ZELUOHE

The holder name alone was not treated as proof that every possible project file
could be licensed. Each included class was reviewed against repository
provenance, disclosures, attribution markers, and the no-vendoring boundary.

## Included original-content classes

| Class | Files | Rights evidence and boundary | Treatment |
|---|---|---|---|
| Core implementation | `axiom_x/*.py` | Project history and disclosure identify project-authored, AI-assisted implementation; no third-party copyright header, copied-source attribution, or vendored code found | Included under project MIT license |
| Tests and synthetic fixtures | `tests/*.py` | Inline deterministic fixtures; no research Gold or external dataset row; project-authored with AI assistance | Included under project MIT license |
| Documentation | Root Markdown files | Project-specific prose; AI assistance disclosed; private assessments and private-file manifests excluded | Included under project MIT license |
| Prompts | `prompts/*.txt` | Project-specific instructions; no third-party prompt attribution or copied corpus text found | Included under project MIT license |
| Protocols, schemas, and run config | `protocol/*` | Project-specific research design and configuration; contains no Gold or raw results | Included under project MIT license |
| Packaging and CI | `pyproject.toml`, requirements, workflow, `.gitignore` | Project configuration; external tools are referenced, not copied | Included under project MIT license |

The MIT grant applies only to copyright interests held by TANG ZELUOHE in the
included project material. It does not override an upstream license or grant
rights in excluded material.

## Excluded because rights are not confirmed

| Material | Treatment |
|---|---|
| `data/category_summary.csv` | Excluded from the working tree and all candidate history; private checksum-preserved backup retained |
| `data/cluster_summary.csv` | Excluded from the working tree and all candidate history; private checksum-preserved backup retained |
| Historical aggregate-statistics script/test | Excluded because public reproduction would require the uncleared CSV files |
| Candidate Gold, review packets, reference answers, raw predictions/results | Excluded for confidentiality and/or unconfirmed redistribution rights |
| Private author assessments and recordings | Excluded; retained only as private evidence |

## Third-party components

Z3, pytest, their transitive test dependencies, setuptools,
`actions/checkout`, and `actions/setup-python` retain their upstream licenses.
They are referenced or installed from upstream and are not vendored. Python's
standard library is a platform dependency and is not redistributed here.
Details are in `DEPENDENCY_LICENSES.md`.
