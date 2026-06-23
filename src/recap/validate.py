"""Numeric-validation gate for AI-generated recaps (BE-022).

``highlights.py`` is the guardrail: every number a recap may print originates
there. The AI is told to use only those numbers, but ``validate_recap`` enforces
it — it pulls every numeric token out of the generated ``headline + body`` and
checks that each is explained by a fact in the highlights. A recap that prints a
number the facts don't contain (a hallucinated score / stat) is rejected, and
``compose.py`` falls back to the deterministic snippet composer.

This is a safety gate, not a precision check: a small tolerance absorbs the model
rounding a two-decimal score to a whole number (e.g. writing ``95`` for
``95.46``). Names are not gated here — numbers are where fabrication does damage.

Pure functions, no LLM / network.
"""

import re

# A recap number matches a fact if within this absolute tolerance. 0.5 absorbs
# rounding a two-decimal score/points value to the nearest whole number while
# still rejecting an invented figure that isn't near any real one.
_TOLERANCE = 0.5

# Matches integer or decimal runs; commas/percent are not expected in recap copy.
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def _collect_facts(obj, acc: set[float]) -> None:
    """Recursively gather every numeric value reachable in ``obj`` into ``acc``.

    Handles ints/floats directly, parses numeric runs out of strings (so values
    stored as strings — ``season``, ``week`` — and compound tokens like a
    ``"3-0"`` record contribute each of their numbers), and walks dicts/lists.
    """
    if isinstance(obj, bool):
        return  # bool is an int subclass; never a recap "number"
    if isinstance(obj, (int, float)):
        acc.add(round(float(obj), 2))
        return
    if isinstance(obj, str):
        for token in _NUMBER_RE.findall(obj):
            acc.add(round(float(token), 2))
        return
    if isinstance(obj, dict):
        for value in obj.values():
            _collect_facts(value, acc)
        return
    if isinstance(obj, (list, tuple)):
        for item in obj:
            _collect_facts(item, acc)


def _matches(value: float, facts: set[float]) -> bool:
    """True when ``value`` is within tolerance of some fact."""
    return any(abs(fact - value) <= _TOLERANCE for fact in facts)


def validate_recap(recap: dict, highlights: dict) -> bool:
    """Return True when every number in the recap is supported by the highlights.

    Args:
        recap: ``{"headline": str, "body": str}`` from ``ai_generate.generate``.
        highlights: The deterministic highlights dict the recap was written from.

    Returns:
        True if all numeric tokens in ``headline + body`` match a fact within
        tolerance (or there are none); False if any number is unsupported.
    """
    facts: set[float] = set()
    _collect_facts(highlights, facts)

    text = f"{recap.get('headline', '')} {recap.get('body', '')}"
    return all(_matches(float(token), facts) for token in _NUMBER_RE.findall(text))
