# Metric definitions

For a fixed strategy, let A, R and U denote ACCEPT, REJECT and ABSTAIN, with N=A+R+U. Let E be the independently classified semantic-error opportunities in the relevant reference comparison, C the known-correct specifications, and FA the erroneous ACCEPTs. In the controlled studies references are automatic, not independent human Gold.

- Specification FCR = FA/E. E=0 means N/A, never artificial zero.
- Acceptance coverage = A/N; decision coverage = (A+R)/N; abstention rate = U/N.
- Specification selective risk = FA / semantically resolved ACCEPTs. UNKNOWN/UNRESOLVED ACCEPTs are excluded and must be explicitly counted.
- Error detection = erroneous REJECTs/E. Abstaining on an error is not counted as detection.
- False rejection = correct REJECTs/C; correct abstention = correct ABSTAINs/C.
- Answer FCR, where reported in historical analyses, uses actually wrong answers as its own denominator. It is distinct from specification FCR. A correct count does not prove equal solution sets.

The V4 challenge has N=96, E=72, C=16 and eight ambiguous cases. AXIOM-X gives A=8, R=72, U=16: FCR 0/72, acceptance coverage 8.33%, decision coverage 83.33%, selective risk 0/8. On the weaker model, 39 correct + four errors + one valid UNKNOWN + four invalid outputs sum to 48; AXIOM-X gives 35/4/9, FCR 0/4 and selective risk 0/35. On the stronger model, E=0 and FCR is N/A.

The saved `unresolved` field counts only label UNRESOLVED; it does not include model UNKNOWN or invalid outputs. Use row records and the explicit category counts rather than interpreting that field as all missing reference relations.

Wilson 95% intervals and exact two-sided McNemar probabilities are nominal row-level summaries. The reported FCR upper bounds are 5.07% for 0/72 and 48.99% for 0/4; paired probabilities versus Accept-all are 2^-71 and 0.125 respectively. Repeated families, parameter settings and shared model tasks limit independence. These figures do not quantify reliability in a natural-language population or prove zero underlying risk.
