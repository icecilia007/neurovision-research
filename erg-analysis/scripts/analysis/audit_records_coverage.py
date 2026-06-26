"""Audit coverage between medical_records_history and pipeline datasets.

Produces four reports saved to --reports-output:

  1. records_not_in_bases_YYYYMMDD_HHMMSS.{parquet,csv}
     Records IDs not found in patients_id_mapping nor consolidated_metadata.
     Includes: ID, Nome, Neurodivergencia, Laudo, ERG, Eye tracking, FDT,
               Sensibilidade ao contraste, Daltonismo.

  2. bases_not_in_records_YYYYMMDD_HHMMSS.{parquet,csv}
     patient_unique_ids from the bases not matched to any record.
     Includes: patient_unique_id, prontuario, nome_completo (from mapping).

  3. records_erg_found_YYYYMMDD_HHMMSS.{parquet,csv}
     Records with ERG=Sim that were found in the bases (expected, good).

  4. records_erg_not_found_YYYYMMDD_HHMMSS.{parquet,csv}
     Records with ERG=Sim that were NOT found in the bases (gap, needs attention).

  5. records_no_erg_found_YYYYMMDD_HHMMSS.{parquet,csv}
     Records with ERG=Não/None that were found in the bases (unexpected, needs attention).
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import polars as pl

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.df_utils import dedup_and_log
from common.id_utils import normalize_prontuario
from common.logging_utils import configure_logging
from common.path_utils import resolve_base_dir, resolve_input_path, resolve_output_dir
from common.value_utils import parse_bool_field


logger = logging.getLogger(__name__)

_RECORDS_REPORT_COLS = [
    "ID", "Nome", "Neurodivergencia", "Laudo",
    "ERG", "Eye tracking", "FDT", "Sensibilidade ao contraste", "Daltonismo",
]
_MAPPING_PATTERNS = ["patients_id_mapping-*.parquet"]
_METADATA_PATTERNS = ["consolidated_metadata.parquet", "*consolidated_metadata*.parquet"]


def _read_parquet(path: Path) -> pl.DataFrame:
    return pl.read_parquet(list(path.rglob("*.parquet")) if path.is_dir() else path)


def _find_files(root: Path, patterns: list[str]) -> list[Path]:
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(root.rglob(pattern))
    return sorted({p.resolve() for p in matches if p.exists()})


def _collect_base_prontuarios(mapping_files: list[Path], metadata_files: list[Path]) -> tuple[set[str], set[str], pl.DataFrame]:
    """Returns (mapping_prontuarios, metadata_prontuarios, mapping_df_deduped_by_patient_unique_id)."""
    mapping_frames: list[pl.DataFrame] = []
    for p in mapping_files:
        mapping_frames.append(_read_parquet(p))

    mapping_df = pl.concat(mapping_frames) if mapping_frames else pl.DataFrame()
    if not mapping_df.is_empty() and "patient_unique_id" in mapping_df.columns:
        mapping_df = dedup_and_log(mapping_df, subset=["patient_unique_id"], label="mapping")

    mapping_pronts: set[str] = set()
    if "prontuario" in mapping_df.columns:
        mapping_pronts = {
            normalize_prontuario(v)
            for v in mapping_df["prontuario"].drop_nulls().to_list()
            if normalize_prontuario(v)
        }

    metadata_pronts: set[str] = set()
    for p in metadata_files:
        df = _read_parquet(p)
        col = "id_prontuario" if "id_prontuario" in df.columns else None
        if col:
            metadata_pronts |= {
                normalize_prontuario(v)
                for v in df[col].drop_nulls().unique().to_list()
                if normalize_prontuario(v)
            }

    return mapping_pronts, metadata_pronts, mapping_df


def _select_available(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    return df.select([c for c in cols if c in df.columns])


def _write_report(df: pl.DataFrame, path_stem: Path, label: str, dry_run: bool) -> None:
    if dry_run:
        logger.info("[dry-run] Would write %s (%d rows)", label, len(df))
        return
    df.write_parquet(str(path_stem.with_suffix(".parquet")))
    df.write_csv(str(path_stem.with_suffix(".csv")))
    logger.info("%s: %d rows → %s", label, len(df), path_stem.with_suffix(".parquet"))


def run(args: argparse.Namespace) -> None:
    base_dir = resolve_base_dir(args.base)
    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    records_path = resolve_input_path(base_dir, args.records_input, must_exist=True)
    mapping_root = resolve_input_path(base_dir, args.mapping_root, must_exist=True)
    metadata_root = resolve_input_path(base_dir, args.metadata_root, must_exist=True)
    reports_dir = resolve_output_dir(base_dir, args.reports_output, create=True)

    logger.info("Records coverage audit — records: %s", records_path)

    records_df = _read_parquet(records_path)
    logger.info("Records loaded: %d rows", len(records_df))

    mapping_files = _find_files(mapping_root, _MAPPING_PATTERNS)
    metadata_files = _find_files(metadata_root, _METADATA_PATTERNS)
    logger.info("Mapping files: %d  Metadata files: %d", len(mapping_files), len(metadata_files))

    mapping_pronts, metadata_pronts, mapping_df = _collect_base_prontuarios(mapping_files, metadata_files)
    all_base_pronts = mapping_pronts | metadata_pronts
    logger.info(
        "Base prontuarios — mapping: %d  metadata: %d  union: %d",
        len(mapping_pronts), len(metadata_pronts), len(all_base_pronts),
    )

    # normalize records ID column
    records_with_pront = records_df.with_columns(
        pl.col("ID").cast(pl.Utf8).map_elements(normalize_prontuario, return_dtype=pl.Utf8).alias("_pront")
    )

    # --- report 1: records not found in bases ---
    not_in_bases = records_with_pront.filter(
        ~pl.col("_pront").is_in(list(all_base_pronts))
    ).drop("_pront")
    _write_report(
        _select_available(not_in_bases, _RECORDS_REPORT_COLS),
        reports_dir / f"records_not_in_bases_{run_tag}",
        "records_not_in_bases",
        args.dry_run,
    )

    # --- report 2: base patient_unique_ids not in records ---
    # Uses prontuario match only (same as coverage audit). Name-matched patients
    # (name_exact/name_prefix) may still appear here — this is intentional since
    # the audit is prontuario-based and name matches are uncertain.
    records_pronts = {
        normalize_prontuario(str(v))
        for v in records_df["ID"].drop_nulls().to_list()
        if normalize_prontuario(str(v))
    }
    if "patient_unique_id" in mapping_df.columns:
        mapping_with_pront = mapping_df.with_columns(
            pl.col("prontuario").cast(pl.Utf8).map_elements(normalize_prontuario, return_dtype=pl.Utf8).alias("_pront")
            if "prontuario" in mapping_df.columns
            else pl.lit("").alias("_pront")
        )
        bases_not_in_records = mapping_with_pront.filter(
            ~pl.col("_pront").is_in(list(records_pronts))
        ).drop("_pront")
        cols = [c for c in ["patient_unique_id", "prontuario", "nome_completo"] if c in bases_not_in_records.columns]
        unique_pronts_not_found = bases_not_in_records["prontuario"].n_unique() if "prontuario" in bases_not_in_records.columns else 0
        logger.info(
            "bases_not_in_records: %d patient_unique_ids (%d unique prontuarios) not found in records",
            len(bases_not_in_records), unique_pronts_not_found,
        )
        _write_report(
            bases_not_in_records.select(cols),
            reports_dir / f"bases_not_in_records_{run_tag}",
            "bases_not_in_records",
            args.dry_run,
        )
    else:
        logger.warning("patient_unique_id column not found in mapping — skipping bases_not_in_records report")

    # parse ERG column to bool for filtering
    erg_col = "ERG"
    if erg_col not in records_df.columns:
        logger.warning("ERG column not found in records — skipping ERG coverage reports")
        return

    records_erg_bool = records_with_pront.with_columns(
        pl.col(erg_col).map_elements(parse_bool_field, return_dtype=pl.Boolean).alias("_erg_bool")
    )

    records_found = records_erg_bool.filter(pl.col("_pront").is_in(list(all_base_pronts)))
    records_not_found = records_erg_bool.filter(~pl.col("_pront").is_in(list(all_base_pronts)))

    # --- report 3: ERG=Sim found in bases (expected) ---
    _write_report(
        _select_available(
            records_found.filter(pl.col("_erg_bool") == True).drop("_pront", "_erg_bool"),
            _RECORDS_REPORT_COLS,
        ),
        reports_dir / f"records_erg_found_{run_tag}",
        "records_erg_found",
        args.dry_run,
    )

    # --- report 4: ERG=Sim NOT found in bases (gap — needs attention) ---
    _write_report(
        _select_available(
            records_not_found.filter(pl.col("_erg_bool") == True).drop("_pront", "_erg_bool"),
            _RECORDS_REPORT_COLS,
        ),
        reports_dir / f"records_erg_not_found_{run_tag}",
        "records_erg_not_found",
        args.dry_run,
    )

    # --- report 5: ERG=Não/None found in bases (unexpected) ---
    _write_report(
        _select_available(
            records_found.filter(pl.col("_erg_bool") != True).drop("_pront", "_erg_bool"),
            _RECORDS_REPORT_COLS,
        ),
        reports_dir / f"records_no_erg_found_{run_tag}",
        "records_no_erg_found",
        args.dry_run,
    )

    logger.info(
        "Coverage summary — records_not_in_bases=%d  erg_gap=%d  no_erg_but_found=%d",
        len(not_in_bases),
        len(records_not_found.filter(pl.col("_erg_bool") == True)),
        len(records_found.filter(pl.col("_erg_bool") != True)),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit coverage between medical_records_history and pipeline datasets. "
            "Generates reports for records not found in bases, bases not in records, "
            "and ERG coverage analysis."
        )
    )
    parser.add_argument("--base", default=".", help="Base directory")
    parser.add_argument(
        "--records-input",
        default="patients-data/medical_records_history.parquet",
        help="Path to medical_records_history parquet",
    )
    parser.add_argument(
        "--mapping-root",
        default="output/patients",
        help="Root directory containing patients_id_mapping parquet files",
    )
    parser.add_argument(
        "--metadata-root",
        default="output/waveforms/consolidated",
        help="Root directory containing consolidated_metadata parquet",
    )
    parser.add_argument(
        "--reports-output",
        default="output/reports/records_coverage",
        help="Directory for coverage audit reports",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be written without writing any files",
    )
    return parser


if __name__ == "__main__":
    configure_logging()
    _args = build_parser().parse_args()
    run(_args)
