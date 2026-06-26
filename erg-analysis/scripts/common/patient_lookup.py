"""Patient lookup and phase-based matching utilities.

Provides:

  build_patient_table(records_path, mapping_root)
      Joins medical_records_history + patients_id_mapping into a single
      Polars DataFrame ready for matching.

  Phase filter functions — each is a pure function that accepts a patient
  DataFrame and query parameters, and returns the filtered subset:

      find_by_dob(patients, *, day, month, year) → pl.DataFrame
      find_by_exact_name(patients, norm_name) → pl.DataFrame
      find_by_first_name(patients, first_token) → pl.DataFrame
      find_by_name_variations(patients, variations) → pl.DataFrame
      find_by_sex(patients, sex_norm) → pl.DataFrame
      find_by_rapidfuzz(patients, norm_name, threshold) → pl.DataFrame

Design principles:
  - All filters use vectorized Polars expressions; no Python row iteration.
  - find_by_rapidfuzz uses rapidfuzz.process.cdist (C-level batch scoring)
    to avoid Python-level loops over candidates.
  - build_patient_table uses map_elements for normalize_name instead of
    extracting the column to a Python list.
  - P3: date parsing uses one regex pass per component via str.extract.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import polars as pl

from common.date_utils import birth_year_range_expr, mapping_dob_to_year_month_day_exprs
from common.id_utils import normalize_name


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# build patient table
# ---------------------------------------------------------------------------

def build_patient_table(records_path: Path, mapping_root: Path) -> pl.DataFrame:
    """Return a flat Polars DataFrame joining patients_id_mapping + medical_records_history.

    Columns guaranteed:
      patient_unique_id  Utf8
      prontuario         Utf8
      records_nome       Utf8   (best available; falls back to nome_completo)
      norm_nome          Utf8   (normalize_name applied via map_elements)
      dob_year           Int32 | null
      dob_month          Int32 | null
      dob_day            Int32 | null
      sexo               Utf8   ('Masculino' | 'Feminino' | 'Unknown' | '')
    """
    records = pl.read_parquet(str(records_path))

    mapping_files = sorted(mapping_root.rglob("patients_id_mapping-*.parquet"), reverse=True)
    if not mapping_files:
        raise FileNotFoundError(f"No patients_id_mapping parquet found under {mapping_root}")
    mapping = pl.read_parquet(str(mapping_files[0]))
    logger.info("Patient table source: %s (%d rows)", mapping_files[0].name, len(mapping))

    # --- records side ---
    records_select = [
        pl.col("ID").cast(pl.Utf8).str.strip_chars().alias("prontuario"),
        pl.col("Nome").str.strip_chars().fill_null("").alias("records_nome"),
    ]
    records_select.append(
        pl.col("Sexo").fill_null("").alias("records_sexo")
        if "Sexo" in records.columns
        else pl.lit("").alias("records_sexo")
    )
    records_clean = records.select(records_select)

    # --- mapping side ---
    map_select = [
        pl.col("prontuario").cast(pl.Utf8).str.strip_chars().alias("prontuario"),
        pl.col("patient_unique_id"),
        pl.col("data_nascimento"),
    ]
    map_select.append(
        pl.col("sexo").fill_null("").alias("mapping_sexo")
        if "sexo" in mapping.columns
        else pl.lit("").alias("mapping_sexo")
    )
    if "nome_completo" in mapping.columns:
        map_select.append(pl.col("nome_completo").fill_null("").alias("nome_completo_map"))

    mapping_clean = (
        mapping
        .select(map_select)
        .unique(subset=["patient_unique_id"])
    )

    # --- join ---
    joined = mapping_clean.join(records_clean, on="prontuario", how="left")

    # best name: records_nome preferred, fallback to nome_completo_map
    if "nome_completo_map" in joined.columns:
        joined = joined.with_columns(
            pl.when(pl.col("records_nome").is_null() | (pl.col("records_nome") == ""))
            .then(pl.col("nome_completo_map"))
            .otherwise(pl.col("records_nome"))
            .alias("records_nome")
        ).drop("nome_completo_map")

    # best sexo: records_sexo preferred, fallback to mapping_sexo
    joined = joined.with_columns(
        pl.when(
            pl.col("records_sexo").is_not_null() & (pl.col("records_sexo") != "")
        )
        .then(pl.col("records_sexo"))
        .otherwise(pl.col("mapping_sexo"))
        .alias("sexo")
    ).drop(["records_sexo", "mapping_sexo"])

    # parse dob columns (single regex pass per component — P3)
    year_expr, month_expr, day_expr = mapping_dob_to_year_month_day_exprs()
    joined = joined.with_columns([year_expr, month_expr, day_expr])

    # P1: use map_elements instead of extracting column to Python list
    joined = joined.with_columns(
        pl.col("records_nome")
        .map_elements(normalize_name, return_dtype=pl.Utf8)
        .alias("norm_nome")
    )

    logger.info(
        "Patient table: %d rows | with dob_year=%d | with norm_nome=%d",
        len(joined),
        joined.filter(pl.col("dob_year").is_not_null()).height,
        joined.filter(pl.col("norm_nome") != "").height,
    )
    return joined


# ---------------------------------------------------------------------------
# RightEye table builder
# ---------------------------------------------------------------------------

# Only the identity columns needed for record linkage are loaded.
# Selecting columns at read time avoids loading the 500+ assessment metric
# columns into memory — critical for scalability.
_RIGHTEYE_IDENTITY_COLS = [
    "PATIENT_ID",
    "PARTICIPANT_ID",
    "FIRST_NAME",
    "LAST_NAME",
    "AGE",
    "GENDER",
    "TEST_DATE",
]


def build_righteye_table(righteye_path: Path) -> pl.DataFrame:
    """Return one row per unique patient from the RightEye dataset.

    Columns produced:
      re_patient_id     Utf8    — raw PATIENT_ID (may be prontuario or other)
      re_prontuario     Utf8    — numeric-only portion when PATIENT_ID is numeric
      participant_id    Utf8    — stable RightEye UUID per patient
      re_full_name      Utf8    — FIRST_NAME + " " + LAST_NAME (raw)
      norm_nome         Utf8    — normalize_name applied to full name
      re_gender         Utf8    — 'm', 'f', or ''
      birth_year_min    Int32   — lower bound of estimated birth year
      birth_year_max    Int32   — upper bound of estimated birth year

    One row per PARTICIPANT_ID (stable patient key): the most recent
    TEST_DATE is used for birth-year estimation so that the range is as
    tight as possible.

    AGE values outside [1, 120] are treated as data errors and produce
    null birth_year_min/max.
    """
    lf = pl.scan_parquet(str(righteye_path), hive_partitioning=False).select(
        _RIGHTEYE_IDENTITY_COLS
    )

    # Keep most recent assessment per patient (latest TEST_DATE gives best age estimate)
    lf = (
        lf
        .sort("TEST_DATE", descending=True)
        .unique(subset=["PARTICIPANT_ID"], keep="first")
    )

    # Build full name and normalize
    lf = lf.with_columns(
        pl.concat_str(
            [pl.col("FIRST_NAME").fill_null(""), pl.col("LAST_NAME").fill_null("")],
            separator=" ",
        )
        .str.strip_chars()
        .alias("re_full_name")
    )

    # Vectorized birth-year range from AGE + TEST_DATE
    min_expr, max_expr = birth_year_range_expr("AGE", "TEST_DATE")
    lf = lf.with_columns([min_expr, max_expr])

    # Extract numeric prontuario when PATIENT_ID is all digits (5-7 chars typical)
    lf = lf.with_columns(
        pl.when(pl.col("PATIENT_ID").str.contains(r"^\d{4,10}$"))
        .then(pl.col("PATIENT_ID"))
        .otherwise(pl.lit(None))
        .alias("re_prontuario")
    )

    # Normalize gender to m/f/''
    lf = lf.with_columns(
        pl.col("GENDER")
        .str.to_lowercase()
        .str.strip_chars()
        .replace({"male": "m", "female": "f", "neutral": "", "na": ""})
        .fill_null("")
        .alias("re_gender")
    )

    df = lf.collect()

    # map_elements for normalize_name (Python UDF — no pure Polars equivalent)
    df = df.with_columns(
        pl.col("re_full_name")
        .map_elements(normalize_name, return_dtype=pl.Utf8)
        .alias("norm_nome")
    )

    return df.select([
        pl.col("PATIENT_ID").alias("re_patient_id"),
        "re_prontuario",
        pl.col("PARTICIPANT_ID").alias("participant_id"),
        "re_full_name",
        "norm_nome",
        "re_gender",
        "birth_year_min",
        "birth_year_max",
    ])


# ---------------------------------------------------------------------------
# phase filter functions
# ---------------------------------------------------------------------------

def find_by_dob(
    patients: pl.DataFrame,
    *,
    day: Optional[int] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> pl.DataFrame:
    """Filter patients by any combination of day, month, year.

    Only the fields that are not None are applied as filters.
    Returns an empty DataFrame (schema preserved) when all fields are None.

    Replaces the three separate find_by_exact_dob / find_by_year_month /
    find_by_year functions with a single composable entry point (O4).
    """
    if day is None and month is None and year is None:
        return patients.clear()
    cond = pl.lit(True)
    if year is not None:
        cond = cond & (pl.col("dob_year") == year)
    if month is not None:
        cond = cond & (pl.col("dob_month") == month)
    if day is not None:
        cond = cond & (pl.col("dob_day") == day)
    return patients.filter(cond)


def find_by_exact_name(patients: pl.DataFrame, norm_name: str) -> pl.DataFrame:
    """Filter patients whose norm_nome equals the query exactly."""
    if not norm_name:
        return patients.clear()
    return patients.filter(pl.col("norm_nome") == norm_name)


def find_by_first_name(patients: pl.DataFrame, first_token: str) -> pl.DataFrame:
    """Filter patients whose norm_nome starts with the first normalized name token.

    M2: no minimum-length guard — the caller (tokens_from_raw) already drops
    tokens shorter than 2 chars. Phase logic determines whether the result is
    unique enough to confirm; string length is not a valid heuristic here.
    """
    if not first_token:
        return patients.clear()
    return patients.filter(pl.col("norm_nome").str.starts_with(first_token))


def find_by_name_variations(patients: pl.DataFrame, variations: set[str]) -> pl.DataFrame:
    """Filter patients whose norm_nome matches any variation — exact or prefix.

    C3: unifies exact membership and prefix checks into a single Polars
    expression evaluated in one vectorized pass.  The previous implementation
    had a short-circuit (return direct if not empty) that silently dropped
    candidates visible only via prefix matching.

    Both checks are combined with OR so every candidate that matches either
    criterion is returned.  Prefix check uses only variations with >= 2 chars
    to avoid single-character noise.
    """
    if not variations:
        return patients.clear()

    # exact membership (vectorized is_in)
    cond = pl.col("norm_nome").is_in(list(variations))

    # prefix check for variations long enough to be meaningful
    prefix_vars = [v for v in variations if len(v) >= 2]
    for v in prefix_vars:
        cond = cond | pl.col("norm_nome").str.starts_with(v)

    return patients.filter(cond)


def find_by_sex(patients: pl.DataFrame, sex_norm: str) -> pl.DataFrame:
    """Filter patients whose sexo matches the normalized query sex.

    M1: sex is an auxiliary disambiguator, never an eliminatory filter.
    Callers should only apply this to reduce a multi-candidate pool, and
    only when the result is non-empty — otherwise ignore and keep the
    full pool.

    sex_norm must be 'm' or 'f' (output of name_utils.norm_sex).
    Matching is case-insensitive prefix: 'Masculino'.startswith('m') → True.
    """
    if not sex_norm:
        return patients
    return patients.filter(
        pl.col("sexo").str.to_lowercase().str.starts_with(sex_norm)
    )


def find_by_rapidfuzz(
    patients: pl.DataFrame,
    norm_name: str,
    threshold: int = 80,
) -> pl.DataFrame:
    """Filter patients whose norm_nome scores above threshold with RapidFuzz.

    C4: uses rapidfuzz.process.cdist for batch C-level scoring — no Python
    loop over candidates.  cdist returns a NumPy matrix; the result is
    converted to a Polars Boolean Series for vectorized filtering.

    Only call this on a pool already reduced by earlier phases (never the
    full patient base).
    """
    if not norm_name or patients.is_empty():
        return patients.clear()

    try:
        from rapidfuzz.process import cdist as _cdist
        from rapidfuzz import fuzz as _fuzz
    except ImportError:
        logger.warning("rapidfuzz not installed — skipping fuzzy phase")
        return patients.clear()

    norm_col = patients["norm_nome"]
    candidates = norm_col.to_list()  # unavoidable: rapidfuzz requires a sequence

    # cdist computes all pairwise scores in a single C-level batch call.
    # Shape: (1, n_candidates) — one query vs all candidates.
    scores_ts = _cdist([norm_name], candidates, scorer=_fuzz.token_sort_ratio)[0]
    scores_pr = _cdist([norm_name], candidates, scorer=_fuzz.partial_ratio)[0]

    # element-wise max without Python loop (NumPy vectorized)
    import numpy as np
    mask = np.maximum(scores_ts, scores_pr) >= threshold

    return patients.filter(pl.Series("_fuzz_mask", mask, dtype=pl.Boolean))
