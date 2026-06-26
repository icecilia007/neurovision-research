"""Patient-level column derivation utilities (generic, domain-agnostic)."""

from __future__ import annotations

import polars as pl


def extract_birth_year_expr(col: str = "data_nascimento") -> pl.Expr:
    """Derives a 4-digit birth year from a YY/MM/DD string column.

    Century rule: YY < 30 → 2000+YY, YY >= 30 → 1900+YY.
    Returns null when the column value is null or does not start with two digits.
    """
    yy = pl.col(col).str.slice(0, 2).cast(pl.Int16, strict=False)
    return (
        pl.when(yy < 30)
        .then(yy + 2000)
        .otherwise(yy + 1900)
        .cast(pl.Int16)
    )
