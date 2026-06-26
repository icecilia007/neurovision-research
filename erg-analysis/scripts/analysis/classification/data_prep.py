"""Data preparation helpers for classification pipelines.

All heavy transformations use Polars. Conversion to pandas/numpy happens
only at the sklearn boundary (split_train_test output).
"""

from __future__ import annotations

import logging
from typing import Callable

import polars as pl
from sklearn.model_selection import train_test_split as _sklearn_split

from common.value_utils import parse_bool_field  # noqa: F401 — re-exported for convenience

logger = logging.getLogger(__name__)


def filter_annotated(
    df: pl.DataFrame,
    column: str,
    condition: Callable[[object], bool] | None = None,
    *,
    native_expr: pl.Expr | None = None,
) -> pl.DataFrame:
    """Keep only rows where condition(column value) is True.

    Prefer passing ``native_expr`` for best performance. When only
    ``condition`` is provided the function falls back to
    ``map_elements``, which triggers a PolarsInefficientMapWarning.
    If neither argument is given the default behaviour is to keep rows
    where the column is non-null and non-empty after stripping whitespace.

    Args:
        df: Input DataFrame.
        column: Column to evaluate.
        condition: Callable that returns True for rows to keep (slow path).
        native_expr: Polars boolean expression used as the filter mask (fast path).

    Example — default non-null / non-empty filter (fast):
        filter_annotated(df, "neurodivergencia")

    Example — custom native expression (fast):
        filter_annotated(df, "neurodivergencia",
                         native_expr=pl.col("neurodivergencia").is_not_null()
                                     & (pl.col("neurodivergencia") != "Não tem"))

    Example — arbitrary callable (slow, emits warning):
        filter_annotated(df, "neurodivergencia", lambda v: v is not None and v != "")
    """
    before = len(df)

    if native_expr is not None:
        mask: pl.Expr | pl.Series = native_expr
    elif condition is None:
        # Default: keep non-null, non-empty strings
        mask = pl.col(column).is_not_null() & (
            pl.col(column).cast(pl.String).str.strip_chars() != ""
        )
    else:
        # Slow path — arbitrary Python callable
        mask = df[column].map_elements(condition, return_dtype=pl.Boolean)

    result = df.filter(mask)
    logger.info(
        "filter_annotated(%s): %d → %d rows (removed %d unannotated)",
        column, before, len(result), before - len(result),
    )
    return result


def binarize_column(
    df: pl.DataFrame,
    column: str,
    parser: Callable[[object], bool | None],
    output_column: str | None = None,
) -> pl.DataFrame:
    """Add a boolean column derived from any free-text column using a caller-supplied parser.

    The caller owns the domain logic — pass any function that maps a raw cell
    value to True, False, or None (None = unknown/excluded from training).

    Args:
        df: Input DataFrame.
        column: Source column to binarize.
        parser: Callable(value) → bool | None. Use parse_bool_field for Sim/Não
                fields or parse_label_from_values for diagnosis-style fields.
        output_column: Name for the new boolean column (default: {column}_bin).

    Example — Sim/Não field:
        binarize_column(df, "erg", parse_bool_field)

    Example — diagnosis field where empty string = None, "Não tem" = False, rest = True:
        from common.value_utils import parse_label_from_values
        binarize_column(df, "neurodivergencia",
                        lambda v: parse_label_from_values(v, false_values=["Não tem", "Nao tem"]))
    """
    out_col = output_column or f"{column}_bin"
    result = df.with_columns(
        pl.col(column)
        .map_elements(parser, return_dtype=pl.Boolean)
        .alias(out_col)
    )
    true_count = result[out_col].sum()
    false_count = (result[out_col] == False).sum()  # noqa: E712
    null_count = result[out_col].null_count()
    logger.info(
        "binarize_column(%s → %s): True=%d  False=%d  null=%d",
        column, out_col, true_count, false_count, null_count,
    )
    return result


def expand_multilabel_column(
    df: pl.DataFrame,
    column: str,
    *,
    sep_pattern: str = r"[,;/+]",
) -> tuple[pl.DataFrame, list[str]]:
    """Expand a free-text multilabel column into one boolean column per unique condition.

    Splits each cell value by ``sep_pattern``, strips whitespace, and creates one
    boolean column per unique token found across all rows.

    Args:
        df: Input DataFrame containing ``column``.
        column: Free-text column with comma/semicolon/slash-separated labels
                (e.g. "TDAH, TEA" or "TDAH+TDA").
        sep_pattern: Regex used to split each cell value (default: comma, semicolon,
                     slash, or plus sign).

    Returns:
        Tuple of (expanded_df, condition_cols) where ``expanded_df`` has one new boolean
        column per unique condition and ``condition_cols`` is the sorted list of those names.
    """
    import re

    raw_values = df[column].to_list()
    parsed: list[list[str]] = []
    unique_conditions: set[str] = set()

    for val in raw_values:
        if val is None:
            parsed.append([])
            continue
        tokens = [t.strip() for t in re.split(sep_pattern, str(val)) if t.strip()]
        parsed.append(tokens)
        unique_conditions.update(tokens)

    condition_cols = sorted(unique_conditions)

    new_series = [
        pl.Series(name=cond, values=[cond in row_tokens for row_tokens in parsed], dtype=pl.Boolean)
        for cond in condition_cols
    ]

    result = df.with_columns(new_series)
    logger.info(
        "expand_multilabel_column(%s): %d conditions — %s",
        column, len(condition_cols), condition_cols,
    )
    return result, condition_cols


