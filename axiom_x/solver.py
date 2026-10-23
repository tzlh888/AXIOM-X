from __future__ import annotations

import itertools
import time
from dataclasses import dataclass
from typing import Any

import z3

from .spec import FormalSpecification


@dataclass(frozen=True)
class SolverResult:
    status: str
    count: int | None
    solutions: frozenset[tuple[int, ...]] | None
    reason: str


@dataclass(frozen=True)
class ComparisonResult:
    status: str
    count_equal: bool | None
    set_equal: bool | None
    counterexample: dict[str, int] | None
    reason: str


def _satisfied(constraint: dict[str, Any], assignment: dict[str, int]) -> bool:
    kind = constraint["kind"]
    if kind == "equal":
        return assignment[constraint["variable"]] == constraint["value"]
    if kind == "not_equal":
        return assignment[constraint["variable"]] != constraint["value"]
    if kind == "less_than":
        return assignment[constraint["left"]] < assignment[constraint["right"]]
    if kind == "less_equal":
        return assignment[constraint["left"]] <= assignment[constraint["right"]]
    values = [assignment[name] for name in constraint["variables"]]
    if kind == "all_different":
        return len(values) == len(set(values))
    if kind == "sum_equal":
        return sum(values) == constraint["value"]
    if kind == "sum_at_least":
        return sum(values) >= constraint["value"]
    if kind == "sum_at_most":
        return sum(values) <= constraint["value"]
    if kind in {"count_equal", "count_at_least", "count_at_most"}:
        count = sum(value == constraint["value"] for value in values)
        return {
            "count_equal": count == constraint["count"],
            "count_at_least": count >= constraint["count"],
            "count_at_most": count <= constraint["count"],
        }[kind]
    if kind == "number_mod":
        number = 0
        for value in values:
            number = number * constraint["base"] + value
        return number % constraint["modulus"] == constraint["remainder"]
    raise AssertionError(kind)


def enumerate_specification(
    specification: FormalSpecification, *, max_assignments: int = 1_000_000
) -> SolverResult:
    if max_assignments < 1:
        return SolverResult("RESOURCE_LIMIT", None, None, "assignment budget must be positive")
    domains = [variable.domain for variable in specification.variables]
    solutions: set[tuple[int, ...]] = set()
    for inspected, values in enumerate(itertools.product(*domains), 1):
        if inspected > max_assignments:
            return SolverResult(
                "RESOURCE_LIMIT", None, None,
                f"enumeration exceeded {max_assignments} assignments",
            )
        assignment = dict(zip(specification.variable_names, values))
        if all(_satisfied(item, assignment) for item in specification.constraints):
            solutions.add(values)
    return SolverResult("COMPLETE", len(solutions), frozenset(solutions), "exhaustive finite enumeration")


def _z3_constraint(constraint: dict[str, Any], variables: dict[str, z3.IntNumRef]) -> z3.BoolRef:
    kind = constraint["kind"]
    if kind == "equal":
        return variables[constraint["variable"]] == constraint["value"]
    if kind == "not_equal":
        return variables[constraint["variable"]] != constraint["value"]
    if kind == "less_than":
        return variables[constraint["left"]] < variables[constraint["right"]]
    if kind == "less_equal":
        return variables[constraint["left"]] <= variables[constraint["right"]]
    values = [variables[name] for name in constraint["variables"]]
    if kind == "all_different":
        return z3.Distinct(values)
    if kind == "sum_equal":
        return z3.Sum(values) == constraint["value"]
    if kind == "sum_at_least":
        return z3.Sum(values) >= constraint["value"]
    if kind == "sum_at_most":
        return z3.Sum(values) <= constraint["value"]
    if kind in {"count_equal", "count_at_least", "count_at_most"}:
        count = z3.Sum([z3.If(value == constraint["value"], 1, 0) for value in values])
        return {
            "count_equal": count == constraint["count"],
            "count_at_least": count >= constraint["count"],
            "count_at_most": count <= constraint["count"],
        }[kind]
    if kind == "number_mod":
        number: Any = 0
        for value in values:
            number = number * constraint["base"] + value
        return number % constraint["modulus"] == constraint["remainder"]
    raise AssertionError(kind)


def _formula(specification: FormalSpecification, variables: dict[str, z3.IntNumRef]) -> z3.BoolRef:
    domain_terms = [
        z3.Or([variables[variable.name] == value for value in variable.domain])
        for variable in specification.variables
    ]
    return z3.And(*(domain_terms + [_z3_constraint(item, variables) for item in specification.constraints]))


