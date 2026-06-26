"""Waveform consolidation stage.

Processes raw RETeval waveform CSV files, extracts metadata and waveform values,
and builds consolidated metadata/waveform Parquet outputs.
"""

import argparse
import csv
import logging
import multiprocessing
import os
import re
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pyarrow as pa
import pyarrow.parquet as pq

SCRIPTS_ROOT = Path(__file__).resolve().parents[2]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.id_utils import (
    build_patient_unique_id,
    extract_prontuario_and_name,
    format_birth_metadata,
    format_birth_yyMMdd,
    format_test_yyMMddHHMMSS,
    normalize_name as normalize_name_token,
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


def build_spark_session(
    workers: int | None,
    max_records_per_file: int | None = None,
    heartbeat_interval: str = "60s",
    network_timeout: str = "600s",
):
    try:
        from pyspark.sql import SparkSession
    except Exception as exc:
        raise RuntimeError(
            "PySpark is required for waveform consolidation. Install pyspark and retry."
        ) from exc

    builder = SparkSession.builder.appName("erg-waveform-consolidation")
    if workers and workers > 0:
        builder = builder.master(f"local[{workers}]")
        shuffle_parts = max(2, workers * 2)
    else:
        builder = builder.master("local[*]")
        shuffle_parts = max(8, os.cpu_count() or 4)

    builder = (
        builder.config("spark.sql.shuffle.partitions", str(shuffle_parts))
        .config("spark.default.parallelism", str(shuffle_parts))
        .config("spark.executor.heartbeatInterval", heartbeat_interval)
        .config("spark.network.timeout", network_timeout)
    )
    if max_records_per_file and max_records_per_file > 0:
        builder = builder.config("spark.sql.files.maxRecordsPerFile", str(max_records_per_file))
    return builder.getOrCreate()


def normalize_name(raw_name: str) -> str:
    """Backward-compatible alias to shared name normalization."""
    return normalize_name_token(raw_name)


def read_csv_lines_with_fallback(input_file: str) -> List[List[str]]:
    try:
        with open(input_file, "r", encoding="utf-8") as file_obj:
            return list(csv.reader(file_obj))
    except UnicodeDecodeError:
        for encoding in ["latin-1", "windows-1252", "utf-8-sig", "iso-8859-1"]:
            try:
                with open(input_file, "r", encoding=encoding) as file_obj:
                    lines = list(csv.reader(file_obj))
                logger.info("Read %s using encoding %s", input_file, encoding)
                return lines
            except UnicodeDecodeError:
                continue

    logger.error("Unable to decode file: %s", input_file)
    raise ValueError(f"Unable to decode CSV input: {input_file}")


def parse_float(value: str) -> Optional[float]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def infer_birth_yyMMdd_from_metadata(metadata_records: List[Dict[str, object]]) -> str:
    for record in metadata_records:
        for col in ["PatientBirthdate", "data_nascimento"]:
            value = format_birth_yyMMdd(record.get(col, ""))
            if value:
                return value
    return ""


def infer_test_yyMMddHHMMSS_from_metadata(metadata_records: List[Dict[str, object]]) -> str:
    for record in metadata_records:
        for col in ["TestingDate", "data_realizada_do_teste"]:
            value = format_test_yyMMddHHMMSS(record.get(col, ""))
            if value:
                return value
    return ""


def infer_patientid_from_metadata(metadata_records: List[Dict[str, object]]) -> str:
    for record in metadata_records:
        value = str(record.get("PatientID", "") or "").strip()
        if value:
            return value
    return ""


def format_test_metadata(test_yyMMddHHMMSS: str) -> str:
    if len(test_yyMMddHHMMSS) < 12:
        return test_yyMMddHHMMSS
    return (
        f"{test_yyMMddHHMMSS[0:2]}/{test_yyMMddHHMMSS[2:4]}/{test_yyMMddHHMMSS[4:6]} "
        f"{test_yyMMddHHMMSS[6:8]}:{test_yyMMddHHMMSS[8:10]}:{test_yyMMddHHMMSS[10:12]}"
    )


def extract_patient_info_from_filename(filename: str) -> Dict[str, object]:
    filename = filename.strip()
    filename = re.sub(r"^c[oó]pia\s+de\s+", "", filename, flags=re.IGNORECASE)

    patterns = [
        r"^(\d+)[_\-\s]+([^_]+)_(\d{6})_(\d+)$",
        r"^(\d+)([^_]+)_(\d{6})_(\d+)$",
        r"^([^_]+)_(\d{6})_(\d+)$",
        r"^(\d+)[_\-\s]+([^_]+)_(\d+)$",
    ]

    for pattern in patterns:
        match = re.match(pattern, filename)
        if not match:
            continue
        groups = match.groups()

        id_prontuario = ""
        raw_name = ""
        raw_birthdate = ""
        raw_test_date = ""

        if len(groups) == 4:
            id_prontuario = groups[0].strip()
            raw_name = groups[1].strip()
            raw_birthdate = groups[2]
            raw_test_date = groups[3]
        elif len(groups) == 3:
            if re.match(r"^\d{6}$", groups[1]):
                id_prontuario = ""
                raw_name = groups[0].strip()
                raw_birthdate = groups[1]
                raw_test_date = groups[2]
            else:
                id_prontuario = groups[0].strip()
                raw_name = groups[1].strip()
                raw_test_date = groups[2]

        normalized_name = normalize_name_token(raw_name)
        birth_yyMMdd = format_birth_yyMMdd(raw_birthdate)
        test_yyMMddHHMMSS = format_test_yyMMddHHMMSS(raw_test_date) or raw_test_date
        patient_unique_id = build_patient_unique_id(
            id_prontuario,
            normalized_name,
            birth_yyMMdd,
            test_yyMMddHHMMSS,
        )

        birthdate = format_birth_metadata(birth_yyMMdd) if birth_yyMMdd else ""
        test_datetime = (
            f"{raw_test_date[0:2]}/{raw_test_date[2:4]}/{raw_test_date[4:6]} "
            f"{raw_test_date[6:8]}:{raw_test_date[8:10]}:{raw_test_date[10:12]}"
            if len(raw_test_date) >= 12
            else raw_test_date
        )

        return {
            "patient_unique_id": patient_unique_id,
            "id_prontuario": id_prontuario,
            "nome_paciente": normalized_name,
            "data_nascimento": birthdate,
            "data_realizada_do_teste": test_datetime,
            "birth_yyMMdd": birth_yyMMdd,
            "test_raw": test_yyMMddHHMMSS,
            "filename_identity_confident": True,
        }

    logger.warning("Could not extract structured patient info from filename: %s", filename)
    return {
        "patient_unique_id": build_patient_unique_id("", filename, "", ""),
        "id_prontuario": "",
        "nome_paciente": filename,
        "data_nascimento": "",
        "data_realizada_do_teste": "N/A",
        "birth_yyMMdd": "",
        "test_raw": "",
        "filename_identity_confident": False,
    }


def apply_metadata_identity_fallback(
    patient_info: Dict[str, object],
    metadata_records: List[Dict[str, object]],
) -> Dict[str, object]:
    """Merges metadata identity without collapsing valid filename-derived identities."""
    filename_identity_confident = bool(patient_info.get("filename_identity_confident", False))

    patientid_raw = infer_patientid_from_metadata(metadata_records)
    prontuario_meta, name_meta = extract_prontuario_and_name(patientid_raw)

    if prontuario_meta and (not filename_identity_confident or not patient_info.get("id_prontuario", "")):
        patient_info["id_prontuario"] = prontuario_meta

    normalized_name_meta = normalize_name_token(name_meta or "")
    if normalized_name_meta and (not filename_identity_confident or not patient_info.get("nome_paciente", "")):
        patient_info["nome_paciente"] = normalized_name_meta

    birth_from_filename = str(patient_info.get("birth_yyMMdd", "") or "").strip()
    test_from_filename = str(patient_info.get("test_raw", "") or "").strip()
    birth_from_metadata = infer_birth_yyMMdd_from_metadata(metadata_records)
    test_from_metadata = infer_test_yyMMddHHMMSS_from_metadata(metadata_records)

    if filename_identity_confident:
        birth_yyMMdd = birth_from_filename or birth_from_metadata
        test_yyMMddHHMMSS = test_from_filename or test_from_metadata
    else:
        birth_yyMMdd = birth_from_metadata or birth_from_filename
        test_yyMMddHHMMSS = test_from_metadata or test_from_filename

    patient_info["birth_yyMMdd"] = birth_yyMMdd
    patient_info["test_raw"] = test_yyMMddHHMMSS
    patient_info["data_nascimento"] = format_birth_metadata(birth_yyMMdd) if birth_yyMMdd else ""
    patient_info["data_realizada_do_teste"] = (
        format_test_metadata(test_yyMMddHHMMSS) if test_yyMMddHHMMSS else patient_info.get("data_realizada_do_teste", "N/A")
    )

    patient_info["patient_unique_id"] = build_patient_unique_id(
        patient_info.get("id_prontuario", ""),
        patient_info.get("nome_paciente", ""),
        patient_info.get("birth_yyMMdd", ""),
        patient_info.get("test_raw", ""),
    )
    return patient_info


def process_reteval_csv(input_file: str, output_dir: str) -> Optional[Tuple[Path, Path]]:
    lines = read_csv_lines_with_fallback(input_file)
    metadata_lines = lines[:12]

    field_names: List[str] = []
    field_descriptions: List[str] = []
    field_values: List[List[str]] = []

    for line in metadata_lines[:11]:
        field_name = line[0] if len(line) > 0 else ""
        field_desc = line[1] if len(line) > 1 else ""
        values = line[2:] if len(line) > 2 else []
        field_names.append(field_name)
        field_descriptions.append(field_desc)
        field_values.append(values)

    patient_values = field_values[0] if field_values else []
    test_metadata_list: List[Dict[str, object]] = []
    test_column_indices: List[int] = []

    for i, val in enumerate(patient_values):
        if not val.strip():
            continue
        real_col_idx = i + 2
        metadata: Dict[str, object] = {"test_id": len(test_metadata_list) + 1, "csv_col_idx": real_col_idx}

        for j, field_name in enumerate(field_names):
            if not field_name:
                continue
            field_value = field_values[j][i] if i < len(field_values[j]) else ""
            metadata[field_name] = str(field_value).strip()

            desc_value = str(field_descriptions[j]).strip()
            if desc_value:
                desc_key = f"{field_name}_description"
                metadata[desc_key] = desc_value

        test_metadata_list.append(metadata)
        test_column_indices.append(real_col_idx)

    logger.info("Identified %d tests in file %s", len(test_metadata_list), Path(input_file).name)
    if not test_metadata_list:
        logger.error("No test metadata found in %s", input_file)
        return None

    file_path = Path(input_file)
    base_name = file_path.stem
    patient_info = extract_patient_info_from_filename(base_name)
    patient_info = apply_metadata_identity_fallback(patient_info, test_metadata_list)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    metadata_path = output_path / f"{base_name}_metadata.parquet"
    waveforms_path = output_path / f"{base_name}_waveforms.parquet"

    metadata_rows: List[Dict[str, object]] = []
    for metadata in test_metadata_list:
        record: Dict[str, object] = {
            "source_file": base_name,
            "test_id": int(metadata.get("test_id", 0)),
            "patient_unique_id": patient_info["patient_unique_id"],
            "id_prontuario": patient_info["id_prontuario"] or "N/A",
            "nome_paciente": patient_info["nome_paciente"],
            "data_nascimento": patient_info["data_nascimento"] or "",
            "data_realizada_do_teste": patient_info["data_realizada_do_teste"],
        }
        for key, value in metadata.items():
            if key in {"test_id", "csv_col_idx"}:
                continue
            record[key] = value
        metadata_rows.append(record)

    if not metadata_rows:
        logger.error("No metadata rows built for %s", input_file)
        return None

    metadata_table = pa.Table.from_pylist(metadata_rows)
    pq.write_table(metadata_table, metadata_path, compression="snappy")
    metadata_count = len(metadata_rows)

    waveform_sections = []
    for i, line in enumerate(lines):
        if i < 12:
            continue
        field0 = line[0].lower() if len(line) > 0 else ""
        if "waveform" in field0 and line[0].strip():
            waveform_sections.append(
                {
                    "line_idx": i,
                    "name": line[0].strip(),
                    "description": line[1].strip() if len(line) > 1 else "",
                }
            )

    for idx, section in enumerate(waveform_sections):
        start_line = section["line_idx"] + 1
        end_line = waveform_sections[idx + 1]["line_idx"] if idx + 1 < len(waveform_sections) else len(lines)
        section["start_line"] = start_line
        section["end_line"] = end_line

    logger.info("Identified %d waveform sections in %s", len(waveform_sections), file_path.name)

    waveform_schema = pa.schema(
        [
            pa.field("source_file", pa.string()),
            pa.field("patient_unique_id", pa.string()),
            pa.field("test_id", pa.int32()),
            pa.field("waveform_type", pa.string()),
            pa.field("waveform_description", pa.string()),
            pa.field("time_ms", pa.float64()),
            pa.field("voltage_uV", pa.float64()),
            pa.field("pupil_mm", pa.float64()),
        ]
    )

    waveform_row_count = 0
    writer: Optional[pq.ParquetWriter] = None
    try:
        for section in waveform_sections:
            waveform_type = section["name"]
            waveform_desc = section["description"]
            waveform_data = lines[section["start_line"] : section["end_line"]]
            if not waveform_data:
                continue

            first_data_row = waveform_data[0]
            data_columns_with_test_id: List[Tuple[int, int, int]] = []

            for test_idx, col_idx in enumerate(test_column_indices):
                ms_col_idx = col_idx
                uv_col_idx = col_idx + 1
                has_data = False

                if ms_col_idx < len(first_data_row) and uv_col_idx < len(first_data_row):
                    ms_val = first_data_row[ms_col_idx].strip()
                    uv_val = first_data_row[uv_col_idx].strip()
                    if parse_float(ms_val) is not None or parse_float(uv_val) is not None:
                        has_data = True

                if has_data:
                    test_id = test_idx + 1
                    data_columns_with_test_id.append((test_id, ms_col_idx, uv_col_idx))

            for test_id, ms_col_idx, uv_col_idx in data_columns_with_test_id:
                source_files: List[str] = []
                patient_ids: List[str] = []
                test_ids: List[int] = []
                waveform_types: List[str] = []
                waveform_descs: List[str] = []
                times_ms: List[float] = []
                voltage_values: List[Optional[float]] = []
                pupil_values: List[Optional[float]] = []

                for row in waveform_data:
                    ms_raw = row[ms_col_idx].strip() if ms_col_idx < len(row) else ""
                    value_raw = row[uv_col_idx].strip() if uv_col_idx < len(row) else ""

                    time_ms = parse_float(ms_raw)
                    if time_ms is None:
                        continue

                    signal_value = parse_float(value_raw)

                    source_files.append(base_name)
                    patient_ids.append(str(patient_info["patient_unique_id"]))
                    test_ids.append(int(test_id))
                    waveform_types.append(str(waveform_type))
                    waveform_descs.append(str(waveform_desc))
                    times_ms.append(float(time_ms))

                    if waveform_type == "Pupil Waveform":
                        voltage_values.append(None)
                        pupil_values.append(signal_value)
                    else:
                        voltage_values.append(signal_value)
                        pupil_values.append(None)

                chunk_count = len(times_ms)
                if chunk_count == 0:
                    continue

                chunk_table = pa.Table.from_pydict(
                    {
                        "source_file": source_files,
                        "patient_unique_id": patient_ids,
                        "test_id": test_ids,
                        "waveform_type": waveform_types,
                        "waveform_description": waveform_descs,
                        "time_ms": times_ms,
                        "voltage_uV": voltage_values,
                        "pupil_mm": pupil_values,
                    },
                    schema=waveform_schema,
                )

                if writer is None:
                    writer = pq.ParquetWriter(waveforms_path, waveform_schema, compression="snappy")

                writer.write_table(chunk_table)
                waveform_row_count += chunk_count
    finally:
        if writer is not None:
            writer.close()

    if waveform_row_count == 0:
        logger.error("No valid waveform data found in %s", input_file)
        try:
            metadata_path.unlink(missing_ok=True)
            waveforms_path.unlink(missing_ok=True)
        except Exception:
            pass
        return None

    logger.info("Saved metadata rows: %s (%d tests)", metadata_path.name, metadata_count)
    logger.info("Saved waveform rows: %s (%d rows)", waveforms_path.name, waveform_row_count)
    return metadata_path, waveforms_path


def consolidate_files(
    output_dir: Path,
    workers: int | None,
    metadata_partitions: int | None,
    waveform_partitions: int | None,
    max_records_per_file: int | None,
    spark_heartbeat_interval: str,
    spark_network_timeout: str,
) -> Optional[Tuple[Path, Path]]:
    if not output_dir.exists():
        logger.error("Directory not found: %s", output_dir)
        return None

    consolidated_folder = output_dir / "consolidated"
    consolidated_folder.mkdir(parents=True, exist_ok=True)

    metadata_files = sorted(output_dir.glob("*_metadata.parquet"))
    waveforms_files = sorted(output_dir.glob("*_waveforms.parquet"))

    if not metadata_files or not waveforms_files:
        logger.error("No metadata or waveform files found for consolidation")
        return None

    spark = build_spark_session(
        workers,
        max_records_per_file=max_records_per_file,
        heartbeat_interval=spark_heartbeat_interval,
        network_timeout=spark_network_timeout,
    )
    spark.sparkContext.setLogLevel("WARN")

    try:
        from pyspark.sql import functions as F
        metadata_df = spark.read.parquet(*[str(path) for path in metadata_files])
        waveforms_df = spark.read.parquet(*[str(path) for path in waveforms_files])

        # Keep local test_id generated per source file in both datasets.
        # This avoids a global Window reindex, which collapses execution to a single partition.
        metadata_global = (
            metadata_df.withColumn("test_id", F.col("test_id").cast("int"))
            .filter(F.col("test_id").isNotNull())
        )

        waveforms_rekeyed = (
            waveforms_df.withColumn("test_id", F.col("test_id").cast("int"))
            .filter(F.col("test_id").isNotNull())
        )

        consolidated_metadata_path = consolidated_folder / "consolidated_metadata.parquet"
        consolidated_waveforms_path = consolidated_folder / "consolidated_waveforms.parquet"

        metadata_out = apply_target_partitions(metadata_global, metadata_partitions)
        waveforms_out = apply_target_partitions(waveforms_rekeyed, waveform_partitions)

        metadata_out.write.mode("overwrite").parquet(str(consolidated_metadata_path))
        waveforms_out.write.mode("overwrite").parquet(str(consolidated_waveforms_path))

        logger.info(
            "Consolidated %d files into %s and %s",
            len(metadata_files),
            consolidated_metadata_path.name,
            consolidated_waveforms_path.name,
        )
    finally:
        spark.stop()

    for temp_file in metadata_files + waveforms_files:
        try:
            temp_file.unlink(missing_ok=True)
        except Exception:
            logger.warning("Unable to delete temporary file %s", temp_file)

    return consolidated_metadata_path, consolidated_waveforms_path


def save_error_report(errors: List[Dict[str, str]], output_dir: Path) -> None:
    if not errors:
        return

    error_file = output_dir / "processing_errors.txt"
    with open(error_file, "w", encoding="utf-8") as file_obj:
        file_obj.write("=" * 80 + "\n")
        file_obj.write(f"ERROR REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        file_obj.write("=" * 80 + "\n\n")
        file_obj.write(f"Total errors: {len(errors)}\n\n")

        for idx, err in enumerate(errors, 1):
            file_obj.write(f"[ERROR #{idx}]\n")
            file_obj.write(f"File: {err['arquivo']}\n")
            file_obj.write(f"Path: {err['caminho_completo']}\n")
            file_obj.write(f"Type: {err['erro_tipo']}\n")
            file_obj.write(f"Message: {err['erro_mensagem']}\n")
            file_obj.write(f"Timestamp: {err['timestamp']}\n")
            file_obj.write(f"\nTraceback:\n{err['traceback']}\n")
            file_obj.write("-" * 80 + "\n\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Processes waveform CSVs and builds consolidated Parquet outputs."
    )
    parser.add_argument("--input", required=True, help="Input directory with raw waveform CSV files")
    parser.add_argument("--base", default=".", help="Base directory")
    parser.add_argument("--output", required=True, help="Output directory for generated Parquet files")
    parser.add_argument("--workers", type=int, default=None, help="Parallel workers")
    parser.add_argument(
        "--metadata-partitions",
        type=int,
        default=None,
        help="Target number of output files/partitions for consolidated metadata parquet",
    )
    parser.add_argument(
        "--waveform-partitions",
        type=int,
        default=None,
        help="Target number of output files/partitions for consolidated waveforms parquet",
    )
    parser.add_argument(
        "--max-records-per-file",
        type=int,
        default=None,
        help="Spark max records per output file (spark.sql.files.maxRecordsPerFile)",
    )
    parser.add_argument(
        "--spark-heartbeat-interval",
        default="60s",
        help="Spark executor heartbeat interval (e.g. 60s)",
    )
    parser.add_argument(
        "--spark-network-timeout",
        default="600s",
        help="Spark network timeout (e.g. 600s). Keep greater than heartbeat interval.",
    )
    return parser


def run(args: argparse.Namespace) -> None:
    base_dir = resolve_base_dir(args.base)
    input_path = resolve_input_path(base_dir, args.input, must_exist=True)
    output_dir = resolve_output_dir(base_dir, args.output, create=True)

    csv_files = [
        file_path
        for file_path in input_path.glob("*.csv")
        if not file_path.name.endswith("_metadata.csv") and not file_path.name.endswith("_waveforms.csv")
    ]
    if not csv_files:
        logger.error("No CSV files found in %s", input_path)
        raise SystemExit(1)

    if args.workers is not None:
        num_workers = min(args.workers, len(csv_files))
    else:
        num_workers = min(len(csv_files), multiprocessing.cpu_count())

    logger.info("Processing %d files with %d worker(s)", len(csv_files), num_workers)

    processed_files = []
    errors = []

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_map = {
            executor.submit(process_reteval_csv, str(csv_file), str(output_dir)): csv_file for csv_file in csv_files
        }

        for future in as_completed(future_map):
            csv_file = future_map[future]
            try:
                output_files = future.result()
                if output_files:
                    processed_files.append(output_files)
            except Exception as exc:
                errors.append(
                    {
                        "arquivo": csv_file.name,
                        "caminho_completo": str(csv_file),
                        "erro_tipo": type(exc).__name__,
                        "erro_mensagem": str(exc),
                        "timestamp": datetime.now().isoformat(),
                        "traceback": traceback.format_exc(),
                    }
                )
                logger.error("Error processing %s - %s: %s", csv_file.name, type(exc).__name__, exc)

    logger.info("=" * 60)
    logger.info("Finished: %d/%d file(s) processed", len(processed_files), len(csv_files))
    if errors:
        save_error_report(errors, output_dir)
        logger.warning("Errors found in %d file(s)", len(errors))
    logger.info("=" * 60)

    if processed_files:
        logger.info("Consolidating files into Parquet...")
        result = consolidate_files(
            output_dir,
            args.workers,
            args.metadata_partitions,
            args.waveform_partitions,
            args.max_records_per_file,
            args.spark_heartbeat_interval,
            args.spark_network_timeout,
        )
        if not result:
            logger.error("Consolidation failed")
            raise SystemExit(1)


def main() -> None:
    configure_logging(level=logging.INFO, fmt="%(levelname)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()