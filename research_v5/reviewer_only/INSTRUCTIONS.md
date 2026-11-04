# Independent annotation instructions

Oscar Levin, *Discrete Mathematics: An Open Introduction*, third edition, exercise 1.2.3. Source: https://discrete.openmathbooks.org/dmoi3/sec_counting-binom.html#ww-binom-subsets-vs . Copyright Oscar Levin; CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/ . Source statement extracted from HTML with solutions removed; whitespace normalized and subquestions grouped with original context.

Complete only your own A or B JSON. Do not inspect the other reviewer, model predictions, AXIOM-X decisions, AI-proposed references, or worked answers. Use your mathematical judgment without generative AI. Declare your identity or stable human-verifiable pseudonym, qualifications, relationship to the project, date, and independent-human attestation in the top-level fields. Additional metadata fields are permitted. Do not mark a review complete if you cannot make that declaration.

Read the full parent before each subquestion. Independently verify that membership indicators preserve the counted objects and their ordering/identity. Each indicator refers to one of the four elements in order; a value of 1 means included. If this convention alters the meaning, flag it rather than conforming to the suggested mapping.

Write one finite formal specification per question. Required fields: problem_id, variables (name and explicit integer domain), constraints, target=count_solutions, source=human-review-A or B, generation_id (unique), verification_status=UNVERIFIED. The review will only become validated after comparison/adjudication. Allowed limits: 1–8 variables, 1–20 unique integers per domain, Cartesian space at most 1,000,000, at most 40 constraints.

Allowed constraint forms:

- all_different: variables
- equal / not_equal: variable, value
- less_than / less_equal: left, right
- sum_equal / sum_at_least / sum_at_most: variables, value
- count_equal / count_at_least / count_at_most: variables, value, count
- number_mod: variables (ordered), base, modulus, remainder

Each constraint has a `kind` plus the listed fields; their conjunction defines the model. Number_mod interprets the ordered variable values as base digits. An empty constraint list is valid. Do not supply a known answer as a substitute for the set of assignments. Do not invent constraints to force a count. If you cannot express the exact meaning, set the reference to null, record UNSUPPORTED, and explain.

Classify ambiguity as CLEAR, CONTEXT_REQUIRED, MULTIPLE_READINGS, UNSUPPORTED, or UNRESOLVED. Provide a rationale and the object-to-assignment bijection. Leave disagreement_note empty until original submissions have been frozen. Preserve any uncertainty rather than guessing.

Return the completed original to the coordinator. The coordinator will hash both originals before comparison. Neither reviewer should change an original after seeing the other's work. Any adjudication must record both readings, their differences, a written resolution, and a new frozen version before model generation. One reviewer is disclosed as a single-reviewer pilot; no reviewers means no evaluation.
