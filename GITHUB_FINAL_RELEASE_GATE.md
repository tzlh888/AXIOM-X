# AXIOM-X final GitHub release gate

What this repo does: it provides a bounded formal-specification audit prototype
for one researcher or developer running a local CLI. The public candidate
contains implementation, protocols, prompts, documentation, and synthetic
tests; it contains no research dataset, Gold, raw result, review packet, author
assessment, or recording.

Audit date: 2026-10-23 (Europe/Budapest)

## Gate result

**NOT READY**

All technically removable publication blockers identified in this audit have
been removed. Two decisions that only the project lead can make remain. No
remote repository, push, tag, Release, paid API call, or real-model call was
performed.

## Remaining P0 decisions

1. **P0 — legal holder and licensing authority.** The project lead must provide
   and approve the actual copyright-holder name and confirm authority to license
   every included original-content class, including AI-assisted material. The
   year is fixed at 2026. `LICENSE-PENDING.md` contains the complete standard MIT
   text, but there is intentionally no effective `LICENSE` file.
2. **P0 — final publication authorization.** After item 1 is resolved, the
   project lead must approve the final 43-file inventory and explicitly
   authorize GitHub publication.

There are **zero remaining technical P0 findings**. Rights for the two excluded
aggregate CSV files remain unresolved, but they are not a blocker for this
release package because neither file nor its dependent statistics script/test
is present anywhere in the candidate history.

## Candidate identity

- Input baseline preserved privately: `d846f657bbabcf04f3bb57a1ce2ac0f502c01e91`
- Audited minimal source commit: `42e392fc8bac929ed40b794a20d80a914cf9744f`
- Audited source tree: `b72fbd8d9e0b20e9a3823016159e828c36b4f6c2`
- Branch: `main`
- Remotes: none
- Source-history commit count: 1
- Final public file count after adding this report, inventory, and manifest: **43**
- Final packaging commit: supplied in the handoff because a commit cannot
  contain its own hash without changing that hash.

## Gate matrix

| Check | Result | Evidence |
|---|---|---|
| Minimal public allowlist | PASS | 43 files; no `data/`, `code/`, results, review, or private-evidence tree |
| Aggregate CSV exclusion | PASS | Both CSV blob IDs absent from the complete candidate object database |
| Old baseline exclusion | PASS | Baseline commit `d846f65…` does not exist in the new object database |
| Complete Git history scan | PASS | One new root history; no excluded path or private evidence object |
| Sensitive-information scan | PASS | No credential signature, private path, private key, or content email match |
| `.gitignore` defense in depth | PASS | All data, results, review material, credentials, recordings, and local artifacts ignored |
| Public tests without Gold/data | PASS | 41 passed; all fixtures are inline and synthetic |
| Fresh-environment reproduction | PASS | Fresh clone, Python 3.12.15, clean install, 41 passed |
| Deterministic public demo | PASS | SHA-256 `19e05de0da04b2ed36e849ab3d7a8a8c2547d793134c7f4e7055203b37d87204` |
| Dependency vulnerability scan | PASS | `pip-audit`: no known vulnerabilities in pinned requirements |
| Dependency-license review | PASS | Runtime, test, build, and CI dependencies are compatible and not vendored |
| Original-content class review | PASS / MANUAL AUTHORITY | Provenance-cleared by class; legal holder/authority still requires project-lead confirmation |
| Standard MIT draft | PASS / PENDING HOLDER | Full 2026 MIT text prepared; holder not invented; no effective `LICENSE` |
| README/reproduction accuracy | PASS | Claims only synthetic software/mechanism reproduction |
| SHA-256 release manifest | PASS | Covers every public file except the manifest itself |
| GitHub publication | NOT RUN | Prohibited until both P0 decisions are explicitly resolved |

## Rights review outcome

`COPYRIGHT_REVIEW.md` reviews six included classes separately: core source,
tests/synthetic fixtures, documentation, prompts, protocols/configuration, and
packaging/CI. Repository provenance and text review found them to be original
project material with disclosed AI assistance and found no vendored or
attributed copied source. This engineering finding does not replace the project
lead's legal confirmation of holder identity and licensing authority.

The following were excluded rather than licensed speculatively:

- `data/category_summary.csv`;
- `data/cluster_summary.csv`;
- `code/rc_stats.py` and its data-dependent regression test;
- historical aggregate reproduction claims and commands;
- all previously excluded Gold, review packets, reference answers, raw
  predictions/results, private assessments, and recordings.

## History and private-backup evidence

The baseline repository was preserved as a complete verified Git bundle before
the new history was built. Bundle SHA-256:

`fca10b0f8afb7ab1fe8390e1138b249550607a8345eb4946acbf8ee2b22db3cf`

The two aggregate CSV files were also copied to a dedicated private directory
with a verified two-entry manifest. Manifest-file SHA-256:

`ecef6879950be25a2e8ba053138f16de213b8ea0d70be7db3c25f3d429560578`

No private evidence was deleted.

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

## Ranked findings

**Must fix before publication**

1. **Approve the actual copyright holder and authority** (`LICENSE-PENDING.md`)
   - **What this is:** The full standard MIT text is ready with year 2026.
   - **Problem:** The actual holder name and authority have not been confirmed.
   - **Fix:** The project lead supplies the legal name, confirms all included
     classes, and approves creation of the effective `LICENSE`.
   - **If we skip it:** Publication would make an unapproved legal assertion.

2. **Approve the final package and publication** (`PUBLIC_RELEASE_FILES.txt`)
   - **What this is:** The candidate has an exact, hash-covered 43-file list.
   - **Problem:** No explicit final push authorization has been given.
   - **Fix:** The project lead reviews the list and explicitly authorizes GitHub publication.
   - **If we skip it:** A remote publication would violate the release gate.

## Verdict

**NOT READY.** The technical candidate is minimal, clean, tested, and free of
the uncleared aggregate data in both files and history. Only project-lead legal
and publication decisions remain.

Not checked: substantive legal advice, remote GitHub Actions, real-model
scientific validation, or external timestamping. Residual risk is limited to
legal authority and intentionally unperformed research, not a known failure of
the public software checks.
