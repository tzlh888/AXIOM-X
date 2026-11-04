# Third-party notices

## Oscar Levin — DMOI3 textbook material

Oscar Levin, *Discrete Mathematics: An Open Introduction*, third edition, section 1.2. Copyright ©2013–2019 Oscar Levin. Original [section](https://discrete.openmathbooks.org/dmoi3/sec_counting-binom.html); [official colophon](https://discrete.openmathbooks.org/dmoi3/front-colophon.html). The book is licensed under [Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/) ([legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en)). No author or publisher endorsement is implied.

The following identifiable content group is distributed under CC BY-SA 4.0, including project contributions to the extracted/adapted material where copyright applies:

- `research_v5/sources/binom_excerpt.html`
- `research_v5/sources/colophon_excerpt.html`
- `research_v5/evidence/candidate_screen.json`
- `research_v5/evidence/natural_candidates.json`
- `research_v5/evidence/AI_FEASIBILITY_NOT_GOLD.json`
- `research_v5/evidence/reviewer_A_BLANK.json`
- `research_v5/evidence/reviewer_B_BLANK.json`
- `research_v5/reviewer_only/reviewer_A_BLANK.json`
- `research_v5/reviewer_only/reviewer_B_BLANK.json`
- `research_v5/reviewer_only/INSTRUCTIONS.md`

Changes: the release uses only the 13 previously recorded rendered exercise statements, with whitespace normalization and mathematical markup preserved as text. They come from human-authored exercise templates with fixed WebWork rendering parameters, not fresh manual annotation. All website presentation, scripts, styling, branding, solutions and interactive components are omitted. Questions are segmented with complete parent context for review; metadata and proposed finite encodings were added. All four original subquestions of the selected parent are retained. These automated encodings are not human Gold.

Attribution and license metadata are also repeated in the two HTML derivatives and the reviewer instructions. When redistributing an individual JSON file, retain the relevant author/title/source/license/change notice with it. Do not impose additional restrictions inconsistent with CC BY-SA. The project MIT license does not relicense this group.

Original complete webpage snapshots are not included. Their SHA-256 values and the derivative relationship are in [RELEASE_PROVENANCE.json](RELEASE_PROVENANCE.json). This release can reproduce the recorded statement extraction, not original website bytes.

## Runtime, build and test tools

Z3, pytest, setuptools, wheel and test dependencies retain their upstream licenses. They are installed rather than vendored. Version, source URL and artifact hashes appear in [DEPENDENCY_ARTIFACTS.json](DEPENDENCY_ARTIFACTS.json); a readable inventory is [DEPENDENCY_LICENSES.md](DEPENDENCY_LICENSES.md). GitHub Actions are upstream references, not bundled source.
