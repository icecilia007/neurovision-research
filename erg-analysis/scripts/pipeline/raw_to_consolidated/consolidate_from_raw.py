"""Consolidation single entrypoint: patients + waveforms + id_audit report.

Runs patient_preparation and waveform_consolidation in sequence, then
generates the id_audit cross-report comparing the two produced datasets.
"""

import argparse
import logging
from pathlib import Path

from analysis.audit_unique_patient_ids import run as run_id_audit
from common.path_utils import resolve_base_dir, resolve_input_path, resolve_output_dir
from pipeline.raw_to_consolidated import run_patient_preparation, run_waveform_consolidation


logger = logging.getLogger(__name__)

PATIENTS_PATTERNS = [
    "patients-*.parquet",
    "patients-*.csv",
]

METADATA_PATTERNS = [
    "consolidated_metadata.parquet",
    "*consolidated_metadata*.parquet",
]


def _latest_match(paths: list[Path]) -> Path:
    return sorted(paths, key=lambda p: (p.stat().st_mtime, str(p)))[-1]


def _discover_dataset(root: Path, patterns: list[str], label: str) -> Path:
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(root.rglob(pattern))
    unique = sorted({p.resolve() for p in matches if p.exists()})
    if not unique:
        raise FileNotFoundError(f"No {label} dataset found under {root}")
    return _latest_match(unique)


def run(args: argparse.Namespace) -> None:
    base_dir = resolve_base_dir(args.base)
    patients_out = resolve_output_dir(base_dir, args.patients_output, create=True)
    waveforms_out = resolve_output_dir(base_dir, args.waveforms_output, create=True)
    reports_out = resolve_output_dir(base_dir, args.reports_output, create=True)

    prepare_args = argparse.Namespace(
        base=str(base_dir),
        input=args.patients_input,
        output=args.patients_output,
        workers=args.workers,
        output_partitions=args.patients_partitions,
    )

    waveform_args = argparse.Namespace(
        base=str(base_dir),
        input=args.waveforms_input,
        output=args.waveforms_output,
        workers=args.workers,
        metadata_partitions=args.metadata_partitions,
        waveform_partitions=args.waveform_partitions,
        max_records_per_file=args.max_records_per_file,
    )

    logger.info("CONSOLIDATE step 1/3: preparing patients")
    run_patient_preparation(prepare_args)

    logger.info("CONSOLIDATE step 2/3: consolidating waveforms")
    run_waveform_consolidation(waveform_args)

    logger.info("CONSOLIDATE step 3/3: running id_audit cross-report")

    patients_path = _discover_dataset(patients_out, PATIENTS_PATTERNS, "patients")
    consolidated_dir = resolve_input_path(base_dir, str(Path(args.waveforms_output) / "consolidated"), must_exist=True)
    metadata_path = _discover_dataset(consolidated_dir, METADATA_PATTERNS, "metadata")

    audit_args = argparse.Namespace(
        base=str(base_dir),
        mode="cross",
        patients_input=str(patients_path),
        metadata_input=str(metadata_path),
        patients_before_input=None,
        patients_after_input=None,
        metadata_before_input=None,
        metadata_after_input=None,
        output=str(reports_out),
    )
    run_id_audit(audit_args)

    logger.info("CONSOLIDATE finished successfully")
    logger.info("Patients: %s", patients_out)
    logger.info("Waveforms: %s", waveforms_out / "consolidated")
    logger.info("Id audit report: %s", reports_out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Unified consolidation runner: patient_preparation + waveform_consolidation "
            "followed by id_audit cross-report."
        )
    )
    parser.add_argument("--base", default=".", help="Base directory")
    parser.add_argument("--patients-input", required=True, help="Input dir/file with patient CSVs")
    parser.add_argument("--waveforms-input", required=True, help="Input dir with waveform CSVs")
    parser.add_argument("--patients-output", default="output/patients", help="Output dir for patients parquet")
    parser.add_argument(
        "--waveforms-output",
        default="output/waveforms",
        help="Output dir for waveforms (consolidated/ is created inside)",
    )
    parser.add_argument(
        "--reports-output",
        default="output/reports/id_audit",
        help="Output dir for id_audit cross-report CSVs",
    )
    parser.add_argument("--workers", type=int, default=None, help="Workers for both consolidation steps")
    parser.add_argument("--patients-partitions", type=int, default=None, help="Target partitions for patients parquet")
    parser.add_argument("--metadata-partitions", type=int, default=None, help="Target partitions for consolidated_metadata")
    parser.add_argument("--waveform-partitions", type=int, default=None, help="Target partitions for consolidated_waveforms")
    parser.add_argument("--max-records-per-file", type=int, default=None, help="spark.sql.files.maxRecordsPerFile")
    return parser
