"""Patient preparation stage.

Reads patient CSV inputs, builds patient_unique_id, and writes Parquet outputs.
"""

import argparse
import concurrent.futures
import csv
import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import chardet

SCRIPTS_ROOT = Path(__file__).resolve().parents[2]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.id_utils import (
    build_patient_unique_id,
    extract_prontuario_and_name,
    format_birth_metadata,
    format_test_metadata,
    normalize_name,
)
from common.logging_utils import configure_logging
from common.path_utils import resolve_base_dir, resolve_input_path, resolve_output_dir


logger = logging.getLogger(__name__)


def apply_target_partitions(df, target_partitions: int | None):
    """Adjust DataFrame partitions to reduce excessive output part files."""
    if not target_partitions or target_partitions <= 0:
        return df
    current = df.rdd.getNumPartitions()
    if target_partitions < current:
        return df.coalesce(target_partitions)
    if target_partitions > current:
        return df.repartition(target_partitions)
    return df


def find_csv_files(base: Path, relative_path: str) -> List[Path]:
    search_path = resolve_input_path(base, relative_path, must_exist=True)
    csv_files = [p for p in search_path.rglob("*.csv")] if search_path.is_dir() else [search_path]
    logger.info("Found %d CSV files under %s", len(csv_files), search_path)
    return csv_files


def detect_encoding(path: Path, num_bytes: int = 2048) -> str:
    try:
        with open(path, "rb") as file_obj:
            raw = file_obj.read(num_bytes)
        guess = chardet.detect(raw)
        return guess["encoding"] or "latin-1"
    except Exception:
        return "latin-1"


def build_spark_session(workers: int | None):
    try:
        from pyspark.sql import SparkSession
    except Exception as exc:
        raise RuntimeError("PySpark is required for patient preparation.") from exc

    builder = SparkSession.builder.appName("erg-patient-preparation")
    if workers and workers > 0:
        builder = builder.master(f"local[{workers}]")
        shuffle_parts = max(2, workers * 2)
    else:
        builder = builder.master("local[*]")
        shuffle_parts = max(8, os.cpu_count() or 4)

    return (
        builder.config("spark.sql.shuffle.partitions", str(shuffle_parts))
        .config("spark.default.parallelism", str(shuffle_parts))
        .getOrCreate()
    )


def try_read_csv_rows_with_header_guesses(path: Path) -> List[Dict[str, str]]:
    enc_guess = detect_encoding(path)
    encodings = [enc_guess, "utf-8-sig", "latin-1", "windows-1252"]
    expected_tokens = ["patientid", "id entered", "birth", "testing", "when test"]

    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, newline="") as file_obj:
                rows = list(csv.reader(file_obj))
        except Exception:
            continue

        if not rows:
            continue

        header_idx = None
        for idx in (0, 1, 2):
            if idx >= len(rows):
                continue
            header_cells = [str(cell).strip().lower() for cell in rows[idx]]
            if any(any(token in cell for token in expected_tokens) for cell in header_cells):
                header_idx = idx
                break

        if header_idx is None:
            header = [f"col_{i}" for i in range(len(rows[0]))]
            data_rows = rows
        else:
            header = []
            for i, col_name in enumerate(rows[header_idx]):
                col = str(col_name).strip()
                header.append(col if col else f"col_{i}")
            data_rows = rows[header_idx + 1 :]

        parsed_rows: List[Dict[str, str]] = []
        for row in data_rows:
            if not any(str(cell).strip() for cell in row):
                continue
            row_vals = [str(cell).strip() for cell in row]
            if len(row_vals) < len(header):
                row_vals.extend([""] * (len(header) - len(row_vals)))
            elif len(row_vals) > len(header):
                row_vals = row_vals[: len(header)]
            parsed_rows.append(dict(zip(header, row_vals)))

        if parsed_rows:
            return parsed_rows

    raise ValueError(f"Unable to parse CSV with known encodings/header guesses: {path}")


def normalize_row_columns(row: Dict[str, str]) -> Dict[str, str]:
    normalized = dict(row)
    found_patient_id = None
    found_birth = None
    found_testing = None

    for col in row.keys():
        col_low = str(col).strip().lower()
        value = row.get(col, "")
        if found_patient_id is None and ("patientid" in col_low or "id entered" in col_low):
            found_patient_id = value
        elif found_birth is None and "birth" in col_low and "date" in col_low:
            found_birth = value
        elif found_testing is None and (
            "when test" in col_low or "testing" in col_low or "when test occcured" in col_low
        ):
            found_testing = value

    if found_patient_id is None:
        first_col = next(iter(row.keys()), None)
        found_patient_id = row.get(first_col, "") if first_col is not None else ""

    if found_birth is None:
        for col in row.keys():
            if "birth" in str(col).lower():
                found_birth = row.get(col, "")
                break

    if found_testing is None:
        for col in row.keys():
            col_low = str(col).lower()
            if "test" in col_low or "when" in col_low:
                found_testing = row.get(col, "")
                break

    normalized["PatientID"] = str(found_patient_id or "").strip()
    normalized["PatientBirthdate"] = str(found_birth or "").strip()
    normalized["TestingDate"] = str(found_testing or "").strip()
    return normalized


def build_patient_unique_id_from_row(patientid_raw: str, birthdate_raw: str, testingdate_raw: str) -> str:
    prontuario, name = extract_prontuario_and_name(patientid_raw or "")
    return build_patient_unique_id(prontuario or "", name or "", birthdate_raw, testingdate_raw)


