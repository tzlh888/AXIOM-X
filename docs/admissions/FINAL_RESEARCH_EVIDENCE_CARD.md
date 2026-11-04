# AXIOM-X — Research Evidence Card

**DRAFT FOR REVIEW · 2027 undergraduate application portfolio · V5 interpretation**

**Question.** Can finite-model verification expose semantic errors in language-model-generated counting specifications?

**Method.** Python enumeration and Z3 check finite solution sets against specifications parsed from supported controlled text. Mismatches yield counterexamples; unsupported cases prompt abstention.

**Evidence.** A frozen 96-case controlled challenge contained 72 injected errors across nine mechanisms, 16 correct controls and eight ambiguous cases. AXIOM-X rejected all 72 errors, accepted eight controls and abstained on 16 cases. Separately, two local models each received 48 controlled tasks. One produced four semantic errors; AXIOM-X and a simple distinctness/nonzero rule both rejected all four. The other produced no semantic-error opportunities.

**Meaning.** These are bounded mechanism results. Repeated families and parser-conditioned eligibility limit independence. The four errors involved fixed assignments and omitted constraints on modulo-themed tasks. Neither superiority to the simple rule on model errors nor generalization to unrestricted natural language is established. Independent human reference validation remains incomplete.

**Contribution disclosure.** Engineering, experiments and reporting received substantial AI assistance. They do not establish unaided applicant implementation or sole algorithm authorship.

Basis: local V5 `4ba750d`; [claim verification](SCIENTIFIC_CLAIMS_VERIFICATION.md). Publication pending review.
