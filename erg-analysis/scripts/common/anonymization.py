"""Anonymization utilities for questionnaire feature datasets.

Independent pipeline for questionnaire data — does NOT touch or depend
on the existing ERG hashing pipeline (scripts/pipeline/anonymize/).

Responsibilities:
  1. Load the existing id_map produced by the ERG hashing pipeline.
  2. Build a prontuario → (patient_unique_id_hashed, sexo, ano_nascimento) lookup.
  3. Join the feature dataset with that lookup.
  4. Rename patient_unique_id_hashed → patient_unique_id  (project convention).
  5. Drop all PII columns.
  6. Log a quantitative audit trail so no records are lost silently.

Join path:
  feature_df.prontuario
      → id_map.prontuario  (extracted from patient_unique_id prefix)
      → id_map.patient_unique_id_hashed  (bcrypt hash)

The final column name for the anonymous identifier is patient_unique_id,
matching the convention used in all other anonymized datasets in the project
(patients-features, waveforms, erg_spectral_features, etc.).

Columns from id_map propagated to final dataset:
  patient_unique_id   Utf8   — bcrypt hash (renamed from patient_unique_id_hashed)
  sexo                Utf8   — 'Masculino' | 'Feminino' | ''
  ano_nascimento      Int16  — 4-digit birth year

These are already present in the id_map and are not PII by themselves
(sex + birth year do not uniquely identify a person).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import polars as pl

logger = logging.getLogger(__name__)

# Columns that must never appear in the anonymized output.
# Does NOT include sexo or ano_nascimento — those are retained as
# covariates, matching the convention in other project datasets.
_PII_COLUMNS = frozenset({
    "prontuario",
    "identity_name",
    "identity_dob",
    "identity_sex",
    "records_nome",
    "nome",
    "nome_completo",
    "data_nascimento",
    "email",
    "cpf",
    "telefone",
    # raw caption columns that may have survived feature_builder
    "QS1", "QS2", "QS3",
})

# Columns to propagate from id_map to the anonymized dataset
_ID_MAP_PROPAGATE = ["patient_unique_id_hashed", "sexo", "ano_nascimento"]


def _find_latest_id_map(id_map_dir: Path) -> Optional[Path]:
    """Return the most recent id_map parquet under id_map_dir (recursive)."""
    candidates = sorted(id_map_dir.rglob("id_map_*.parquet"), reverse=True)
    return candidates[0] if candidates else None


def load_id_map(
    id_map_path: Optional[Path] = None,
    id_map_dir: Optional[Path] = None,
) -> pl.DataFrame:
    """Load prontuario → (hash, sexo, ano_nascimento) lookup from id_map.

    The id_map produced by the ERG hashing pipeline stores patient_unique_id
    in the format  PRONTUARIO_name_YYMMDD_...  (underscore-separated).
    The prontuario is extracted from the numeric prefix before the first
    underscore or dash.

    Returns DataFrame with columns:
      prontuario               Utf8
      patient_unique_id_hashed Utf8
      sexo                     Utf8
      ano_nascimento           Int16
    """
    if id_map_path is None:
        if id_map_dir is None:
            raise ValueError("Provide id_map_path or id_map_dir.")
        id_map_path = _find_latest_id_map(id_map_dir)
        if id_map_path is None:
            raise FileNotFoundError(f"No id_map_*.parquet found under {id_map_dir}")

    logger.info("Loading id_map from: %s", id_map_path)

    available = pl.scan_parquet(str(id_map_path)).schema.names()

    select_exprs = [
        pl.col("patient_unique_id"),
        pl.col("patient_unique_id_hashed"),
    ]
    if "sexo" in available:
        select_exprs.append(pl.col("sexo").fill_null(""))
    else:
        select_exprs.append(pl.lit("").alias("sexo"))

    if "ano_nascimento" in available:
        select_exprs.append(pl.col("ano_nascimento").cast(pl.Int16, strict=False))
    else:
        select_exprs.append(pl.lit(None, dtype=pl.Int16).alias("ano_nascimento"))

    # Extract prontuario: numeric prefix before first underscore or dash
    df = (
        pl.scan_parquet(str(id_map_path))
        .select(select_exprs)
        .with_columns(
            pl.col("patient_unique_id")
            .str.extract(r"^(\d+)[_-]", 1)
            .alias("prontuario")
        )
        .filter(pl.col("prontuario").is_not_null())
        .unique(subset=["prontuario"], keep="first")
        .select(["prontuario", "patient_unique_id_hashed", "sexo", "ano_nascimento"])
        .collect()
    )

    logger.info("id_map loaded: %d prontuarios with hash", len(df))
    return df


def anonymize_dataset(
    feature_df: pl.DataFrame,
    id_map: pl.DataFrame,
    extra_pii_columns: Optional[list[str]] = None,
) -> tuple[pl.DataFrame, dict]:
    """Replace prontuario with patient_unique_id (bcrypt hash) and remove PII.

    Also propagates sexo and ano_nascimento from id_map, matching the
    convention in other anonymized datasets in the project.

    Args:
        feature_df:        Output of build_feature_dataset() — must have 'prontuario'.
        id_map:            Output of load_id_map().
        extra_pii_columns: Additional columns to drop beyond the defaults.

    Returns:
        (anonymized_df, audit_dict) where audit_dict contains counts for
        full traceability: input_rows, matched_rows, dropped_rows, output_rows.
    """
    pii_to_drop = set(_PII_COLUMNS)
    if extra_pii_columns:
        pii_to_drop.update(extra_pii_columns)

    input_rows = len(feature_df)

    df = (
        feature_df.lazy()
        .join(
            id_map.lazy().select([
                "prontuario",
                "patient_unique_id_hashed",
                "sexo",
                "ano_nascimento",
            ]),
            on="prontuario",
            how="left",
        )
        .collect()
    )

    matched_rows   = df.filter(pl.col("patient_unique_id_hashed").is_not_null()).height
    unmatched_rows = df.filter(pl.col("patient_unique_id_hashed").is_null()).height

    if unmatched_rows:
        unmatched_pront = (
            df.filter(pl.col("patient_unique_id_hashed").is_null())["prontuario"]
            .unique().to_list()
        )
        logger.warning(
            "%d rows dropped: prontuario not found in id_map. "
            "Prontuarios not found: %s",
            unmatched_rows,
            unmatched_pront[:10],
        )

    df = df.filter(pl.col("patient_unique_id_hashed").is_not_null())

    # Rename hash column to the project-standard name
    df = df.rename({"patient_unique_id_hashed": "patient_unique_id"})

    # Drop PII
    drop_cols = [c for c in df.columns if c in pii_to_drop]
    if drop_cols:
        df = df.drop(drop_cols)
        logger.info("PII columns dropped: %s", sorted(drop_cols))

    # Place patient_unique_id first, then sexo, ano_nascimento, then rest
    priority = ["patient_unique_id", "sexo", "ano_nascimento"]
    ordered = priority + [c for c in df.columns if c not in priority]
    df = df.select([c for c in ordered if c in df.columns])

    output_rows = len(df)
    audit = {
        "input_rows":     input_rows,
        "matched_rows":   matched_rows,
        "unmatched_rows": unmatched_rows,
        "output_rows":    output_rows,
    }

    logger.info(
        "Anonymization audit: input=%d | matched=%d | unmatched=%d | output=%d",
        input_rows, matched_rows, unmatched_rows, output_rows,
    )
    return df, audit
