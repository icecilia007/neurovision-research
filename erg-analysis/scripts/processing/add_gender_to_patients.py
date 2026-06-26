"""Enrich patients_id_mapping with gender (sexo) from an external gender CSV.

Joins on `nome_completo`. Rows without a match receive "Unknown".

Outputs:
  - Parquet enriched with `sexo` column written to --output path
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import polars as pl

from common.logging_utils import configure_logging

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enrich patients_id_mapping with gender from gender_mapping CSV"
    )
    parser.add_argument("--parquet", required=True, help="Path to patients_id_mapping parquet file or folder")
    parser.add_argument("--gender-csv", required=True, help="Path to gender_mapping.csv")
    parser.add_argument("--output", required=True, help="Output parquet path")
    return parser


def run(args: argparse.Namespace) -> None:
    patients = pl.read_parquet(args.parquet)
    logger.info("Loaded patients: %d rows", len(patients))

    gender = (
        pl.read_csv(args.gender_csv)
        .unique(subset=["nome_completo"], keep="last")
    )
    logger.info("Loaded gender mapping: %d unique names", len(gender))

    result = (
        patients
        .join(gender, on="nome_completo", how="left")
        .with_columns(pl.col("sexo").fill_null("Unknown"))
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.write_parquet(str(output_path))

    total   = len(result)
    known   = result.filter(pl.col("sexo") != "Unknown").height
    unknown = total - known

    logger.info("Total rows   : %d", total)
    logger.info("With gender  : %d", known)
    logger.info("Unknown      : %d", unknown)

    if unknown > 0:
        logger.warning(
            "Rows with Unknown gender:\n%s",
            result.filter(pl.col("sexo") == "Unknown").select(["nome_completo", "patient_unique_id"]),
        )


def main() -> None:
    configure_logging()
    args = build_parser().parse_args()
    run(args)


if __name__ == "__main__":
    main()
