# Deliberately excluded from public release

The following material is retained in a private local evidence backup but is not
present in this repository's working tree, commit history, refs, or reflogs:

- all historical V2 and V2.1 candidate Gold;
- all Gold review packets, reviewer ledgers, completion receipts, and disagreement ledgers;
- unpublished reference answers and Gold-derived specifications;
- original or raw experiment datasets not explicitly cleared for redistribution;
- `category_summary.csv` and `cluster_summary.csv`, pending confirmation of
  copyright and redistribution rights;
- raw model predictions, generated experiment outputs, and stored result bundles;
- private author assessments, technical-verification records, and recordings;
- credentials, environment files, API keys, tokens, and private machine paths;
- utilities whose sole purpose is to build private datasets, Gold packets, or
  private evidence manifests;
- the historical aggregate-statistics script and regression test that require
  the excluded CSV files;
- prior publication-audit manifests that described the excluded Gold-bearing tree.

`.gitignore` is defense in depth only. The release candidate was rebuilt as a new
Git repository from an explicit allowlist, so excluded material was never
committed to its history.
