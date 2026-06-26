"""Value normalization helpers for non-ID fields."""

from __future__ import annotations

import re
from typing import Collection


_TRUE_PATTERNS = re.compile(
    r"^\s*(sim|s|yes|y|tem|true|1)\s*$",
    re.IGNORECASE,
)
_FALSE_PATTERNS = re.compile(
    r"^\s*(n[aã]o(\s+tem)?|n|no|false|0)\s*$",
    re.IGNORECASE,
)


def parse_label_from_values(
    value: object,
    false_values: Collection[str],
    *,
    case_sensitive: bool = False,
) -> bool | None:
    """Binarize a free-text field where the caller defines what counts as False.

    Rules:
      None / ""                   → None  (not annotated)
      value in false_values       → False
      any other non-empty string  → True

    Useful for fields like neurodivergencia where "Não tem" means False
    and any diagnosis string (TDAH, TEA, DISLEXIA...) means True.

    Args:
        value: Raw cell value.
        false_values: Strings that map to False (e.g. ["Não tem", "Nao tem"]).
        case_sensitive: Whether the comparison is case-sensitive (default False).
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    compare = text if case_sensitive else text.lower()
    negatives = {v if case_sensitive else v.lower() for v in false_values}
    if compare in negatives:
        return False
    return True


def parse_bool_field(value: object) -> bool | None:
    """Normalizes free-text boolean-like values to bool or None.

    Handles Portuguese/English variants:
      True  <- Sim, S, Yes, Y, Tem, true, 1
      False <- Não, Nao, Nâo, Não tem, Nao tem, N, No, false, 0
      None  <- null, empty, unrecognized
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if _TRUE_PATTERNS.match(text):
        return True
    if _FALSE_PATTERNS.match(text):
        return False
    return None
