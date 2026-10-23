# AXIOM-X final GitHub release gate

What this repo does: it provides a bounded formal-specification audit prototype
for one researcher or developer running a local CLI. The public candidate
contains implementation, protocols, prompts, documentation, and inline
synthetic tests; it contains no research dataset, Gold, raw result, review
packet, private author assessment, or recording.

Audit date: 2026-10-23 (Europe/Budapest)

## Gate result

**READY FOR FINAL HUMAN APPROVAL**

The candidate has no known technical P0 blocker. It is not yet authorized for
GitHub publication because the project lead must review the final file list and
explicitly approve Push/Tag/Release. No remote operation, paid API call, or
real-model call was performed.

## License result

- License: MIT License
- Copyright: `Copyright (c) 2026 TANG ZELUOHE`
- Canonical text check: exact match to the SPDX/OSI standard MIT text after
  substituting the confirmed year and holder
- `LICENSE` SHA-256:
  `3af281122766e24f57aaa13d6eb0f4d2b8209a3e64d198c48b8eec5962a04a5c`
- `LICENSE-PENDING.md`: absent from the final working tree

The holder name was not used as blanket evidence for every file. Six included
material classes were reviewed separately in `COPYRIGHT_REVIEW.md`. The project
MIT grant applies only to copyright interests held by TANG ZELUOHE. Third-party
dependencies retain their upstream licenses, and materials with unconfirmed
redistribution rights remain excluded.

## Candidate identity

- License-configured source commit: `4943e2ba77bf38e690814c6aa9d3998dff3b7da3`
- Source tree: `3f64bafff0770698e67051b7e455173561aa5580`
- Branch: `main`
- Remotes: none
- Source-history commit count before this audit artifact: 3
- Final public file count: **43**
- Final packaging commit: supplied in the handoff because a Git commit cannot
  contain its own hash without changing that hash

## Gate matrix

| Check | Result | Evidence |
|---|---|---|
| Formal MIT `LICENSE` | PASS | Standard text, confirmed 2026 holder line, byte comparison passed |
| Material-class rights review | PASS | Six included original-content classes reviewed individually |
| Third-party boundary | PASS | Dependencies are not vendored and retain upstream licenses |
| Uncleared aggregate CSV exclusion | PASS | Both CSV blob IDs absent from complete candidate object database |
| Gold/private-material exclusion | PASS | No private evidence path or blob in complete candidate history |
| Full Git history scan | PASS | All reachable commits and named objects checked |
| Sensitive-information scan | PASS | No credential signature, private path, private key, or content email match |
| Public tests | PASS | 41 passed without Gold or research data |
| Deterministic demo | PASS | SHA-256 `19e05de0da04b2ed36e849ab3d7a8a8c2547d793134c7f4e7055203b37d87204` |
| Dependency vulnerability scan | PASS | `pip-audit`: no known vulnerabilities in pinned requirements |
| README/reproduction boundary | PASS | Claims only public synthetic software/mechanism reproduction |
| SHA-256 release manifest | PASS | Covers every final public file except the manifest itself |
| Core algorithm unchanged | PASS | All 12 `axiom_x/*.py` files byte-identical to the pre-license baseline |
| GitHub Push/Tag/Release | NOT RUN | Awaiting explicit project-lead approval |

## Rights and exclusion boundary

Included under the project MIT license after class-level provenance review:

- original `axiom_x` implementation;
- tests and inline synthetic fixtures;
- project documentation;
- project prompts;
- protocols, schemas, and run configuration;
- packaging and CI configuration.

Not relicensed or published:

- Z3, pytest and transitive test/build dependencies, or GitHub Actions code;
- `data/category_summary.csv` and `data/cluster_summary.csv`;
- the aggregate-statistics script and data-dependent regression test;
- V1/V2/V2.1 private datasets, Gold, review packets, reference answers, raw
  predictions/results, author assessments, and recordings.

The two aggregate CSV files and all prior private evidence remain in local
checksum-preserved backups outside the public candidate.

## Reproducibility boundary

Publicly reproducible:

- schema and bounded-input validation;
- Python/Z3 finite-solver agreement;
- specification comparison and isolation controls on inline synthetic fixtures;
- frozen-payload and review-receipt integrity checks using temporary test data;
- deterministic synthetic demo.

Not publicly reproducible:

- historical aggregate-statistics recomputation;
- V1/V2/V2.1 private datasets, Gold, raw results, or review packets;
- a completed natural LLM experiment;
- independent Gold validation or a pristine held-out study.

## Final audit finding

Healthy. Nothing technical to fix before the final human approval step.

## Remaining manual approval

The project lead must inspect `PUBLIC_RELEASE_FILES.txt` and explicitly state
that this exact candidate may be published. That future approval authorizes the
remote action; this preparation does not infer it and performs no Push, Tag, or
Release.

## Verdict

**READY FOR FINAL HUMAN APPROVAL; NOT YET AUTHORIZED FOR PUBLICATION.**

Not checked: substantive legal advice, remote GitHub Actions, real-model
scientific validation, or external timestamping. Residual risk is limited to
the normal legal effect of the holder's grant and research intentionally kept
outside this public package.
