"""Anonymize single entrypoint consuming datasets under output/."""

import argparse
import csv
import logging
from datetime import datetime
from pathlib import Path

import polars as pl

from analysis.audit_unique_patient_ids import run as run_id_audit
from processing.annotate_patient_mapping import ANNOTATE_COLS
from common.path_utils import resolve_base_dir, resolve_input_path, resolve_output_dir
from common.patient_utils import extract_birth_year_expr
from pipeline.consolidated_to_parquet import run_consolidated_to_parquet
from pipeline.hashing import run_hash_orchestrator
from pipeline_utils import normalize_patient_id


logger = logging.getLogger(__name__)


ID_MAPPING_PATTERNS = [
    "patients_id_mapping-*.parquet",
]

def _write_unknown_sexo_audit(annotations: pl.DataFrame, reports_dir: Path, run_tag: str) -> None:
    """Write audit CSV of patients dropped due to sexo=Unknown."""
    if "sexo" not in annotations.columns:
        return
    unknown = annotations.filter(
        pl.col("sexo").cast(pl.Utf8, strict=False).str.to_lowercase().is_in(["unknown", ""])
    ).select(["patient_unique_id", "sexo"])
    if unknown.height == 0:
        logger.info("unknown_sexo audit: no patients with sexo=Unknown")
        return
    audit_path = reports_dir / f"unknown_sexo_dropped_{run_tag}.csv"
    unknown.write_csv(str(audit_path))
    logger.warning(
        "unknown_sexo audit: %d patients with sexo=Unknown — written to %s",
        unknown.height, audit_path.name,
    )


def _enrich_id_map_with_annotations(
    id_map_path: Path,
    patients_root: Path,
    reports_dir: Path,
    run_tag: str,
) -> None:
    """Join id_map with annotation columns from the latest patients_id_mapping."""
    mapping_files: list[Path] = []
    for pattern in ID_MAPPING_PATTERNS:
        mapping_files.extend(patients_root.rglob(pattern))
    mapping_files = sorted({p.resolve() for p in mapping_files if p.exists()})

    if not mapping_files:
        logger.warning("No patients_id_mapping found under %s — id_map not enriched", patients_root)
        return

    frames: list[pl.DataFrame] = []
    for mp in mapping_files:
        parts = list(mp.rglob("*.parquet")) if mp.is_dir() else [mp]
        df = pl.read_parquet([str(p) for p in parts])
        cols_to_keep = ["patient_unique_id", "data_nascimento"] + ANNOTATE_COLS
        available = [c for c in cols_to_keep if c in df.columns]
        if "patient_unique_id" not in available:
            continue
        frames.append(df.select(available))

    if not frames:
        logger.warning("patients_id_mapping files had no usable annotation columns")
        return

    combined = pl.concat(frames)
    combined = combined.with_columns(
        pl.col("patient_unique_id")
        .map_elements(normalize_patient_id, return_dtype=pl.Utf8)
        .alias("patient_unique_id")
    )

    if "data_nascimento" in combined.columns and "ano_nascimento" not in combined.columns:
        combined = combined.with_columns(extract_birth_year_expr("data_nascimento").alias("ano_nascimento"))

    annotations = combined.unique(subset=["patient_unique_id"], keep="first")

    # audit and nullify unknown sexo — patients with sexo=Unknown are kept in id_map with null sexo
    _write_unknown_sexo_audit(annotations, reports_dir, run_tag)
    if "sexo" in annotations.columns:
        annotations = annotations.with_columns(
            pl.when(pl.col("sexo").cast(pl.Utf8, strict=False).str.to_lowercase().is_in(["unknown", ""]))
            .then(pl.lit(None))
            .otherwise(pl.col("sexo"))
            .alias("sexo")
        )

    extra_cols = [c for c in ["ano_nascimento"] if c in annotations.columns]
    ann_cols_present = [c for c in ANNOTATE_COLS if c in annotations.columns] + extra_cols
    if not ann_cols_present:
        logger.info("No annotation columns found in mapping — id_map not enriched")
        return

    annotations = annotations.select(["patient_unique_id"] + ann_cols_present)

    id_map = pl.read_parquet(str(id_map_path))

    for col in ann_cols_present:
        if col in id_map.columns:
            id_map = id_map.drop(col)

    id_map = id_map.join(annotations, on="patient_unique_id", how="left")

    for col in ann_cols_present:
        if id_map[col].dtype == pl.Utf8:
            id_map = id_map.with_columns(pl.col(col).fill_null(""))

    id_map.write_parquet(str(id_map_path))
    logger.info(
        "id_map enriched with annotation columns %s: %s",
        ann_cols_present, id_map_path.name,
    )


