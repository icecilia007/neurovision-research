"""Date parsing helpers shared across pipeline stages."""

from __future__ import annotations

import re
from datetime import date
from typing import Optional, Tuple

import polars as pl


_RE_DATE_SEP = re.compile(r"[/\-\.]")

# Century rule: YY < 30 → 2000+YY, YY >= 30 → 1900+YY
_CENTURY_CUTOFF = 30


def parse_dob_parts(raw: Optional[str]) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """Parse a date string into (day, month, year) as integers.

    Accepts Brazilian DD/MM/YYYY and ISO YYYY/MM/DD formats,
    with separators / - or .

    Applies century rule for 2-digit years: YY < 30 → 2000+YY, else 1900+YY.

    Returns (None, None, None) on any parse failure.
    """
    if not raw or not isinstance(raw, str):
        return None, None, None
    parts = _RE_DATE_SEP.split(raw.strip())
    if len(parts) != 3:
        return None, None, None
    try:
        p0, p1, p2 = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if len(p0) == 4:
            year, month, day = int(p0), int(p1), int(p2)
        else:
            day, month = int(p0), int(p1)
            yr = int(p2)
            if yr < 100:
                year = 2000 + yr if yr < _CENTURY_CUTOFF else 1900 + yr
            else:
                year = yr
        if not (1 <= month <= 12) or not (1 <= day <= 31):
            return None, None, None
        return day, month, year
    except (ValueError, IndexError):
        return None, None, None


def extract_birth_year(raw_dob: Optional[str]) -> Optional[int]:
    """Extract the 4-digit birth year from a date string.

    Accepts DD/MM/YYYY, YYYY/MM/DD with separators / - .
    Applies 2-digit century rule (YY < 30 → 20YY, else 19YY).
    Returns None on parse failure.

    Examples:
        extract_birth_year("11/07/1985") → 1985
    """
    _, _, year = parse_dob_parts(raw_dob)
    return year


def estimate_birth_year_range(
    age: Optional[int],
    test_date,
) -> Tuple[Optional[int], Optional[int]]:
    """Estimate the range of possible birth years from age + test date.

    RightEye provides AGE at assessment time but no birth date.  Because
    we do not know whether the person had already celebrated their birthday
    on TEST_DATE, the birth year is one of two consecutive values.

    Examples:
        estimate_birth_year_range(37, "2021-04-12") → (1983, 1984)
        estimate_birth_year_range(10, "2015-01-01") → (2004, 2005)

    Returns (None, None) when age is None / invalid or test_date cannot
    be parsed.  Ages outside [1, 120] are treated as data errors.
    """
    if age is None or not (1 <= age <= 120):
        return None, None
    if not test_date:
        return None, None
    try:
        test_year = int(str(test_date)[:4])
    except (ValueError, TypeError):
        return None, None
    # The person may not yet have had their birthday in test_year:
    #   born in (test_year - age)     if birthday already passed
    #   born in (test_year - age - 1) if birthday not yet reached
    return test_year - age - 1, test_year - age


def birth_year_range_expr(
    age_col: str = "AGE",
    test_date_col: str = "TEST_DATE",
) -> tuple[pl.Expr, pl.Expr]:
    """Vectorized Polars version of estimate_birth_year_range.

    Returns (birth_year_min_expr, birth_year_max_expr) for use in
    df.with_columns([*birth_year_range_expr()]).
    """
    test_year = pl.col(test_date_col).dt.year().cast(pl.Int32)
    age = pl.col(age_col).cast(pl.Int32, strict=False)
    valid = (age >= 1) & (age <= 120)
    min_expr = (
        pl.when(valid).then(test_year - age - 1).otherwise(pl.lit(None, dtype=pl.Int32))
        .alias("birth_year_min")
    )
    max_expr = (
        pl.when(valid).then(test_year - age).otherwise(pl.lit(None, dtype=pl.Int32))
        .alias("birth_year_max")
    )
    return min_expr, max_expr


def mapping_dob_to_year_month_day_exprs() -> tuple[pl.Expr, pl.Expr, pl.Expr]:
    """Return Polars expressions to extract dob_year, dob_month, dob_day
    from the patients_id_mapping ``data_nascimento`` column (YY/MM/DD format).

    Uses a single regex pass over the column instead of three independent
    str.split calls, which would parse the same string three times.

    Usage::

        df = df.with_columns([
            *mapping_dob_to_year_month_day_exprs()
        ])
    """
    # One regex pass extracts all three groups: YY, MM, DD
    col = pl.col("data_nascimento")
    yy = col.str.extract(r"^(\d+)/", 1).cast(pl.Int32, strict=False)
    mm = col.str.extract(r"^\d+/(\d+)/", 1).cast(pl.Int32, strict=False)
    dd = col.str.extract(r"^\d+/\d+/(\d+)$", 1).cast(pl.Int32, strict=False)

    year_expr = (
        pl.when(yy < _CENTURY_CUTOFF)
        .then(yy + 2000)
        .otherwise(yy + 1900)
        .alias("dob_year")
    )
    month_expr = mm.alias("dob_month")
    day_expr = dd.alias("dob_day")

    return year_expr, month_expr, day_expr
