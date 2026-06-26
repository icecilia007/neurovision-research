"""Audit unique patient IDs across patients and consolidated metadata datasets.

Generates:
- unique ID counts per dataset
- overlap counts between datasets
- a CSV with unique IDs and identity fields from both datasets
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.id_utils import extract_prontuario_and_name, normalize_name as normalize_name_token
from common.logging_utils import configure_logging
from common.path_utils import resolve_base_dir, resolve_input_path, resolve_output_dir


logger = logging.getLogger(__name__)


PATIENTS_PATTERNS = [
    "patients-*.parquet",
    "patients-*.csv",
    "*patients*.parquet",
    "*patients*.csv",
]

METADATA_PATTERNS = [
    "consolidated_metadata.parquet",
    "consolidated_metadata.csv",
    "*metadata*.parquet",
    "*metadata*.csv",
]

CANDIDATE_COLS = [
    "patient_unique_id",
    "nome_paciente",
    "nome_completo",
    "id_prontuario",
    "prontuario",
    "data_nascimento",
    "PatientBirthdate",
    "data_realizada_do_teste",
    "data_teste",
    "TestingDate",
    "test_id",
    "PatientID",
]


def _pick_latest_from_dir(folder: Path, patterns: list[str]) -> Path:
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(folder.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No files found under {folder} with patterns {patterns}")
    return sorted(matches)[-1]


def resolve_dataset_path(base_dir: Path, raw_path: str, patterns: list[str]) -> Path:
    path = resolve_input_path(base_dir, raw_path, must_exist=True)
    if path.is_dir():
        # Spark-style parquet outputs are directories ending with .parquet.
        if path.suffix.lower() == ".parquet":
            return path
        return resolve_input_path(base_dir, str(_pick_latest_from_dir(path, patterns)), must_exist=True)
    return path


def read_table(path: Path, candidate_columns: list[str]) -> pd.DataFrame:
    suffix = path.suffix.lower()

    if path.is_dir() or suffix == ".parquet":
        import pyarrow.dataset as ds

        dataset = ds.dataset(str(path), format="parquet")
        available = dataset.schema.names
        cols = [col for col in candidate_columns if col in available]
        if not cols:
            raise ValueError(f"No required columns found in parquet dataset: {path}")
        return pd.read_parquet(path, columns=cols)

    if suffix == ".csv":
        header_cols = pd.read_csv(path, nrows=0, low_memory=False).columns.tolist()
        cols = [col for col in candidate_columns if col in header_cols]
        if not cols:
            raise ValueError(f"No required columns found in csv dataset: {path}")
        return pd.read_csv(path, usecols=cols, dtype=str, low_memory=False)

    raise ValueError(f"Unsupported dataset format: {path}")


def first_non_empty_series(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    available = [col for col in columns if col in df.columns]
    if not available:
        return pd.Series([""] * len(df), index=df.index, dtype="string")

    tmp = df[available].fillna("").astype(str)
    for col in tmp.columns:
        tmp[col] = tmp[col].str.strip()
    tmp = tmp.replace("", pd.NA)
    return tmp.bfill(axis=1).iloc[:, 0].fillna("")


def non_empty_agg(series: pd.Series) -> str:
    for value in series:
        text = "" if pd.isna(value) else str(value).strip()
        if text:
            return text
    return ""


def build_unique_identity_table(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    if "patient_unique_id" not in df.columns:
        raise ValueError(f"Column patient_unique_id not found for source {source_name}")

    work = df.copy()

    work["patient_unique_id"] = work["patient_unique_id"].fillna("").astype(str).str.strip()
    work = work[work["patient_unique_id"] != ""].copy()

    if "PatientID" in work.columns:
        parsed = work["PatientID"].fillna("").astype(str).map(extract_prontuario_and_name)
        pront_from_patientid = parsed.map(lambda pair: pair[0] or "")
        name_from_patientid = parsed.map(lambda pair: normalize_name_token(pair[1] or ""))
    else:
        pront_from_patientid = pd.Series([""] * len(work), index=work.index)
        name_from_patientid = pd.Series([""] * len(work), index=work.index)

    id_prontuario_base = first_non_empty_series(work, ["id_prontuario", "prontuario"]) 
    nome_base = first_non_empty_series(work, ["nome_paciente", "nome_completo"])
    data_nascimento_base = first_non_empty_series(work, ["data_nascimento", "PatientBirthdate"])
    data_teste_base = first_non_empty_series(work, ["data_realizada_do_teste", "data_teste", "TestingDate"])
    test_id_base = first_non_empty_series(work, ["test_id"])

    id_prontuario = id_prontuario_base.where(id_prontuario_base != "", pront_from_patientid)
    nome_encontrado = nome_base.where(nome_base != "", name_from_patientid)

    work["id_prontuario"] = id_prontuario.fillna("").astype(str).str.strip()
    work["nome_encontrado"] = nome_encontrado.fillna("").astype(str).str.strip()
    work["data_nascimento"] = data_nascimento_base.fillna("").astype(str).str.strip()
    work["data_teste"] = data_teste_base.fillna("").astype(str).str.strip()
    work["test_id"] = test_id_base.fillna("").astype(str).str.strip()

    unique_table = (
        work.groupby("patient_unique_id", as_index=False)
        .agg(
            {
                "nome_encontrado": non_empty_agg,
                "id_prontuario": non_empty_agg,
                "data_nascimento": non_empty_agg,
                "data_teste": non_empty_agg,
                "test_id": non_empty_agg,
            }
        )
        .sort_values("patient_unique_id")
        .reset_index(drop=True)
    )

    unique_table.insert(0, "source_dataset", source_name)
    return unique_table


def build_id_occurrence_counts(df: pd.DataFrame, count_column_name: str) -> pd.DataFrame:
    if "patient_unique_id" not in df.columns:
        raise ValueError("Column patient_unique_id not found while building occurrence counts")

    ids = df["patient_unique_id"].fillna("").astype(str).str.strip()
    ids = ids[ids != ""]

    counts = ids.value_counts(dropna=False).rename_axis("patient_unique_id").reset_index(name=count_column_name)
    return counts


def build_comparison_table(patients_unique: pd.DataFrame, metadata_unique: pd.DataFrame) -> pd.DataFrame:
    left = patients_unique.drop(columns=["source_dataset"]).rename(
        columns={
            "nome_encontrado": "patients_nome_encontrado",
            "id_prontuario": "patients_id_prontuario",
            "data_nascimento": "patients_data_nascimento",
            "data_teste": "patients_data_teste",
            "test_id": "patients_test_id",
        }
    )
    right = metadata_unique.drop(columns=["source_dataset"]).rename(
        columns={
            "nome_encontrado": "metadata_nome_encontrado",
            "id_prontuario": "metadata_id_prontuario",
            "data_nascimento": "metadata_data_nascimento",
            "data_teste": "metadata_data_teste",
            "test_id": "metadata_test_id",
        }
    )

    comparison = left.merge(right, on="patient_unique_id", how="outer", indicator=True)
    comparison["presence"] = comparison.pop("_merge").astype(str).map(
        {"left_only": "only_patients", "right_only": "only_metadata", "both": "both"}
    )

    return comparison.sort_values(["presence", "patient_unique_id"]).reset_index(drop=True)


def build_before_after_table(
    before_unique: pd.DataFrame,
    after_unique: pd.DataFrame,
    dataset_name: str,
) -> pd.DataFrame:
    before = before_unique.drop(columns=["source_dataset"]).rename(
        columns={
            "nome_encontrado": "before_nome_encontrado",
            "id_prontuario": "before_id_prontuario",
            "data_nascimento": "before_data_nascimento",
            "data_teste": "before_data_teste",
            "test_id": "before_test_id",
        }
    )
    after = after_unique.drop(columns=["source_dataset"]).rename(
        columns={
            "nome_encontrado": "after_nome_encontrado",
            "id_prontuario": "after_id_prontuario",
            "data_nascimento": "after_data_nascimento",
            "data_teste": "after_data_teste",
            "test_id": "after_test_id",
        }
    )

    comparison = before.merge(after, on="patient_unique_id", how="outer", indicator=True)
    comparison["presence"] = comparison.pop("_merge").astype(str).map(
        {"left_only": "only_before", "right_only": "only_after", "both": "both"}
    )
    comparison.insert(0, "dataset", dataset_name)

    return comparison.sort_values(["presence", "patient_unique_id"]).reset_index(drop=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit unique patient_unique_id across patients and consolidated metadata datasets."
    )
    parser.add_argument("--base", default=".", help="Base directory")
    parser.add_argument(
        "--mode",
        choices=["cross", "before-after"],
        default="cross",
        help="cross=patients vs metadata in same snapshot; before-after=compare snapshots",
    )
    parser.add_argument(
        "--patients-input",
        help="Path to patients dataset file or directory (parquet/csv). Required in cross mode.",
    )
    parser.add_argument(
        "--metadata-input",
        help="Path to consolidated_metadata dataset file or directory (parquet/csv). Required in cross mode.",
    )
    parser.add_argument(
        "--patients-before-input",
        help="Patients dataset path for before snapshot (parquet/csv). Required in before-after mode.",
    )
    parser.add_argument(
        "--patients-after-input",
        help="Patients dataset path for after snapshot (parquet/csv). Required in before-after mode.",
    )
    parser.add_argument(
        "--metadata-before-input",
        help="Metadata dataset path for before snapshot (parquet/csv). Required in before-after mode.",
    )
    parser.add_argument(
        "--metadata-after-input",
        help="Metadata dataset path for after snapshot (parquet/csv). Required in before-after mode.",
    )
    parser.add_argument("--output", required=True, help="Output directory for audit CSVs")
    return parser


def _require_args(args: argparse.Namespace, fields: list[str], mode_name: str) -> None:
    missing = [field for field in fields if not getattr(args, field)]
    if missing:
        missing_flags = ", ".join(f"--{field.replace('_', '-')}" for field in missing)
        raise ValueError(f"Missing required arguments for mode '{mode_name}': {missing_flags}")


def run_cross(args: argparse.Namespace, base_dir: Path, out_dir: Path) -> None:
    _require_args(args, ["patients_input", "metadata_input"], "cross")

    patients_path = resolve_dataset_path(base_dir, args.patients_input, PATIENTS_PATTERNS)
    metadata_path = resolve_dataset_path(base_dir, args.metadata_input, METADATA_PATTERNS)

    logger.info("Patients dataset: %s", patients_path)
    logger.info("Metadata dataset: %s", metadata_path)

    df_patients = read_table(patients_path, CANDIDATE_COLS)
    df_metadata = read_table(metadata_path, CANDIDATE_COLS)

    patients_id_counts = build_id_occurrence_counts(df_patients, "patients_row_count")
    metadata_id_counts = build_id_occurrence_counts(df_metadata, "metadata_row_count")

    unique_patients = build_unique_identity_table(df_patients, "patients")
    unique_metadata = build_unique_identity_table(df_metadata, "consolidated_metadata")

    comparison = build_comparison_table(unique_patients, unique_metadata)

    patients_unique_count = len(unique_patients)
    metadata_unique_count = len(unique_metadata)
    both_count = int((comparison["presence"] == "both").sum())
    only_patients_count = int((comparison["presence"] == "only_patients").sum())
    only_metadata_count = int((comparison["presence"] == "only_metadata").sum())

    logger.info("Unique patient_unique_id count (patients): %d", patients_unique_count)
    logger.info("Unique patient_unique_id count (consolidated_metadata): %d", metadata_unique_count)
    logger.info("Unique IDs present in both: %d", both_count)
    logger.info("Unique IDs only in patients: %d", only_patients_count)
    logger.info("Unique IDs only in consolidated_metadata: %d", only_metadata_count)

    combined_unique_out = out_dir / "unique_ids_both_sources.csv"
    summary_out = out_dir / "unique_id_counts_summary.csv"
    comparison_out = out_dir / "unique_ids_comparison.csv"
    exclusive_counts_out = out_dir / "unique_ids_only_one_base_counts.csv"
    exclusive_summary_out = out_dir / "unique_ids_only_one_base_summary.csv"

    pd.concat([unique_patients, unique_metadata], ignore_index=True).to_csv(
        combined_unique_out,
        index=False,
        encoding="utf-8-sig",
    )

    pd.DataFrame(
        [
            {
                "patients_unique_ids": patients_unique_count,
                "metadata_unique_ids": metadata_unique_count,
                "ids_in_both": both_count,
                "ids_only_patients": only_patients_count,
                "ids_only_metadata": only_metadata_count,
            }
        ]
    ).to_csv(summary_out, index=False, encoding="utf-8-sig")

    comparison.to_csv(comparison_out, index=False, encoding="utf-8-sig")

    exclusive_counts = comparison[
        [
            "patient_unique_id",
            "presence",
            "patients_nome_encontrado",
            "patients_id_prontuario",
            "patients_data_nascimento",
            "patients_data_teste",
            "patients_test_id",
            "metadata_nome_encontrado",
            "metadata_id_prontuario",
            "metadata_data_nascimento",
            "metadata_data_teste",
            "metadata_test_id",
        ]
    ].merge(
        patients_id_counts,
        on="patient_unique_id",
        how="left",
    )
    exclusive_counts = exclusive_counts.merge(
        metadata_id_counts,
        on="patient_unique_id",
        how="left",
    )
    exclusive_counts["patients_row_count"] = exclusive_counts["patients_row_count"].fillna(0).astype(int)
    exclusive_counts["metadata_row_count"] = exclusive_counts["metadata_row_count"].fillna(0).astype(int)
    exclusive_counts = exclusive_counts[exclusive_counts["presence"].isin(["only_patients", "only_metadata"])]
    exclusive_counts = exclusive_counts.sort_values(["presence", "patient_unique_id"]).reset_index(drop=True)

    exclusive_counts.to_csv(exclusive_counts_out, index=False, encoding="utf-8-sig")

    exclusive_summary = (
        exclusive_counts.groupby("presence", as_index=False)
        .agg(
            unique_ids_count=("patient_unique_id", "nunique"),
            patients_rows_total=("patients_row_count", "sum"),
            metadata_rows_total=("metadata_row_count", "sum"),
        )
        .sort_values("presence")
        .reset_index(drop=True)
    )
    exclusive_summary.to_csv(exclusive_summary_out, index=False, encoding="utf-8-sig")

    logger.info("Saved: %s", combined_unique_out)
    logger.info("Saved: %s", summary_out)
    logger.info("Saved: %s", comparison_out)
    logger.info("Saved: %s", exclusive_counts_out)
    logger.info("Saved: %s", exclusive_summary_out)


def run_before_after(args: argparse.Namespace, base_dir: Path, out_dir: Path) -> None:
    _require_args(
        args,
        [
            "patients_before_input",
            "patients_after_input",
            "metadata_before_input",
            "metadata_after_input",
        ],
        "before-after",
    )

    patients_before_path = resolve_dataset_path(base_dir, args.patients_before_input, PATIENTS_PATTERNS)
    patients_after_path = resolve_dataset_path(base_dir, args.patients_after_input, PATIENTS_PATTERNS)
    metadata_before_path = resolve_dataset_path(base_dir, args.metadata_before_input, METADATA_PATTERNS)
    metadata_after_path = resolve_dataset_path(base_dir, args.metadata_after_input, METADATA_PATTERNS)

    logger.info("Patients before dataset: %s", patients_before_path)
    logger.info("Patients after dataset: %s", patients_after_path)
    logger.info("Metadata before dataset: %s", metadata_before_path)
    logger.info("Metadata after dataset: %s", metadata_after_path)

    patients_before_df = read_table(patients_before_path, CANDIDATE_COLS)
    patients_after_df = read_table(patients_after_path, CANDIDATE_COLS)
    metadata_before_df = read_table(metadata_before_path, CANDIDATE_COLS)
    metadata_after_df = read_table(metadata_after_path, CANDIDATE_COLS)

    patients_before_unique = build_unique_identity_table(patients_before_df, "patients_before")
    patients_after_unique = build_unique_identity_table(patients_after_df, "patients_after")
    metadata_before_unique = build_unique_identity_table(metadata_before_df, "metadata_before")
    metadata_after_unique = build_unique_identity_table(metadata_after_df, "metadata_after")

    patients_comparison = build_before_after_table(
        before_unique=patients_before_unique,
        after_unique=patients_after_unique,
        dataset_name="patients",
    )
    metadata_comparison = build_before_after_table(
        before_unique=metadata_before_unique,
        after_unique=metadata_after_unique,
        dataset_name="consolidated_metadata",
    )

    patients_only_before = int((patients_comparison["presence"] == "only_before").sum())
    patients_only_after = int((patients_comparison["presence"] == "only_after").sum())
    patients_both = int((patients_comparison["presence"] == "both").sum())

    metadata_only_before = int((metadata_comparison["presence"] == "only_before").sum())
    metadata_only_after = int((metadata_comparison["presence"] == "only_after").sum())
    metadata_both = int((metadata_comparison["presence"] == "both").sum())

    logger.info("Patients unique IDs before: %d", len(patients_before_unique))
    logger.info("Patients unique IDs after: %d", len(patients_after_unique))
    logger.info("Patients IDs in both snapshots: %d", patients_both)
    logger.info("Patients IDs only before: %d", patients_only_before)
    logger.info("Patients IDs only after: %d", patients_only_after)

    logger.info("Metadata unique IDs before: %d", len(metadata_before_unique))
    logger.info("Metadata unique IDs after: %d", len(metadata_after_unique))
    logger.info("Metadata IDs in both snapshots: %d", metadata_both)
    logger.info("Metadata IDs only before: %d", metadata_only_before)
    logger.info("Metadata IDs only after: %d", metadata_only_after)

    patients_comparison_out = out_dir / "before_after_patients_unique_ids_comparison.csv"
    metadata_comparison_out = out_dir / "before_after_metadata_unique_ids_comparison.csv"
    summary_out = out_dir / "before_after_counts_summary.csv"

    patients_comparison.to_csv(patients_comparison_out, index=False, encoding="utf-8-sig")
    metadata_comparison.to_csv(metadata_comparison_out, index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [
            {
                "patients_before_unique_ids": len(patients_before_unique),
                "patients_after_unique_ids": len(patients_after_unique),
                "patients_ids_in_both": patients_both,
                "patients_ids_only_before": patients_only_before,
                "patients_ids_only_after": patients_only_after,
                "metadata_before_unique_ids": len(metadata_before_unique),
                "metadata_after_unique_ids": len(metadata_after_unique),
                "metadata_ids_in_both": metadata_both,
                "metadata_ids_only_before": metadata_only_before,
                "metadata_ids_only_after": metadata_only_after,
            }
        ]
    ).to_csv(summary_out, index=False, encoding="utf-8-sig")

    logger.info("Saved: %s", patients_comparison_out)
    logger.info("Saved: %s", metadata_comparison_out)
    logger.info("Saved: %s", summary_out)


def run(args: argparse.Namespace) -> None:
    base_dir = resolve_base_dir(args.base)
    out_dir = resolve_output_dir(base_dir, args.output, create=True)

    if args.mode == "before-after":
        run_before_after(args, base_dir, out_dir)
        return

    run_cross(args, base_dir, out_dir)


def main() -> None:
    configure_logging(level=logging.INFO, fmt="%(levelname)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
