from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .spec import FormalSpecification


@dataclass(frozen=True)
class SemanticParse:
    status: str
    specification: FormalSpecification | None
    triggered_checks: tuple[str, ...]
    reason: str


def _specification(
    problem_id: str,
    variables: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
) -> FormalSpecification:
    return FormalSpecification.from_dict({
        "problem_id": problem_id,
        "variables": variables,
        "constraints": constraints,
        "target": "count_solutions",
        "source": "v2.1-deterministic-public-text-parser",
        "generation_id": f"semantic-v2.1-{problem_id}",
        "verification_status": "UNVERIFIED",
    })


def _range_variables(names: tuple[str, ...], lower: int, upper: int) -> list[dict[str, Any]]:
    if upper < lower:
        raise ValueError("domain upper bound is below lower bound")
    return [{"name": name, "domain": list(range(lower, upper + 1))} for name in names]


def _complete(
    problem_id: str,
    variables: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    checks: list[str],
) -> SemanticParse:
    return SemanticParse(
        "COMPLETE",
        _specification(problem_id, variables, constraints),
        tuple(checks),
        "entire problem matched a fixed high-precision grammar",
    )


def parse_public_problem(problem_id: str, text: str) -> SemanticParse:
    """Parse only fully matched benchmark grammars; partial keyword matches are never accepted."""
    # shortcut: bounded controlled-language rewrites only; ambiguous/free-form prose must abstain.
    text = re.sub(
        r"Require ([A-Za-z_]\w*) to be strictly less than ([A-Za-z_]\w*)",
        r"Require \1 < \2",
        text.strip(),
    )
    text = re.sub(
        r"Require ([A-Za-z_]\w*) to be less than or equal to ([A-Za-z_]\w*)",
        r"Require \1 <= \2",
        text,
    )
    text = text.replace("No two variables have the same value.", "All variables are distinct.")
    match = re.fullmatch(
        r"Variables (?P<names>[A-Za-z_]\w*(?:, [A-Za-z_]\w*)+) each range over integers "
        r"(?P<lower>-?\d+) through (?P<upper>-?\d+)\. All variables are distinct\. Their sum is "
        r"exactly (?P<total>-?\d+)\. How many assignments satisfy all conditions\?",
        text,
    )
    if match:
        names = tuple(match.group("names").split(", "))
        lower, upper, total = (int(match.group(key)) for key in ("lower", "upper", "total"))
        return _complete(
            problem_id,
            _range_variables(names, lower, upper),
            [
                {"kind": "all_different", "variables": list(names)},
                {"kind": "sum_equal", "variables": list(names), "value": total},
            ],
            ["VARIABLE_DOMAINS", "ALL_DIFFERENT", "SUM_EQUAL"],
        )

    match = re.fullmatch(
        r"Variables (?P<names>[A-Za-z_]\w*(?:, [A-Za-z_]\w*)+) each range over integers "
        r"(?P<lower>-?\d+) through (?P<upper>-?\d+)\. All variables are distinct\. "
        r"How many assignments are possible\?",
        text,
    )
    if match:
        names = tuple(match.group("names").split(", "))
        lower, upper = int(match.group("lower")), int(match.group("upper"))
        return _complete(
            problem_id,
            _range_variables(names, lower, upper),
            [{"kind": "all_different", "variables": list(names)}],
            ["VARIABLE_DOMAINS", "ALL_DIFFERENT"],
        )

    match = re.fullmatch(
        r"Variables (?P<left>[A-Za-z_]\w*) and (?P<right>[A-Za-z_]\w*) each range over integers "
        r"(?P<lower>-?\d+) through (?P<upper>-?\d+)\. Require (?P=left) (?P<operator><=|<) (?P=right)"
        r"(?P<nonzero>, and (?P=left) is nonzero)?\. How many (?:ordered )?assignments are possible\?",
        text,
    )
    if match:
        names = (match.group("left"), match.group("right"))
        lower, upper = int(match.group("lower")), int(match.group("upper"))
        inequality_kind = "less_equal" if match.group("operator") == "<=" else "less_than"
        constraints: list[dict[str, Any]] = [
            {"kind": inequality_kind, "left": names[0], "right": names[1]}
        ]
        checks = [
            "VARIABLE_DOMAINS",
            "NONSTRICT_INEQUALITY" if inequality_kind == "less_equal" else "STRICT_INEQUALITY",
        ]
        if match.group("nonzero"):
            constraints.append({"kind": "not_equal", "variable": names[0], "value": 0})
            checks.append("EXCLUSION_NONZERO")
        return _complete(problem_id, _range_variables(names, lower, upper), constraints, checks)

    match = re.fullmatch(
        r"Variables (?P<left>[A-Za-z_]\w*) and (?P<right>[A-Za-z_]\w*) each range over integers "
        r"(?P<lower>-?\d+) through (?P<upper>-?\d+)\. Their sum is at least (?P<minimum>-?\d+) "
        r"and at most (?P<maximum>-?\d+)\. How many ordered assignments satisfy both bounds\?",
        text,
    )
    if match:
        names = (match.group("left"), match.group("right"))
        lower, upper = int(match.group("lower")), int(match.group("upper"))
        minimum, maximum = int(match.group("minimum")), int(match.group("maximum"))
        return _complete(
            problem_id,
            _range_variables(names, lower, upper),
            [
                {"kind": "sum_at_least", "variables": list(names), "value": minimum},
                {"kind": "sum_at_most", "variables": list(names), "value": maximum},
            ],
            ["VARIABLE_DOMAINS", "SUM_LOWER_BOUND", "SUM_UPPER_BOUND"],
        )

    match = re.fullmatch(
        r"Variables (?P<left>[A-Za-z_]\w*) and (?P<right>[A-Za-z_]\w*) each range over integers "
        r"(?P<lower>-?\d+) through (?P<upper>-?\d+)\. Their sum is at most (?P<maximum>-?\d+)\. "
        r"How many assignments are possible\?",
        text,
    )
    if match:
        names = (match.group("left"), match.group("right"))
        lower, upper = int(match.group("lower")), int(match.group("upper"))
        maximum = int(match.group("maximum"))
        return _complete(
            problem_id,
            _range_variables(names, lower, upper),
            [{"kind": "sum_at_most", "variables": list(names), "value": maximum}],
            ["VARIABLE_DOMAINS", "SUM_UPPER_BOUND"],
        )

    match = re.fullmatch(
        r"Variables (?P<left>[A-Za-z_]\w*) and (?P<right>[A-Za-z_]\w*) each range over integers "
        r"(?P<lower>-?\d+) through (?P<upper>-?\d+)\. Require (?P<variable>[A-Za-z_]\w*) = "
        r"(?P<value>-?\d+)\. How many assignments are possible\?",
        text,
    )
    if match and match.group("variable") in {match.group("left"), match.group("right")}:
        names = (match.group("left"), match.group("right"))
        lower, upper, value = int(match.group("lower")), int(match.group("upper")), int(match.group("value"))
        return _complete(
            problem_id,
            _range_variables(names, lower, upper),
            [{"kind": "equal", "variable": match.group("variable"), "value": value}],
            ["VARIABLE_DOMAINS", "EQUALITY"],
        )

    match = re.fullmatch(
        r"Variables (?P<left>[A-Za-z_]\w*) and (?P<right>[A-Za-z_]\w*) each range over integers "
        r"(?P<lower>-?\d+) through (?P<upper>-?\d+)\. Require (?P<variable>[A-Za-z_]\w*) to be "
        r"nonzero\. How many assignments are possible\?",
        text,
    )
    if match and match.group("variable") in {match.group("left"), match.group("right")}:
        names = (match.group("left"), match.group("right"))
        lower, upper = int(match.group("lower")), int(match.group("upper"))
        return _complete(
            problem_id,
            _range_variables(names, lower, upper),
            [{"kind": "not_equal", "variable": match.group("variable"), "value": 0}],
            ["VARIABLE_DOMAINS", "EXCLUSION_NONZERO"],
        )

    match = re.fullmatch(
        r"Variable (?P<name>[A-Za-z_]\w*) ranges over integers (?P<lower>-?\d+) through "
        r"(?P<upper>-?\d+) and (?P=name) is nonzero\. How many values are possible\?",
        text,
    )
    if match:
        name = match.group("name")
        lower, upper = int(match.group("lower")), int(match.group("upper"))
        return _complete(
            problem_id,
            _range_variables((name,), lower, upper),
            [{"kind": "not_equal", "variable": name, "value": 0}],
            ["VARIABLE_DOMAINS", "EXCLUSION_NONZERO"],
        )

    match = re.fullmatch(
        r"Variables (?P<names>[A-Za-z_]\w*(?:, [A-Za-z_]\w*)+) are binary\. Exactly "
        r"(?P<count>\d+) equal (?P<value>-?\d+)\. How many assignments are possible\?",
        text,
    )
    if match:
        names = tuple(match.group("names").split(", "))
        count, value = int(match.group("count")), int(match.group("value"))
        return _complete(
            problem_id,
            _range_variables(names, 0, 1),
            [{"kind": "count_equal", "variables": list(names), "value": value, "count": count}],
            ["BINARY_DOMAINS", "CARDINALITY_EXACTLY"],
        )

    match = re.fullmatch(
        r"Variables (?P<names>[A-Za-z_]\w*(?:, [A-Za-z_]\w*)+) are each either 0 or 1\. "
        r"(?P<quantifier>Exactly|At least|At most) (?P<count>\d+) of them equal (?P<value>-?\d+)\. "
        r"How many assignments satisfy this\?",
        text,
    )
    if match:
        names = tuple(match.group("names").split(", "))
        count, value = int(match.group("count")), int(match.group("value"))
        kind, check = {
            "Exactly": ("count_equal", "CARDINALITY_EXACTLY"),
            "At least": ("count_at_least", "CARDINALITY_AT_LEAST"),
            "At most": ("count_at_most", "CARDINALITY_AT_MOST"),
        }[match.group("quantifier")]
        return _complete(
            problem_id,
            _range_variables(names, 0, 1),
            [{"kind": kind, "variables": list(names), "value": value, "count": count}],
            ["BINARY_DOMAINS", check],
        )

    match = re.fullmatch(
        r"Digits (?P<names>[A-Za-z_]\w*(?:, [A-Za-z_]\w*)+) each range from 0 through "
        r"(?P<maximum>\d+) and form a three-digit base-(?P<base>\d+) number in that order\. "
        r"(?P<first>[A-Za-z_]\w*) is nonzero\. All variables are distinct\. The number has remainder "
        r"(?P<remainder>\d+) modulo (?P<modulus>\d+)\. How many such numbers exist\?",
        text,
    )
    if match:
        names = tuple(match.group("names").split(", "))
        maximum, base = int(match.group("maximum")), int(match.group("base"))
        if len(names) == 3 and names[0] == match.group("first") and maximum == base - 1:
            return _complete(
                problem_id,
                _range_variables(names, 0, maximum),
                [
                    {"kind": "not_equal", "variable": names[0], "value": 0},
                    {"kind": "all_different", "variables": list(names)},
                    {
                        "kind": "number_mod",
                        "variables": list(names),
                        "base": base,
                        "modulus": int(match.group("modulus")),
                        "remainder": int(match.group("remainder")),
                    },
                ],
                ["DIGIT_DOMAINS", "LEADING_NONZERO", "ALL_DIFFERENT", "MODULAR_RESTRICTION"],
            )

    match = re.fullmatch(
        r"Variables (?P<left>[A-Za-z_]\w*) and (?P<right>[A-Za-z_]\w*) each range over integers "
        r"(?P<lower>-?\d+) through (?P<upper>-?\d+)\. Variable (?P<variable>[A-Za-z_]\w*) must not "
        r"equal (?P<forbidden>-?\d+), and (?P=left) \+ (?P=right) must equal (?P<total>-?\d+)\. "
        r"How many ordered assignments satisfy both conditions\?",
        text,
    )
    if match and match.group("variable") in {match.group("left"), match.group("right")}:
        names = (match.group("left"), match.group("right"))
        lower, upper = int(match.group("lower")), int(match.group("upper"))
        return _complete(
            problem_id,
            _range_variables(names, lower, upper),
            [
                {
                    "kind": "not_equal",
                    "variable": match.group("variable"),
                    "value": int(match.group("forbidden")),
                },
                {"kind": "sum_equal", "variables": list(names), "value": int(match.group("total"))},
            ],
            ["VARIABLE_DOMAINS", "EXCLUSION_VALUE", "SUM_EQUAL"],
        )

    return SemanticParse(
        "UNSUPPORTED",
        None,
        (),
        "problem did not fully match a fixed V2.1 grammar; partial keyword evidence is insufficient",
    )
