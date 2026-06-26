"""Parse questionnaire export JSON into a flat Polars DataFrame.

Handles the nested format produced by the platform API:

    {
      "success": true,
      "data": {
        "questionnaire": {"id": 3, "title": "...", ...},
        "submissions": [
          {
            "submission_id": 143,
            "total_score": 15.0,
            "submitted_at": "2026-...",
            "answers": [
              {"caption": "QS1", "text_response": "Marcelo ...", ...},
              {"caption": "QS4", "selected_option_texts": ["Masculino"], ...},
              ...
            ]
          }
        ]
      }
    }

Also handles the legacy flat format (list of dicts with pre-extracted fields).

Output DataFrame columns:
    submission_id       Int64
    questionnaire_id    Int64
    questionnaire_title Utf8
    total_score         Float64
    submitted_at        Utf8
    <caption>           Utf8   — one column per caption found (QS1, QS2, Q1..Q20, F1, ...)

Identity field mapping (configurable, case-insensitive caption prefix match):
    QS1  → identity_name
    QS2  → identity_dob
    QS4  → identity_sex

These aliases are added as extra columns so the linkage pipeline can
consume them without knowing which caption carries which field.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import polars as pl

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# configurable caption → identity field mapping
# ---------------------------------------------------------------------------

# Maps caption prefix (case-insensitive) to a standardized alias column.
# Override by passing caption_identity_map to parse_questionnaire_file().
_DEFAULT_CAPTION_IDENTITY_MAP: dict[str, str] = {
    "QS1": "identity_name",
    "QS2": "identity_dob",
    "QS4": "identity_sex",
}

# PII columns that carry raw identity data — removed during anonymization.
# questionnaire_feature_builder uses this list to know what to drop.
PII_CAPTIONS = frozenset(_DEFAULT_CAPTION_IDENTITY_MAP.keys())


# ---------------------------------------------------------------------------
# response value extractor
# ---------------------------------------------------------------------------

def _answer_value(answer: dict) -> str:
    """Extract the display value from one answer dict.

    Priority:
      1. text_response (free-text questions)
      2. selected_option_texts joined by "; " (single/multi-choice)
      3. empty string
    """
    text = str(answer.get("text_response") or "").strip()
    if text:
        return text
    opts = answer.get("selected_option_texts") or []
    if opts:
        return "; ".join(str(o).strip() for o in opts if o)
    return ""


# ---------------------------------------------------------------------------
# nested JSON parser
# ---------------------------------------------------------------------------

def _parse_nested(
    data: dict,
    caption_identity_map: dict[str, str],
) -> pl.DataFrame:
    """Parse the nested API format into a flat DataFrame."""
    questionnaire = data.get("data", {}).get("questionnaire", {})
    submissions   = data.get("data", {}).get("submissions", [])

    q_id    = questionnaire.get("id")
    q_title = str(questionnaire.get("title") or "")

    rows: list[dict] = []
    all_captions: set[str] = set()

    for sub in submissions:
        sub_id      = sub.get("submission_id")
        total_score = sub.get("total_score")
        chyps_score = sub.get("chyps_score")
        submitted   = str(sub.get("submitted_at") or "")

        caption_values: dict[str, str] = {}
        for answer in sub.get("answers") or []:
            caption = str(answer.get("caption") or "").strip()
            if not caption:
                continue
            caption_values[caption] = _answer_value(answer)
            all_captions.add(caption)

        row: dict = {
            "submission_id":       sub_id,
            "questionnaire_id":    q_id,
            "questionnaire_title": q_title,
            "total_score":         total_score,
            "chyps_score":         chyps_score,
            "submitted_at":        submitted,
        }
        row.update(caption_values)
        rows.append(row)

    if not rows:
        return pl.DataFrame()

    # Build schema: fixed columns first, then one Utf8 per caption
    schema: dict[str, pl.PolarsDataType] = {
        "submission_id":       pl.Int64,
        "questionnaire_id":    pl.Int64,
        "questionnaire_title": pl.Utf8,
        "total_score":         pl.Float64,
        "chyps_score":         pl.Float64,
        "submitted_at":        pl.Utf8,
    }
    for cap in sorted(all_captions):
        schema[cap] = pl.Utf8

    # Normalise rows so every row has every caption key
    for row in rows:
        for cap in all_captions:
            row.setdefault(cap, "")

    df = pl.DataFrame(rows, schema=schema)
    df = _add_identity_aliases(df, caption_identity_map)

    logger.info(
        "Parsed nested questionnaire '%s' (id=%s): %d submissions, %d captions",
        q_title, q_id, len(df), len(all_captions),
    )
    return df


# ---------------------------------------------------------------------------
# legacy flat-list parser
# ---------------------------------------------------------------------------

_LEGACY_FIELD_MAP = {
    "ID da Submissão":                              "submission_id",
    "Pontuação Total":                              "total_score",
    "Data de Envio":                                "submitted_at",
    "QS1: Nome":                                    "QS1",
    "QS2: Data de nascimento: __ / __ / ____":     "QS2",
    "QS3: Email":                                   "QS3",
    "QS4: Sexo":                                    "QS4",
    "QS5: Raça/Etnia":                              "QS5",
    "QS6: Grau de escolaridade":                    "QS6",
}


def _parse_legacy(
    records: list[dict],
    caption_identity_map: dict[str, str],
) -> pl.DataFrame:
    """Parse the legacy flat-list export format."""
    rows: list[dict] = []
    all_keys: set[str] = set()

    for rec in records:
        row: dict = {
            "submission_id":       None,
            "questionnaire_id":    None,
            "questionnaire_title": "",
            "total_score":         None,
            "submitted_at":        "",
        }
        for src_key, value in rec.items():
            dest = _LEGACY_FIELD_MAP.get(src_key, src_key)
            row[dest] = str(value) if value is not None else ""
            if dest not in ("submission_id", "questionnaire_id",
                            "questionnaire_title", "total_score", "submitted_at"):
                all_keys.add(dest)
        rows.append(row)

    if not rows:
        return pl.DataFrame()

    schema: dict[str, pl.PolarsDataType] = {
        "submission_id":       pl.Int64,
        "questionnaire_id":    pl.Int64,
        "questionnaire_title": pl.Utf8,
        "total_score":         pl.Float64,
        "submitted_at":        pl.Utf8,
    }
    for k in sorted(all_keys):
        schema[k] = pl.Utf8

    for row in rows:
        for k in all_keys:
            row.setdefault(k, "")

    df = pl.DataFrame(rows, schema=schema)
    df = _add_identity_aliases(df, caption_identity_map)

    logger.info("Parsed legacy questionnaire: %d submissions", len(df))
    return df


# ---------------------------------------------------------------------------
# identity alias helper
# ---------------------------------------------------------------------------

def _add_identity_aliases(
    df: pl.DataFrame,
    caption_identity_map: dict[str, str],
) -> pl.DataFrame:
    """Add alias columns (identity_name, identity_dob, identity_sex) by
    looking up each caption in caption_identity_map.

    Matching is case-insensitive and uses startswith so "QS1" matches
    both "QS1" and "QS1: Nome" column names.
    """
    for col in df.columns:
        col_upper = col.upper()
        for prefix, alias in caption_identity_map.items():
            if col_upper.startswith(prefix.upper()) and alias not in df.columns:
                df = df.with_columns(pl.col(col).alias(alias))
                break

    # Ensure the three identity columns always exist (empty string if absent)
    for alias in caption_identity_map.values():
        if alias not in df.columns:
            df = df.with_columns(pl.lit("").alias(alias))

    return df


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def parse_questionnaire_file(
    path: Path,
    caption_identity_map: Optional[dict[str, str]] = None,
) -> pl.DataFrame:
    """Parse any supported questionnaire export format into a flat DataFrame.

    Supports:
      - Nested API format  ({"success": true, "data": {"submissions": [...]}})
      - Legacy flat format (list of dicts with pre-extracted field names)

    Args:
        path: Path to the JSON file.
        caption_identity_map: Override the default caption→identity mapping.
            Default: {"QS1": "identity_name", "QS2": "identity_dob",
                      "QS4": "identity_sex"}

    Returns:
        Flat Polars DataFrame with one row per submission.
    """
    if caption_identity_map is None:
        caption_identity_map = _DEFAULT_CAPTION_IDENTITY_MAP

    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    # Detect format
    if isinstance(raw, dict) and raw.get("success") and "data" in raw:
        return _parse_nested(raw, caption_identity_map)

    if isinstance(raw, list):
        return _parse_legacy(raw, caption_identity_map)

    raise ValueError(
        f"Unrecognised questionnaire JSON format in {path}. "
        "Expected nested API format or legacy flat list."
    )


def get_identity_fields(df: pl.DataFrame) -> tuple[str, str, str]:
    """Return (name, dob, sex) column names from a parsed DataFrame.

    These are the alias columns added by parse_questionnaire_file.
    """
    return "identity_name", "identity_dob", "identity_sex"
