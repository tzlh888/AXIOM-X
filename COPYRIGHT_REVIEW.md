# Copyright and redistribution review

Status: **project-lead confirmation required before publication**. This is a
provenance and release-engineering review, not legal advice or a license grant.

## Included original-content classes

| Class | Files | Evidence reviewed | Release treatment |
|---|---|---|---|
| Core implementation | `axiom_x/*.py` | Project history and disclosure identify project-authored, AI-assisted implementation; no third-party copyright header, copied-source attribution, vendored code, or non-standard dependency was found | Eligible for the proposed MIT grant after holder/authority confirmation |
| Tests and synthetic fixtures | `tests/*.py` | Inline deterministic fixtures; no research Gold or external dataset row; project-authored with AI assistance | Eligible after holder/authority confirmation |
| Documentation | Root Markdown files | Project-specific prose; AI assistance disclosed; private assessments and prior private-file manifests excluded | Eligible after holder/authority confirmation |
| Prompts | `prompts/*.txt` | Project-specific instructions; no third-party prompt attribution or copied corpus text found | Eligible after holder/authority confirmation |
| Protocols, schemas, and run config | `protocol/*` | Project-specific research design and machine-readable configuration; contains no Gold or raw results | Eligible after holder/authority confirmation |
| Packaging and CI | `pyproject.toml`, requirements, workflow, `.gitignore` | Project configuration; external tools are referenced, not copied | Eligible after holder/authority confirmation |

The evidence supports provisional classification of these files as original
project material. The project lead must still confirm the legal copyright-holder
name and authority to license all included classes, including AI-assisted
material. Until that confirmation, there is no effective `LICENSE` and no public
release authorization.

## Excluded because rights are not confirmed

| Material | Treatment |
|---|---|
| `data/category_summary.csv` | Excluded from the working tree and all candidate history; private checksum-preserved backup retained |
| `data/cluster_summary.csv` | Excluded from the working tree and all candidate history; private checksum-preserved backup retained |
| Historical aggregate-statistics script/test | Excluded because public reproduction would require the uncleared CSV files |
| Candidate Gold, review packets, reference answers, raw predictions/results | Excluded for confidentiality and/or unconfirmed redistribution rights |
| Private author assessments and recordings | Excluded; retained only as private evidence |

## Third-party components

Z3, pytest, setuptools, `actions/checkout`, and `actions/setup-python` are
external MIT-licensed dependencies or CI actions. They are referenced or
installed from upstream and are not vendored. Python's standard library is a
platform dependency and is not redistributed here. Details are in
`DEPENDENCY_LICENSES.md`.
