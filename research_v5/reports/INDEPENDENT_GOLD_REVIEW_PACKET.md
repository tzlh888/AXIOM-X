# Independent Gold Review Packet

Status: packet preparation COMPLETED; reviews NOT PERFORMED. Completed reviewers: zero. No reference specification has been entered in either reviewer form.

Give each reviewer only `research_v5/reviewer_only/INSTRUCTIONS.md` and their own blank JSON in that directory. Do not send the complete candidate: `research_v5/evidence/AI_FEASIBILITY_NOT_GOLD.json` contains AI mappings and answers, and V4 records contain system decisions. Every reviewer form remains uncompleted; this is preparation, not human Gold.

The packet contains complete parent wording, each subquestion, source attribution, finite-domain context, empty formal specification fields, empty ambiguity/rationale fields, and disagreement notes. Domain context is an AI-proposed organizational convention, which reviewers must independently verify. It is not a supplied Gold constraint set.

Two qualified reviewers should independently read the four tasks, construct finite-domain specifications, justify lossless membership mappings, classify ambiguity, and sign their human/independence declaration before seeing each other's work. Do not use LLM-generated answers or AXIOM-X output. Published answer keys should not replace semantic annotation.

After both submissions are hashed and locked, a coordinator compares their formal solution sets using Python and Z3. Equivalence is necessary but not sufficient: reviewers must also agree on the intended reading and variable map. Disagreement records must preserve both original versions, the disputed text, each rationale, and any semantic witness. A third qualified adjudicator resolves disagreements with a written rationale. Unresolved items remain unresolved and are excluded from FCR/selective-risk denominators without replacement.

Freeze final Gold, both original reviews, reviewer identities or stable pseudonyms with verifiable human attestation, timestamps, qualification/relationship declarations, adjudication record, and SHA-256 hashes before model generation. Never change Gold in response to model/system output. Corrections require a dated new version and separate analysis.

If only one independent reviewer is available, the protocol permits a separately disclosed pilot after their freeze. It cannot be described as dual review or adjudicated Gold. With zero reviewers, model evaluation remains blocked. No reviewer was contacted automatically.