def process_file(path: Path) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    logger.info("Processing %s", path)
    try:
        rows = try_read_csv_rows_with_header_guesses(path)
        patient_rows: List[Dict[str, str]] = []
        mapping_rows: List[Dict[str, str]] = []

        for raw_row in rows:
            row = normalize_row_columns(raw_row)
            patient_unique_id = build_patient_unique_id_from_row(
                row.get("PatientID", ""),
                row.get("PatientBirthdate", ""),
                row.get("TestingDate", ""),
            )

            birthdate_raw = row.get("PatientBirthdate", "")
            birthdate_formatted = format_birth_metadata(birthdate_raw)
            birthdate_to_store = birthdate_formatted or str(birthdate_raw or "").strip()
            testing_raw = row.get("TestingDate", "")
            testing_formatted = format_test_metadata(testing_raw)
            testing_to_store = testing_formatted or str(testing_raw or "").strip()

            # Keep patients output aligned with consolidated metadata format (YY/MM/DD).
            row["PatientBirthdate"] = birthdate_to_store
            row["data_nascimento"] = birthdate_to_store
            row["TestingDate"] = testing_to_store
            row["data_teste"] = testing_to_store

            row["patient_unique_id"] = patient_unique_id
            patient_rows.append(row)

            prontuario, nome = extract_prontuario_and_name(row.get("PatientID", ""))
            nome = normalize_name(nome or "")
            mapping_rows.append(
                {
                    "prontuario": prontuario or "",
                    "nome_completo": nome or "",
                    "data_nascimento": birthdate_to_store,
                    "data_teste": testing_to_store,
                    "patient_unique_id": patient_unique_id,
                }
            )

        logger.info("Finished %s -> %d rows", path, len(patient_rows))
        return patient_rows, mapping_rows
    except Exception as exc:
        logger.exception("Error processing %s: %s", path, exc)
        return [], []


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepares patient data by reading multiple CSV files and creating patient_unique_id."
    )
    parser.add_argument("--input", required=True, help="Relative path to scan CSV files")
    parser.add_argument("--base", default=".", help="Base directory")
    parser.add_argument("--output", required=True, help="Output directory for generated files")
    parser.add_argument("--workers", type=int, default=None, help="Parallel workers")
    parser.add_argument(
        "--output-partitions",
        type=int,
        default=None,
        help="Target number of Spark output partitions/files for parquet writes",
    )
    return parser


def run(args: argparse.Namespace) -> None:
    base_dir = resolve_base_dir(args.base)
    out_dir = resolve_output_dir(base_dir, args.output, create=True)

    files = find_csv_files(base_dir, args.input)
    if not files:
        logger.error("No CSV files found. Exiting.")
        return

    max_workers = args.workers or min(32, (os.cpu_count() or 2) + 4)
    patient_row_count = 0
    mapping_row_count = 0

    tmp_dir = Path(tempfile.mkdtemp(prefix="erg_patient_prepare_", dir=str(out_dir)))
    patients_jsonl_path = tmp_dir / "patients_rows.jsonl"
    mapping_jsonl_path = tmp_dir / "mapping_rows.jsonl"

    try:
        with open(patients_jsonl_path, "w", encoding="utf-8") as patients_out, open(
            mapping_jsonl_path, "w", encoding="utf-8"
        ) as mapping_out:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {executor.submit(process_file, file_path): file_path for file_path in files}
                for future in concurrent.futures.as_completed(future_map):
                    patient_rows, mapping_rows = future.result()

                    for row in patient_rows:
                        patients_out.write(json.dumps(row, ensure_ascii=True))
                        patients_out.write("\n")
                    patient_row_count += len(patient_rows)

                    for row in mapping_rows:
                        mapping_out.write(json.dumps(row, ensure_ascii=True))
                        mapping_out.write("\n")
                    mapping_row_count += len(mapping_rows)

        if patient_row_count == 0:
            logger.error("No records produced from files. Exiting.")
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        patients_parquet_path = out_dir / f"patients-{timestamp}.parquet"
        mapping_parquet_path = out_dir / f"patients_id_mapping-{timestamp}.parquet"

        spark = build_spark_session(args.workers)
        spark.sparkContext.setLogLevel("WARN")
        try:
            patients_df = spark.read.json(str(patients_jsonl_path))
            mapping_df = spark.read.json(str(mapping_jsonl_path)).dropDuplicates(["patient_unique_id"])

            apply_target_partitions(patients_df, args.output_partitions).write.mode("overwrite").parquet(
                str(patients_parquet_path)
            )
            apply_target_partitions(mapping_df, args.output_partitions).write.mode("overwrite").parquet(
                str(mapping_parquet_path)
            )
        finally:
            spark.stop()

        logger.info(
            "Wrote patients Parquet to %s and mapping Parquet to %s (patient_rows=%d, mapping_rows=%d)",
            patients_parquet_path,
            mapping_parquet_path,
            patient_row_count,
            mapping_row_count,
        )
    finally:
        for temp_path in (patients_jsonl_path, mapping_jsonl_path):
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                logger.warning("Unable to delete temporary file %s", temp_path)
        try:
            tmp_dir.rmdir()
        except Exception:
            pass


def main() -> None:
    configure_logging()
    args = build_parser().parse_args()
    run(args)


if __name__ == "__main__":
    main()
