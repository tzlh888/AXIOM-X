# AXIOM-X

AXIOM-X is a bounded formal-specification audit prototype for finite counting
problems. This repository is a source-only public-release candidate. It contains
the implementation, protocols, and tests built from inline synthetic fixtures.
It deliberately contains no aggregate research data, candidate Gold, review
packet, reference answer, raw prediction, private author assessment, or recording.

## Research status

This repository does **not** establish real-model reliability.

- The publication-grade natural LLM experiment is not complete; this public
  candidate contains zero natural-LLM result rows.
- Independent, blind human validation of Gold is not complete.
- A pristine independently sourced held-out set is not complete.
- The available evidence is synthetic mechanism and software evidence only. It
  demonstrates bounded parsing, solver agreement, isolation controls, and known
  failure mechanisms; it does not validate performance on real models or natural
  data.
- Historical V1/V2/V2.1 results and candidate Gold are not included here and
  cannot be reproduced from this public repository.

See [LIMITATIONS.md](LIMITATIONS.md), [DISCLOSURE.md](DISCLOSURE.md), and
[REPRODUCE.md](REPRODUCE.md) before interpreting any output.

## Public reproduction

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-extension.txt
python -m pip install --no-deps .
pytest -q
python -m axiom_x.demo
```

The tests require no API credential and no bundled Gold. Any real-provider path
fails closed when credentials and frozen run prerequisites are absent.

## Repository boundary

The public tree is intentionally small. `PRIVATE_EXCLUSIONS.md` records the
excluded categories. The old Gold-bearing candidate and its Git history are
retained only in a local private backup outside this repository.

## License status

MIT is the proposed project license, but it is **not yet granted**. The project
lead must first approve the exact license text, copyright year, copyright holder,
and the rights inventory in `COPYRIGHT_REVIEW.md`. Until that happens, this
candidate has no `LICENSE` file and must not be described as MIT-licensed or
open source. `LICENSE-PENDING.md` contains the complete standard MIT text as a
non-operative draft with an unfilled holder field.

No GitHub repository, push, or release has been created by this preparation.
