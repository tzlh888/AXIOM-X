from pathlib import Path

from research_v3.audit_external_datasets import COUNT_TARGET, FINITE_DOMAIN, FOL_QUANTIFIER


def test_external_compatibility_patterns_do_not_treat_open_fol_as_axiom_dsl() -> None:
    assert FOL_QUANTIFIER.search("∀x (Bird(x) → Fly(x))")
    assert COUNT_TARGET.search("How many ordered assignments are possible?")
    assert FINITE_DOMAIN.search("x ranges over integers 0 through 4")
    assert not COUNT_TARGET.search("Every bird can fly.")