def solve_z3(specification: FormalSpecification, *, timeout_ms: int = 5_000) -> SolverResult:
    if timeout_ms <= 0:
        return SolverResult("UNKNOWN", None, None, "timeout budget is non-positive")
    variables = {name: z3.Int(name) for name in specification.variable_names}
    solver = z3.Solver()
    solver.add(_formula(specification, variables))
    solutions: set[tuple[int, ...]] = set()
    deadline = time.monotonic() + timeout_ms / 1_000
    while True:
        remaining_ms = int((deadline - time.monotonic()) * 1_000)
        if remaining_ms <= 0:
            return SolverResult("UNKNOWN", None, None, "overall model-enumeration timeout")
        solver.set(timeout=remaining_ms)
        status = solver.check()
        if status == z3.unknown:
            return SolverResult("UNKNOWN", None, None, solver.reason_unknown())
        if status == z3.unsat:
            return SolverResult("COMPLETE", len(solutions), frozenset(solutions), "Z3 model enumeration")
        model = solver.model()
        values = tuple(model.eval(variables[name]).as_long() for name in specification.variable_names)
        solutions.add(values)
        solver.add(z3.Or([variables[name] != value for name, value in zip(specification.variable_names, values)]))


def compare_specifications(
    left: FormalSpecification, right: FormalSpecification, *, timeout_ms: int = 5_000
) -> ComparisonResult:
    if left.variable_names != right.variable_names or tuple(v.domain for v in left.variables) != tuple(v.domain for v in right.variables):
        return ComparisonResult("INCONCLUSIVE", None, None, None, "variable/domain mapping is not identical")
    if timeout_ms <= 0:
        return ComparisonResult("INCONCLUSIVE", None, None, None, "timeout budget is non-positive")
    variables = {name: z3.Int(name) for name in left.variable_names}
    solver = z3.Solver()
    solver.set(timeout=timeout_ms)
    solver.add(z3.Xor(_formula(left, variables), _formula(right, variables)))
    status = solver.check()
    if status == z3.unknown:
        return ComparisonResult("INCONCLUSIVE", None, None, None, solver.reason_unknown())
    left_result, right_result = solve_z3(left, timeout_ms=timeout_ms), solve_z3(right, timeout_ms=timeout_ms)
    count_equal = (
        left_result.count == right_result.count
        if left_result.count is not None and right_result.count is not None else None
    )
    if status == z3.unsat:
        return ComparisonResult("EQUIVALENT", count_equal, True, None, "no symmetric-difference witness exists")
    model = solver.model()
    witness = {name: model.eval(variables[name]).as_long() for name in left.variable_names}
    return ComparisonResult("DIFFERENT", count_equal, False, witness, "symmetric-difference witness found")


def compare_specifications_by_name(
    left: FormalSpecification, right: FormalSpecification, *, timeout_ms: int = 5_000
) -> ComparisonResult:
    """Compare under an exact-name bijection; order and domains may differ, renaming may not."""
    if set(left.variable_names) != set(right.variable_names):
        return ComparisonResult(
            "INCONCLUSIVE", None, None, None,
            "exact-name variable mapping cannot be proved",
        )
    if timeout_ms <= 0:
        return ComparisonResult("INCONCLUSIVE", None, None, None, "timeout budget is non-positive")
    names = tuple(sorted(left.variable_names))
    variables = {name: z3.Int(name) for name in names}
    solver = z3.Solver()
    solver.set(timeout=timeout_ms)
    solver.add(z3.Xor(_formula(left, variables), _formula(right, variables)))
    status = solver.check()
    if status == z3.unknown:
        return ComparisonResult("INCONCLUSIVE", None, None, None, solver.reason_unknown())
    left_result = solve_z3(left, timeout_ms=timeout_ms)
    right_result = solve_z3(right, timeout_ms=timeout_ms)
    count_equal = (
        left_result.count == right_result.count
        if left_result.count is not None and right_result.count is not None else None
    )
    if status == z3.unsat:
        return ComparisonResult(
            "EQUIVALENT", count_equal, True, None,
            "no symmetric-difference witness exists under exact-name mapping",
        )
    model = solver.model()
    witness = {name: model.eval(variables[name]).as_long() for name in names}
    return ComparisonResult(
        "DIFFERENT", count_equal, False, witness,
        "symmetric-difference witness found under exact-name mapping",
    )
