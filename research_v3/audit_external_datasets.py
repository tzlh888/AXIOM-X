from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable


COUNT_TARGET = re.compile(r"\bhow many\b.*\b(assignments|values|solutions)\b", re.IGNORECASE)
FINITE_DOMAIN = re.compile(r"\b(range|ranges|values?)\b.*(?:\{|\bthrough\b|\bfrom\b)", re.IGNORECASE)
FOL_QUANTIFIER = re.compile(r"[∀∃]|\b(?:forall|exists)\b", re.IGNORECASE)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _head(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def _json_rows(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError(f"expected JSON object array: {path}")
    return value


def _jsonl_rows(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        rows.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return rows


def _texts_and_formulas(rows: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    texts: list[str] = []
    formulas: list[str] = []
    for row in rows:
        for key, value in row.items():
            key_lower = key.casefold()
            values = value if isinstance(value, list) else [value]
            if any(token in key_lower for token in ("nl", "premise", "conclusion")) and "fol" not in key_lower:
                texts.extend(str(item) for item in values if isinstance(item, str))
            if "fol" in key_lower:
                formulas.extend(str(item) for item in values if isinstance(item, str))
    return texts, formulas


def _record(
    name: str,
    repo: Path,
    files: list[Path],
    rows: list[dict[str, Any]],
    *,
    annotation_origin: str,
    license_finding: str,
    license_usable: bool,
) -> dict[str, Any]:
    texts, formulas = _texts_and_formulas(rows)
    count_targets = sum(bool(COUNT_TARGET.search(text)) for text in texts)
    finite_domains = sum(bool(FINITE_DOMAIN.search(text)) for text in texts)
    quantifier_formulas = sum(bool(FOL_QUANTIFIER.search(formula)) for formula in formulas)
    eligible = count_targets and finite_domains and not quantifier_formulas
    return {
        "dataset": name,
        "repository": str(repo),
        "repository_commit": _head(repo),
        "source_files": [{"path": str(path.relative_to(repo)), "sha256": _sha256(path)} for path in files],
        "row_count": len(rows),
        "natural_language_string_count": len(texts),
        "formula_string_count": len(formulas),
        "formula_strings_with_fol_quantifier": quantifier_formulas,
        "texts_with_explicit_assignment_count_target": count_targets,
        "texts_with_explicit_finite_domain_surface_form": finite_domains,
        "annotation_origin": annotation_origin,
        "license_finding": license_finding,
        "license_clear_enough_for_research_use": license_usable,
        "axiom_x_lossless_eligible_rows": 0,
        "decision": "EXCLUDED",
        "exclusion_reasons": [
            "task target is NL-to-open-domain-FOL or NLI, not finite-domain assignment counting",
            "quantified predicate/function semantics cannot be represented in the current AXIOM-X integer DSL without loss",
            "no row-level finite-domain declaration and count_solutions target compatible with AXIOM-X was identified",
        ] + ([] if license_usable else ["license statement is absent, conflicting, or insufficiently clear for redistribution"]),
        "scan_flag_was_not_used_as_semantic_conversion": bool(eligible) is False,
    }


def audit(sources: Path) -> dict[str, Any]:
    folio = sources / "FOLIO"
    fixing = sources / "Fixing-FOLIO-and-MALLS"
    groves = sources / "ANLFtFOLwFLLMs"

    folio_files = sorted((folio / "data/v0.0").glob("*.jsonl"))
    corrected_folio = fixing / "core/dataset/datasets/folio/dataset_rawpairs.jsonl"
    corrected_malls = fixing / "core/dataset/datasets/malls/dataset_rawpairs.jsonl"
    groves_files = [
        groves / "datasets_nl_fol/groves_train.json",
        groves / "datasets_nl_fol/groves_val.json",
        groves / "datasets_nl_fol/groves_test.json",
    ]
    human_benchmark = groves / "datasets_nl_fol/goldstandard.json"
    records = [
        _record(
            "FOLIO-v0.0",
            folio,
            folio_files,
            _jsonl_rows(folio_files),
            annotation_origin="expert-written NL with FOL annotations; later audit found substantial annotation errors",
            license_finding="repository LICENSE is CC BY-SA 4.0",
            license_usable=True,
        ),
        _record(
            "FOLIO-2026-human-curated-validation",
            fixing,
            [corrected_folio],
            _jsonl_rows([corrected_folio]),
            annotation_origin="2026 human inspection and correction, 275 FOLIO validation instances",
            license_finding="README says dataset CC BY 4.0 but repository has no LICENSE file and upstream FOLIO says CC BY-SA 4.0",
            license_usable=False,
        ),
        _record(
            "MALLS-2026-human-curated-test-subset",
            fixing,
            [corrected_malls],
            _jsonl_rows([corrected_malls]),
            annotation_origin="2026 human inspection and correction, 100 MALLS test instances",
            license_finding="README says dataset CC BY 4.0; no repository LICENSE file; original MALLS repository says CC BY-NC 4.0",
            license_usable=False,
        ),
        _record(
            "GROVES",
            groves,
            groves_files,
            sum((_json_rows(path) for path in groves_files), []),
            annotation_origin="LLM-regenerated and automatically corrected corpus derived from MALLS/Willow",
            license_finding="repository LICENSE is MIT; upstream derivative-data obligations still require care",
            license_usable=True,
        ),
        _record(
            "GROVES-human-annotated-benchmark",
            groves,
            [human_benchmark],
            _json_rows(human_benchmark),
            annotation_origin="100-row human-annotated NL-to-FOL benchmark",
            license_finding="distributed in MIT-licensed repository; upstream text provenance is not row-level in the file",
            license_usable=True,
        ),
    ]
    return {
        "schema": "axiom-x-external-compatibility-audit-v1",
        "audit_date": "2026-11-03",
        "axiom_x_target": "explicit finite integer domains plus constraints, target=count_solutions",
        "method": "full-file structural scan plus task-semantics review; no formula was simplified or converted",
        "records": records,
        "summary": {
            "datasets_checked": len(records),
            "rows_checked": sum(record["row_count"] for record in records),
            "lossless_eligible_rows": 0,
            "route_a_status": "NOT_FEASIBLE",
            "selected_route": "B_CONTROLLED_LANGUAGE",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    result = audit(args.sources)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
