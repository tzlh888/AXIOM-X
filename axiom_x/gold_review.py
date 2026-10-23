from __future__ import annotations

import itertools
import json
import re
from typing import Any


def render_specification(specification: dict[str, Any]) -> str:
    variables = ", ".join(
        f"{item['name']} ∈ {{{', '.join(map(str, item['domain']))}}}"
        for item in specification["variables"]
    )
    clauses: list[str] = []
    for item in specification["constraints"]:
        kind = item["kind"]
        if kind == "all_different":
            clauses.append(f"{', '.join(item['variables'])} are pairwise distinct")
        elif kind in {"equal", "not_equal"}:
            op = "=" if kind == "equal" else "≠"
            clauses.append(f"{item['variable']} {op} {item['value']}")
        elif kind in {"less_than", "less_equal"}:
            op = "<" if kind == "less_than" else "≤"
            clauses.append(f"{item['left']} {op} {item['right']}")
        elif kind.startswith("sum_"):
            op = {"sum_equal": "=", "sum_at_least": "≥", "sum_at_most": "≤"}[kind]
            clauses.append(f"sum({', '.join(item['variables'])}) {op} {item['value']}")
        elif kind.startswith("count_"):
            op = {"count_equal": "=", "count_at_least": "≥", "count_at_most": "≤"}[kind]
            clauses.append(
                f"number of variables equal to {item['value']} among "
                f"{', '.join(item['variables'])} {op} {item['count']}"
            )
        elif kind == "number_mod":
            digits = ", ".join(item["variables"])
            clauses.append(
                f"the base-{item['base']} numeral ({digits}) is congruent to "
                f"{item['remainder']} modulo {item['modulus']}"
            )
        else:  # FormalSpecification validation should make this unreachable.
            raise ValueError(f"unsupported constraint in review rendering: {kind}")
    conditions = "; ".join(clauses) if clauses else "no additional constraints"
    return f"Count ordered assignments with {variables}; require {conditions}."


def verification_guidance(category: str) -> str:
    return {
        "exactly_count": "Use a binomial coefficient after independently identifying n and k.",
        "at_least_count": "Sum the relevant binomial coefficients from k through n.",
        "at_most_count": "Sum the relevant binomial coefficients from 0 through k.",
        "sum_bounds": "List or count ordered pairs in the square domain whose sum lies in both bounds.",
        "digit_modular": "Enumerate the small digit product, enforcing leading, distinctness, and modulus conditions separately.",
        "negation_and_sum": "Solve the fixed-sum equation over the stated domains, then remove the forbidden first coordinate.",
        "combined_distinct_sum": "Enumerate ordered triples, checking distinctness and the exact sum independently.",
        "order_and_boundary": "For each allowed nonzero x, count the domain values y with y > x, then sum.",
    }[category]


def independent_solutions_from_text(case: dict[str, Any]) -> tuple[tuple[str, ...], frozenset[tuple[int, ...]]]:
    """Template-family verifier driven by public text, independent of the Gold specification."""
    text, category = case["problem_text"], case["category"]
    if category in {"exactly_count", "at_least_count", "at_most_count"}:
        match = re.fullmatch(
            r"Variables (.+) are each either 0 or 1\. (Exactly|At least|At most) "
            r"(\d+) of them equal 1\. How many assignments satisfy this\?",
            text,
        )
        if not match:
            raise ValueError(f"unparsed binary-count problem: {text}")
        names = tuple(part.strip() for part in match.group(1).split(","))
        quantifier, threshold = match.group(2), int(match.group(3))

        def predicate(values: tuple[int, ...]) -> bool:
            count = sum(values)
            return {
                "Exactly": count == threshold,
                "At least": count >= threshold,
                "At most": count <= threshold,
            }[quantifier]

        domains = [(0, 1)] * len(names)
    elif category == "sum_bounds":
        match = re.fullmatch(
            r"Variables u and v each range over integers 0 through (\d+)\. Their sum is at least "
            r"(\d+) and at most (\d+)\. How many ordered assignments satisfy both bounds\?",
            text,
        )
        if not match:
            raise ValueError(f"unparsed sum-bounds problem: {text}")
        maximum, lower, upper = map(int, match.groups())
        names, domains = ("u", "v"), [range(maximum + 1)] * 2
        predicate = lambda values: lower <= sum(values) <= upper
    elif category == "digit_modular":
        match = re.fullmatch(
            r"Digits d0, d1, d2 each range from 0 through (\d+) and form a three-digit base-(\d+) "
            r"number in that order\. d0 is nonzero\. All variables are distinct\. The number has "
            r"remainder (\d+) modulo (\d+)\. How many such numbers exist\?",
            text,
        )
        if not match:
            raise ValueError(f"unparsed digit-modular problem: {text}")
        maximum, base, remainder, modulus = map(int, match.groups())
        if maximum != base - 1:
            raise ValueError("digit domain is inconsistent with the stated base")
        names, domains = ("d0", "d1", "d2"), [range(base)] * 3
        predicate = lambda values: (
            values[0] != 0
            and len(set(values)) == 3
            and (values[0] * base * base + values[1] * base + values[2]) % modulus == remainder
        )
    elif category == "negation_and_sum":
        match = re.fullmatch(
            r"Variables m and n each range over integers 0 through (\d+)\. Variable m must not equal "
            r"(\d+), and m \+ n must equal (\d+)\. How many ordered assignments satisfy both conditions\?",
            text,
        )
        if not match:
            raise ValueError(f"unparsed negation-and-sum problem: {text}")
        maximum, forbidden, total = map(int, match.groups())
        names, domains = ("m", "n"), [range(maximum + 1)] * 2
        predicate = lambda values: values[0] != forbidden and sum(values) == total
    elif category == "combined_distinct_sum":
        match = re.fullmatch(
            r"Variables a, b, c each range over integers 0 through (\d+)\. All variables are distinct\. "
            r"Their sum is exactly (\d+)\. How many assignments satisfy all conditions\?",
            text,
        )
        if not match:
            raise ValueError(f"unparsed distinct-sum problem: {text}")
        maximum, total = map(int, match.groups())
        names, domains = ("a", "b", "c"), [range(maximum + 1)] * 3
        predicate = lambda values: len(set(values)) == 3 and sum(values) == total
    elif category == "order_and_boundary":
        match = re.fullmatch(
            r"Variables x and y each range over integers 0 through (\d+)\. Require x < y, and x is "
            r"nonzero\. How many ordered assignments are possible\?",
            text,
        )
        if not match:
            raise ValueError(f"unparsed order-and-boundary problem: {text}")
        maximum = int(match.group(1))
        names, domains = ("x", "y"), [range(maximum + 1)] * 2
        predicate = lambda values: values[0] < values[1] and values[0] != 0
    else:
        raise ValueError(f"unsupported review category: {category}")
    solutions = frozenset(values for values in itertools.product(*domains) if predicate(values))
    return names, solutions


def candidate_json(specification: dict[str, Any]) -> str:
    return json.dumps(specification, sort_keys=True, separators=(",", ":"))