PATIENTS_DATASET_PATTERNS = [
    "patients-*.parquet",
    "patients-*.csv",
]

METADATA_DATASET_PATTERNS = [
    "consolidated_metadata.parquet",
    "consolidated_metadata.csv",
    "*consolidated_metadata*.parquet",
    "*consolidated_metadata*.csv",
]

WAVEFORMS_DATASET_PATTERNS = [
    "consolidated_waveforms.parquet",
    "consolidated_waveforms.csv",
    "*consolidated_waveforms*.parquet",
    "*consolidated_waveforms*.csv",
]


def _latest_match(paths: list[Path]) -> Path:
    return sorted(paths, key=lambda path: (path.stat().st_mtime, str(path)))[-1]


def _discover_dataset(input_root: Path, preferred_subdir: str, patterns: list[str], label: str) -> Path:
    roots: list[Path] = []
    preferred = input_root / preferred_subdir
    if preferred.exists():
        roots.append(preferred)
    roots.append(input_root)

    matches: list[Path] = []
    for root in roots:
        for pattern in patterns:
            matches.extend(root.rglob(pattern))

    unique_matches = sorted({path.resolve() for path in matches if path.exists()})
    if not unique_matches:
        raise FileNotFoundError(f"No {label} dataset found under {input_root}")

    return _latest_match(unique_matches)


def _hashed_output_path_for_input(input_path: Path, hashed_dir: Path, name_suffix: str = "") -> Path:
    suffix = f"_{name_suffix}" if name_suffix else ""
    stem = input_path.stem.lower()

    if "consolidated_metadata" in stem or stem.endswith("_metadata"):
        return hashed_dir / f"metadata{suffix}.parquet"

    if "consolidated_waveforms" in stem or stem.endswith("_waveforms"):
        return hashed_dir / f"waveforms{suffix}.parquet"

    if stem.startswith("patients-") or stem == "patients" or "patients" in stem:
        return hashed_dir / f"patients{suffix}.parquet"

    return hashed_dir / f"{input_path.stem}{suffix}.parquet"


def _load_cross_summary(summary_csv: Path) -> dict[str, int] | None:
    if not summary_csv.exists():
        logger.warning("Audit summary not found: %s", summary_csv)
        return

    with summary_csv.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    if not rows:
        logger.warning("Audit summary is empty: %s", summary_csv)
        return None

    row = rows[0]
    return {
        "patients_unique_ids": int(row.get("patients_unique_ids", 0)),
        "metadata_unique_ids": int(row.get("metadata_unique_ids", 0)),
        "ids_in_both": int(row.get("ids_in_both", 0)),
        "ids_only_patients": int(row.get("ids_only_patients", 0)),
        "ids_only_metadata": int(row.get("ids_only_metadata", 0)),
    }


