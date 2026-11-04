# Method and version scope

A formal specification declares named finite integer domains, supported constraints and a count-solution target. Python enumerates the Cartesian product; Z3 enumerates models with full-assignment blocking clauses until UNSAT or an incomplete status. Exact-name set comparison distinguishes equivalent encodings from changed solution sets. Unproved variable renaming remains inconclusive.

The B2.1 audit compares a candidate against semantics extracted by the fixed controlled-language parser. Unsupported or incomplete text, unknown solving and unproved mapping lead to ABSTAIN. A set mismatch can supply a counterexample. ACCEPT is conditional on the extracted formal semantics and implemented checks; it is not independent validation of intended natural-language meaning. The older two-specification audit only establishes formal/peer agreement.

V3 provides corrected controlled-model evidence and a separately identified post-hoc auxiliary analysis. V4 provides a frozen injected-error challenge and separate model-generated specifications on controlled inputs. V5 corrects mechanism attribution and independence claims, adds internal reference checks and prepares a gated independent-review packet. It supplies no new model-generation or natural-language effectiveness result.

The release preserves original V3/V4 evidence and test bytes. Packaging changes are confined to public documentation, source-excerpt handling and public verification metadata. They do not alter a solver algorithm or an experimental result. See [provenance](RELEASE_PROVENANCE.md), [metrics](METRICS.md) and [limitations](LIMITATIONS.md).
