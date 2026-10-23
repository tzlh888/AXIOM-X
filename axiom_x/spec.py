from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


class SpecificationError(ValueError):
    """A specification is invalid or exceeds the public safety budget."""


SUPPORTED_CONSTRAINTS = {
    "all_different",
    "equal",
    "not_equal",
    "sum_equal",
    "count_equal",
    "number_mod",
    "less_than",
    "less_equal",
    "sum_at_least",
    "sum_at_most",
    "count_at_least",
    "count_at_most",
}


@dataclass(frozen=True)
class Variable:
    name: str
    domain: tuple[int, ...]


@dataclass(frozen=True)
class FormalSpecification:
    problem_id: str
    variables: tuple[Variable, ...]
    constraints: tuple[dict[str, Any], ...]
    target: str
    source: str
    generation_id: str
    verification_status: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FormalSpecification":
        if not isinstance(value, dict):
            raise SpecificationError("specification must be an object")
        required = {
            "problem_id", "variables", "constraints", "target", "source",
            "generation_id", "verification_status",
        }
        missing = sorted(required - value.keys())
        if missing:
            raise SpecificationError(f"missing fields: {', '.join(missing)}")
        if value["target"] != "count_solutions":
            raise SpecificationError("only target=count_solutions is supported")
        if value["verification_status"] not in {"UNVERIFIED", "VALIDATED"}:
            raise SpecificationError("invalid verification_status")
        variables_raw = value["variables"]
        if not isinstance(variables_raw, list) or not 1 <= len(variables_raw) <= 8:
            raise SpecificationError("variables must contain 1..8 items")
        variables: list[Variable] = []
        for raw in variables_raw:
            if not isinstance(raw, dict) or set(raw) != {"name", "domain"}:
                raise SpecificationError("each variable needs exactly name and domain")
            name, domain = raw["name"], raw["domain"]
            if not isinstance(name, str) or not name.isidentifier():
                raise SpecificationError("variable name must be a Python-style identifier")
            if not isinstance(domain, list) or not 1 <= len(domain) <= 20:
                raise SpecificationError(f"{name}: domain must contain 1..20 values")
            if any(type(item) is not int for item in domain) or len(set(domain)) != len(domain):
                raise SpecificationError(f"{name}: domain must contain unique integers")
            variables.append(Variable(name, tuple(domain)))
        names = [variable.name for variable in variables]
        if len(set(names)) != len(names):
            raise SpecificationError("variable names must be unique")
        if math.prod(len(variable.domain) for variable in variables) > 1_000_000:
            raise SpecificationError("search space exceeds 1,000,000 assignments")
        constraints_raw = value["constraints"]
        if not isinstance(constraints_raw, list) or len(constraints_raw) > 40:
            raise SpecificationError("constraints must be a list of at most 40 items")
        constraints = tuple(_validate_constraint(item, set(names)) for item in constraints_raw)
        for field in ("problem_id", "source", "generation_id"):
            if not isinstance(value[field], str) or not value[field].strip():
                raise SpecificationError(f"{field} must be a non-empty string")
        return cls(
            problem_id=value["problem_id"], variables=tuple(variables),
            constraints=constraints, target=value["target"], source=value["source"],
            generation_id=value["generation_id"],
            verification_status=value["verification_status"],
        )

    @property
    def variable_names(self) -> tuple[str, ...]:
        return tuple(variable.name for variable in self.variables)

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "variables": [
                {"name": variable.name, "domain": list(variable.domain)}
                for variable in self.variables
            ],
            "constraints": [dict(item) for item in self.constraints],
            "target": self.target,
            "source": self.source,
            "generation_id": self.generation_id,
            "verification_status": self.verification_status,
        }


def _variables(value: Any, names: set[str]) -> list[str]:
    if not isinstance(value, list) or not value or any(item not in names for item in value):
        raise SpecificationError("constraint variables must be a non-empty list of known names")
    if len(set(value)) != len(value):
        raise SpecificationError("constraint variable list contains duplicates")
    return value


def _validate_constraint(value: Any, names: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("kind") not in SUPPORTED_CONSTRAINTS:
        raise SpecificationError("unsupported constraint")
    item = dict(value)
    kind = item["kind"]
    allowed = {
        "equal": {"kind", "variable", "value"},
        "not_equal": {"kind", "variable", "value"},
        "less_than": {"kind", "left", "right"},
        "less_equal": {"kind", "left", "right"},
        "all_different": {"kind", "variables"},
        "sum_equal": {"kind", "variables", "value"},
        "sum_at_least": {"kind", "variables", "value"},
        "sum_at_most": {"kind", "variables", "value"},
        "count_equal": {"kind", "variables", "value", "count"},
        "count_at_least": {"kind", "variables", "value", "count"},
        "count_at_most": {"kind", "variables", "value", "count"},
        "number_mod": {"kind", "variables", "base", "modulus", "remainder"},
    }[kind]
    if set(item) != allowed:
        raise SpecificationError(f"{kind} fields must be exactly {sorted(allowed)}")
    if kind in {"equal", "not_equal"}:
        if item.get("variable") not in names or type(item.get("value")) is not int:
            raise SpecificationError(f"invalid {kind} constraint")
    elif kind in {"less_than", "less_equal"}:
        if item.get("left") not in names or item.get("right") not in names:
            raise SpecificationError("invalid less_than constraint")
    elif kind == "all_different":
        _variables(item.get("variables"), names)
    elif kind in {"sum_equal", "sum_at_least", "sum_at_most"}:
        _variables(item.get("variables"), names)
        if type(item.get("value")) is not int:
            raise SpecificationError("sum_equal value must be an integer")
    elif kind in {"count_equal", "count_at_least", "count_at_most"}:
        _variables(item.get("variables"), names)
        if type(item.get("value")) is not int or type(item.get("count")) is not int:
            raise SpecificationError("count_equal value/count must be integers")
    elif kind == "number_mod":
        _variables(item.get("variables"), names)
        if type(item.get("base")) is not int or not 2 <= item["base"] <= 36:
            raise SpecificationError("number_mod base must be in 2..36")
        if type(item.get("modulus")) is not int or item["modulus"] <= 0:
            raise SpecificationError("number_mod modulus must be positive")
        if type(item.get("remainder")) is not int:
            raise SpecificationError("number_mod remainder must be an integer")
    return item
