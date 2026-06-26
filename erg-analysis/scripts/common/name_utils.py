"""Name normalization and variation generation helpers.

All functions operate on raw (accented, spaced) or already-normalized
(lowercase ASCII alnum, no spaces) name strings.

Normalization is delegated to ``id_utils.normalize_name`` so there is
one canonical implementation for the whole codebase.
"""

from __future__ import annotations

import re
from itertools import combinations

from common.id_utils import normalize_name


_RE_SPACES = re.compile(r"\s+")


def tokens_from_raw(raw_name: str) -> list[str]:
    """Split a raw name into normalized tokens, discarding stop words.

    "Izabela Cecilia de Silva" → ["izabela", "cecilia", "silva"]
    Single-character parts are dropped.
    """
    parts = _RE_SPACES.split(raw_name.strip())
    return [normalize_name(p) for p in parts if len(normalize_name(p)) >= 2]


def generate_name_variations(raw_name: str) -> set[str]:
    """Generate plausible name forms anchored to the first name token.

    All variations include the first name as a prefix — this prevents
    last-name-only tokens (e.g. "alexandre" from "Daniela Alexandre")
    from matching unrelated records named "alexandre".

    Given "Izabela Cecilia Silva Barbosa" produces:
      - izabelaceciliasilvabarbosa        (full collapsed)
      - izabelacecilia, izabelasilva, …   (first name + one/two additional tokens)
      - izabelacsb, izabelacs, izabelacb  (first name + subset of initials)
      - icsb, ics, …                      (all-initials variants)

    Individual standalone tokens are NOT included because they cause
    false-positive matches when the base has a record whose name equals
    a common first name (e.g. "alexandre", "jose").
    """
    tokens = tokens_from_raw(raw_name)
    if not tokens:
        return set()

    variations: set[str] = set()
    first = tokens[0]
    rest = tokens[1:]

    # full collapsed (always anchored to first name)
    variations.add("".join(tokens))

    # first name alone — always included; phase logic (not string length)
    # determines whether a single-name match is unique enough to confirm
    variations.add(first)

    # first name + one or two additional full tokens (ordered combos)
    for r in (1, 2):
        if len(rest) < r:
            break
        for combo in combinations(range(len(rest)), r):
            variations.add(first + "".join(rest[i] for i in combo))

    # first name + subsets of initials from remaining tokens
    if rest:
        for r in range(1, len(rest) + 1):
            for combo in combinations(range(len(rest)), r):
                initials = "".join(rest[i][0] for i in combo)
                variations.add(first + initials)

    # all-initials (only when >= 2 tokens)
    if len(tokens) >= 2:
        variations.add("".join(t[0] for t in tokens))

    # first name + partial initials + last full token
    # Covers legacy patterns like "izabelacsbarbosa" (first + middle initials + last surname).
    # Generated as: first + initials_of_middle_tokens + last_token
    if len(tokens) >= 3:
        last = tokens[-1]
        middle = tokens[1:-1]
        for r in range(1, len(middle) + 1):
            for combo in combinations(range(len(middle)), r):
                initials = "".join(middle[i][0] for i in combo)
                variations.add(first + initials + last)

    return variations


def norm_sex(raw: str) -> str:
    """Normalize a sex/gender string to 'm', 'f', or '' (unknown)."""
    s = raw.strip().lower()
    if s in ("masculino", "m", "male"):
        return "m"
    if s in ("feminino", "f", "female"):
        return "f"
    return ""


def compare_gender(a: str, b: str) -> bool:
    """Return True when both gender strings normalize to the same non-empty value.

    Accepts all Portuguese/English variants:
        Masculino / Male / M / masc → "m"
        Feminino  / Female / F / fem → "f"

    Returns False when either value is unknown/neutral/NA.
    """
    na = norm_sex(a)
    nb = norm_sex(b)
    return bool(na and nb and na == nb)


def build_name_signatures(raw_name: str) -> set[str]:
    """Build the full set of comparison signatures for a name.

    Extends generate_name_variations with spaced variants so that
    fuzzy-matching algorithms receive both the collapsed form (used by
    existing patient bases) and the spaced form (used by questionnaires
    and RightEye FIRST_NAME/LAST_NAME).

    Given "Izabela Cecilia Silva Barbosa" produces everything from
    generate_name_variations PLUS:
      - "izabela cecilia silva barbosa"  (spaced full name)
      - "izabela cecilia"                (spaced first+second)
      - "izabela silva"                  (spaced first+third)
      - "izabela barbosa"                (spaced first+last)
      - "izabela cecilia barbosa"        (spaced triple combos)
      - …

    Spaced variants are critical for matching against RightEye records
    where FIRST_NAME="Leticia Maria Vieira" (full name in one field).
    """
    tokens = tokens_from_raw(raw_name)
    if not tokens:
        return set()

    sigs = generate_name_variations(raw_name)

    # spaced full name
    sigs.add(" ".join(tokens))

    # spaced pairwise and triple combos anchored to first token
    first = tokens[0]
    rest = tokens[1:]
    for r in (1, 2):
        if len(rest) < r:
            break
        for combo in combinations(range(len(rest)), r):
            sigs.add(first + " " + " ".join(rest[i] for i in combo))

    return sigs
