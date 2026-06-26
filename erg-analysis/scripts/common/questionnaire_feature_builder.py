"""Build a feature dataset from parsed questionnaire + linkage results.

Takes:
  - parsed_df   : output of questionnaire_parser.parse_questionnaire_file()
  - linkage_df  : DataFrame with columns [submission_id, prontuario, decision]

Joins on submission_id and:
  - Keeps only MATCH_UNIQUE rows (confirmed prontuario) by default
  - Drops identity PII columns (name, dob, email) by explicit list
  - Retains all clinical/demographic and question response columns

PII columns dropped (explicit list — NOT by prefix):
  QS1  name
  QS2  date of birth
  QS3  email
  identity_name / identity_dob / identity_sex  (parser aliases)

Columns KEPT (examples from Cardiff questionnaire):
  QS4  sexo
  QS5  raça/etnia
  QS6  escolaridade
  QS7  profissão
  QS8  diagnóstico
  QS9  possui diagnóstico (clinical feature — not PII)
  Q1..Q20  questionnaire responses
  F1, F2   ease/feedback
  TR1      trigger

All processing uses Polars LazyFrame; collect() only at the final step.
"""

from __future__ import annotations

import logging
from typing import Optional

import polars as pl

logger = logging.getLogger(__name__)

# Explicit list of captions that carry raw identity (PII) or open-ended
# free-text that could contain identifying information.
# Drop by exact caption name, not by prefix — prevents accidentally
# dropping clinical features like QS9 (has prior diagnosis?).
#
# Free-text fields (text_response) are high re-identification risk:
# users may write names, ages, diagnoses, or personal details.
# Add any free-text caption here even if it seems innocuous.
_PII_CAPTION_EXACT: frozenset[str] = frozenset({
    "QS1",   # name
    "QS2",   # date of birth
    "QS3",   # email
    "F2",    # open-ended feedback/observations — free text, re-identification risk
})

# Alias columns added by the parser for linkage — always PII
_IDENTITY_ALIASES: frozenset[str] = frozenset({
    "identity_name",
    "identity_dob",
    "identity_sex",
})


def build_feature_dataset(
    parsed_df: pl.DataFrame,
    linkage_df: pl.DataFrame,
    keep_unmatched: bool = False,
    extra_pii_captions: Optional[list[str]] = None,
) -> pl.DataFrame:
    """Join parsed questionnaire with linkage results and return feature dataset.

    Args:
        parsed_df:          Output of parse_questionnaire_file().
        linkage_df:         DataFrame with [submission_id, prontuario, decision].
        keep_unmatched:     Include rows with decision != MATCH_UNIQUE
                            (prontuario will be null for those rows).
        extra_pii_captions: Additional caption column names to drop beyond defaults.
                            Use when a specific questionnaire has extra PII fields.

    Returns:
        DataFrame with prontuario + all non-PII columns.
    """
    pii_to_drop = set(_PII_CAPTION_EXACT) | set(_IDENTITY_ALIASES)
    if extra_pii_captions:
        pii_to_drop.update(extra_pii_captions)

    linkage_lf = (
        linkage_df.lazy()
        .select(["submission_id", "prontuario", "decision"])
        .with_columns(pl.col("submission_id").cast(pl.Int64))
    )

    joined = (
        parsed_df.lazy()
        .join(linkage_lf, on="submission_id", how="left")
    )

    if not keep_unmatched:
        joined = joined.filter(pl.col("decision") == "MATCH_UNIQUE")

    # Drop only explicit PII columns that exist in the DataFrame
    existing_cols = parsed_df.columns
    drop_cols = [c for c in existing_cols if c in pii_to_drop]
    if drop_cols:
        joined = joined.drop(drop_cols)

    df = joined.collect()

    n_with_prontuario = df.filter(pl.col("prontuario").is_not_null()).height
    retained = [c for c in df.columns if c not in pii_to_drop]
    logger.info(
        "Feature dataset: %d rows | with_prontuario=%d | columns=%d | dropped_pii=%s",
        len(df),
        n_with_prontuario,
        len(retained),
        sorted(drop_cols),
    )
    return df