def join_label(
    features_df: pl.DataFrame,
    label_df: pl.DataFrame,
    features_key: str,
    label_key: str,
    label_columns: list[str],
) -> pl.DataFrame:
    """Left-join label columns from label_df into features_df.

    Args:
        features_df: Feature rows (one row per exam/eye/protocol).
        label_df: Label source (id_map with annotation columns).
        features_key: Join key column name in features_df (hashed patient id).
        label_key: Join key column name in label_df (hashed patient id).
        label_columns: Columns to bring from label_df (e.g. ["neurodivergencia_bin"]).
    """
    label_subset = label_df.select([label_key] + label_columns).rename({label_key: features_key})
    label_subset = label_subset.unique(subset=[features_key], keep="first")

    before = len(features_df)
    result = features_df.join(label_subset, on=features_key, how="left")
    matched = result.filter(pl.col(label_columns[0]).is_not_null()).select(features_key).n_unique()
    logger.info(
        "join_label: %d feature rows → %d after join | %d unique patients matched",
        before, len(result), matched,
    )
    return result


def aggregate_per_patient(
    df: pl.DataFrame,
    id_col: str,
    numeric_cols: list[str],
    categorical_cols: list[str],
    label_cols: list[str],
) -> pl.DataFrame:
    """Collapse multiple exam rows into one row per patient.

    Numeric columns: mean aggregation.
    Categorical columns: mode (first value after sort).
    Label columns: first non-null value (labels are patient-level, not exam-level).

    This step is required to prevent data leakage — without it the same
    patient can appear in both train and test splits.
    """
    agg_exprs: list[pl.Expr] = []

    for col in numeric_cols:
        if col in df.columns:
            agg_exprs.append(pl.col(col).cast(pl.Float64, strict=False).mean().alias(col))

    for col in categorical_cols:
        if col in df.columns:
            agg_exprs.append(pl.col(col).drop_nulls().first().alias(col))

    for col in label_cols:
        if col in df.columns:
            agg_exprs.append(pl.col(col).drop_nulls().first().alias(col))

    before = len(df)
    result = df.group_by(id_col).agg(agg_exprs)
    logger.info(
        "aggregate_per_patient: %d rows → %d unique patients (id_col=%s)",
        before, len(result), id_col,
    )
    return result


def split_train_test(
    df: pl.DataFrame,
    label_col: str,
    id_col: str,
    feature_cols: list[str],
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple:
    """Stratified 80/20 train/test split.

    Returns (X_train, X_test, y_train, y_test, ids_train, ids_test) as pandas/numpy
    ready for sklearn. Stratified on label_col to preserve class proportions.

    Args:
        df: Aggregated per-patient DataFrame.
        label_col: Boolean label column name.
        id_col: Patient ID column (kept separate for predictions audit).
        feature_cols: Feature columns to include in X.
        test_size: Fraction for test set (default 0.2 = 20%).
        random_state: Reproducibility seed.
    """
    valid = df.filter(pl.col(label_col).is_not_null())
    dropped = len(df) - len(valid)
    if dropped:
        logger.warning("split_train_test: dropped %d rows with null label", dropped)

    pdf = valid.to_pandas()
    X = pdf[feature_cols]
    y = pdf[label_col].astype(int)
    ids = pdf[id_col]

    X_train, X_test, y_train, y_test, ids_train, ids_test = _sklearn_split(
        X, y, ids,
        test_size=test_size,
        stratify=y,
        random_state=random_state,
    )
    def _balance(y_series) -> str:
        pos = int(y_series.sum())
        neg = len(y_series) - pos
        return f"True={pos} ({pos/len(y_series)*100:.1f}%)  False={neg} ({neg/len(y_series)*100:.1f}%)"

    logger.info(
        "split_train_test: train=%d [%s]  test=%d [%s]  (stratified, test_size=%.0f%%)",
        len(X_train), _balance(y_train),
        len(X_test), _balance(y_test),
        test_size * 100,
    )
    return X_train, X_test, y_train, y_test, ids_train, ids_test