def _log_before_after_cross_validation(before_summary: Path, after_summary: Path) -> None:
    before = _load_cross_summary(before_summary)
    after = _load_cross_summary(after_summary)
    if not before or not after:
        return

    logger.info(
        "Unique IDs | patients before=%d after=%d | metadata before=%d after=%d",
        before["patients_unique_ids"],
        after["patients_unique_ids"],
        before["metadata_unique_ids"],
        after["metadata_unique_ids"],
    )

    if (
        before["patients_unique_ids"] != after["patients_unique_ids"]
        or before["metadata_unique_ids"] != after["metadata_unique_ids"]
    ):
        logger.warning(
            "Unique ID count changed after anonymization: patients(%d -> %d), metadata(%d -> %d)",
            before["patients_unique_ids"],
            after["patients_unique_ids"],
            before["metadata_unique_ids"],
            after["metadata_unique_ids"],
        )
    else:
        logger.info("Validation passed: unique ID counts were preserved after anonymization.")


def run(args: argparse.Namespace) -> None:
    base_dir = resolve_base_dir(args.base)
    input_root = resolve_input_path(base_dir, args.input_root, must_exist=True)
    output_root = resolve_output_dir(base_dir, args.output_root, create=True)
    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    anonymized_root_rel = Path(args.output_root) / "anonymized"
    anonymized_root = resolve_output_dir(base_dir, str(anonymized_root_rel), create=True)

    staging_rel = anonymized_root_rel / "staging"
    staging_dir = resolve_output_dir(base_dir, str(staging_rel), create=True)

    datasets_rel = anonymized_root_rel / "datasets"
    datasets_dir = resolve_output_dir(base_dir, str(datasets_rel), create=True)

    reports_rel = Path(args.reports_output) if args.reports_output else (Path(args.output_root) / "reports" / "id_audit")
    reports_dir = resolve_output_dir(base_dir, str(reports_rel), create=True)
    before_reports_dir = resolve_output_dir(base_dir, str(reports_dir / "before_anonymization"), create=True)
    after_reports_dir = resolve_output_dir(base_dir, str(reports_dir / "after_anonymization"), create=True)

    patients_path = _discover_dataset(
        input_root=input_root,
        preferred_subdir="patients",
        patterns=PATIENTS_DATASET_PATTERNS,
        label="patients",
    )
    metadata_path = _discover_dataset(
        input_root=input_root,
        preferred_subdir="waveforms",
        patterns=METADATA_DATASET_PATTERNS,
        label="metadata",
    )
    waveforms_path = _discover_dataset(
        input_root=input_root,
        preferred_subdir="waveforms",
        patterns=WAVEFORMS_DATASET_PATTERNS,
        label="waveforms",
    )

    logger.info("ANONYMIZE auto input root: %s", input_root)
    logger.info("Resolved patients dataset: %s", patients_path)
    logger.info("Resolved metadata dataset: %s", metadata_path)
    logger.info("Resolved waveforms dataset: %s", waveforms_path)

    before_audit_args = argparse.Namespace(
        base=str(base_dir),
        mode="cross",
        patients_input=str(patients_path),
        metadata_input=str(metadata_path),
        patients_before_input=None,
        patients_after_input=None,
        metadata_before_input=None,
        metadata_after_input=None,
        output=str(before_reports_dir),
    )

    logger.info("ANONYMIZE step 1/5: running pre-anonymization audit")
    run_id_audit(before_audit_args)

    mapping_input = before_reports_dir / "unique_ids_both_sources.csv"
    if not mapping_input.exists():
        raise FileNotFoundError(f"Mapping input not generated: {mapping_input}")

    hash_args = argparse.Namespace(
        base=str(base_dir),
        normalize_inputs=None,
        mapping_input=str(mapping_input),
        mapping_output=str(staging_dir / f"id_map_{run_tag}.parquet"),
        apply_inputs=[str(metadata_path), str(waveforms_path), str(patients_path)],
        output_dir=str(staging_dir),
        debug_csv=str(staging_dir / f"missing_ids_{run_tag}.csv"),
        column=args.column,
        drop_columns=args.drop_columns,
        float_columns=args.float_columns,
        int_columns=args.int_columns,
        metadata_before=None,
        metadata_after=None,
        metadata=str(metadata_path),
        chunk_size=args.chunk_size,
        salt=args.salt,
        name_suffix=run_tag,
        skip_normalize=True,
        skip_mapping=False,
        skip_apply=False,
    )

    logger.info("ANONYMIZE step 2/5: applying hash pipeline")
    run_hash_orchestrator(hash_args)

    id_map_path = staging_dir / f"id_map_{run_tag}.parquet"
    patients_root = input_root / "patients"
    if id_map_path.exists() and patients_root.exists():
        logger.info("ANONYMIZE step 2b/5: enriching id_map with annotation columns")
        _enrich_id_map_with_annotations(id_map_path, patients_root, reports_dir, run_tag)

    parquet_args = argparse.Namespace(
        base=str(base_dir),
        input=str(staging_dir),
        output=str(datasets_dir),
        workers=args.workers,
        block_size_mb=args.block_size_mb,
        name_prefix="",
        compact_names=True,
        name_date_suffix=run_tag,
        skip_metadata_output=True,
    )

    logger.info("ANONYMIZE step 3/5: generating final ERG datasets")
    run_consolidated_to_parquet(parquet_args)

    after_audit_args = argparse.Namespace(
        base=str(base_dir),
        mode="cross",
        patients_input=str(_hashed_output_path_for_input(patients_path, staging_dir, run_tag)),
        metadata_input=str(_hashed_output_path_for_input(metadata_path, staging_dir, run_tag)),
        patients_before_input=None,
        patients_after_input=None,
        metadata_before_input=None,
        metadata_after_input=None,
        output=str(after_reports_dir),
    )

    logger.info("ANONYMIZE step 4/5: running post-anonymization audit with full report set")
    run_id_audit(after_audit_args)

    logger.info("ANONYMIZE step 5/5: validating ID preservation between before and after audits")
    _log_before_after_cross_validation(
        before_summary=before_reports_dir / "unique_id_counts_summary.csv",
        after_summary=after_reports_dir / "unique_id_counts_summary.csv",
    )

    logger.info("ANONYMIZE finished successfully")
    logger.info("Anonymized staging data: %s", staging_dir)
    logger.info("Anonymized analytical datasets: %s", datasets_dir)
    logger.info("Audit reports (before): %s", before_reports_dir)
    logger.info("Audit reports (after): %s", after_reports_dir)
    logger.info("Output root: %s", output_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Single-entry anonymization runner: discover input datasets under output/, audit IDs, hash, and generate final data."
    )
    parser.add_argument("--base", default=".", help="Base directory")
    parser.add_argument("--input-root", default="output", help="Root folder containing patients/ and waveforms/")
    parser.add_argument(
        "--output-root",
        default="output/data",
        help="Root folder for generated anonymize outputs (anonymized/ and reports/ are created inside)",
    )
    parser.add_argument(
        "--reports-output",
        default=None,
        help="Optional override for id audit output directory (default: <output-root>/reports/id_audit)",
    )
    parser.add_argument("--column", default="patient_unique_id", help="ID column name")
    parser.add_argument(
        "--drop-columns",
        default="source_file,id_prontuario,nome_paciente,data_nascimento,sexo,ano_nascimento,PatientID,PatientBirthdate,TestingDate,data_realizada_do_teste,data_teste",
        help="Comma-separated columns to drop in hash stage",
    )
    parser.add_argument("--float-columns", default="voltage_uV,pupil_mm,time_ms", help="Comma-separated float columns")
    parser.add_argument("--int-columns", default="test_id", help="Comma-separated int columns")
    parser.add_argument("--chunk-size", type=int, default=50000, help="Hash stage chunk size")
    parser.add_argument("--salt", default=None, help="Optional bcrypt salt")
    parser.add_argument("--workers", type=int, default=None, help="Workers for final parquet stage")
    parser.add_argument("--block-size-mb", type=int, default=64, help="Block size for final parquet stage")
    return parser
