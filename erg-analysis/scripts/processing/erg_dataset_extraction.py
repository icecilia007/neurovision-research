"""ERG dataset extraction stage.

Reads consolidated hashed datasets, removes sensitive metadata,
extracts feature columns, and writes final CSV/Parquet artifacts.
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pa_csv
import pyarrow.dataset as pa_ds
import pyarrow.parquet as pa_parquet

from common.logging_utils import configure_logging
from common.path_utils import resolve_base_dir, resolve_input_path, resolve_output_dir


logger = logging.getLogger(__name__)


SENSITIVE_METADATA_COLUMNS = {
    "source_file",
    "id_prontuario",
    "nome_paciente",
    "data_nascimento",
    "PatientID",
}

WAVEFORM_COLUMNS_TO_DROP = {"source_file", "waveform_type", "waveform_description"}
WAVEFORM_TYPE_COLUMN = "waveform_type"

WAVEFORM_TYPE_MAP = {
    "Pupil Waveform": 1,
    "Raw Waveform": 2,
    "Reported Waveform": 3,
}

WAVEFORM_TYPE_ORDER = [
    "Pupil Waveform",
    "Raw Waveform",
    "Reported Waveform",
]

WAVEFORM_TYPE_DESCRIPTIONS = {
    "Pupil Waveform": "Width of pupil in mm",
    "Raw Waveform": "Unprocessed waveform, time = 0 is center of first flash",
    "Reported Waveform": "Processed waveform as-shown in the PDF report",
}

FEATURE_COLUMNS = [
    "patient_unique_id",
    "TestedEye",
    "TestStepType",
    "AWaveTime",
    "AWaveAmplitude",
    "BWaveTime",
    "BWaveAmplitude",
    "WaveformAmplitude",
]


def find_latest_patients_file(base_dir: Path) -> Path | None:
    direct_candidates = [base_dir / "patients.parquet", base_dir / "patients.csv"]
    for path in direct_candidates:
        if path.exists():
            return path

    candidates = list(base_dir.rglob("patients-*.parquet"))
    candidates.extend(base_dir.rglob("patients_*.parquet"))
    if not candidates:
        candidates = list(base_dir.rglob("patients-*.csv"))
        candidates.extend(base_dir.rglob("patients_*.csv"))
    if not candidates:
        return None
    return sorted(candidates)[-1]


def resolve_data_coleta() -> str:
    return datetime.now().strftime("%Y%m%d")


def load_dataframe(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path, dtype=str, low_memory=False)


def write_waveforms_parquet_chunked(
    input_path: Path,
    parquet_path: Path,
    drop_cols: set[str],
    block_size_mb: int,
    use_threads: bool,
) -> None:
    writer = None

    def _transform(table: pa.Table) -> pa.Table:
        if WAVEFORM_TYPE_COLUMN not in table.column_names:
            raise ValueError("Column waveform_type not found in waveform dataset")

        types = table.column(WAVEFORM_TYPE_COLUMN)
        idx = pc.index_in(types, value_set=pa.array(WAVEFORM_TYPE_ORDER))
        if pc.any(pc.equal(idx, -1)).as_py():
            raise ValueError("Unmapped waveform type found")

        ids = pc.add(idx, 1)
        table = table.append_column("waveform_type_id", ids.cast(pa.int32()))

        cols_to_drop = [col for col in drop_cols if col in table.column_names]
        if cols_to_drop:
            table = table.drop(cols_to_drop)
        return table

    try:
        if input_path.suffix.lower() == ".parquet" or input_path.is_dir():
            dataset = pa_ds.dataset(str(input_path), format="parquet")
            batch_size = max(50000, block_size_mb * 4096)
            for batch in dataset.to_batches(batch_size=batch_size, use_threads=use_threads):
                table = _transform(pa.Table.from_batches([batch]))
                if writer is None:
                    writer = pa_parquet.ParquetWriter(parquet_path, table.schema)
                writer.write_table(table)
        else:
            read_options = pa_csv.ReadOptions(
                block_size=block_size_mb * 1024 * 1024,
                use_threads=use_threads,
            )
            parse_options = pa_csv.ParseOptions(delimiter=",")
            convert_options = pa_csv.ConvertOptions(strings_can_be_null=True)
            reader = pa_csv.open_csv(
                input_path,
                read_options=read_options,
                parse_options=parse_options,
                convert_options=convert_options,
            )

            for batch in reader:
                table = _transform(pa.Table.from_batches([batch]))
                if writer is None:
                    writer = pa_parquet.ParquetWriter(parquet_path, table.schema)
                writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()


def extract_features(df_patients: pd.DataFrame) -> pd.DataFrame:
    available = [col for col in FEATURE_COLUMNS if col in df_patients.columns]
    missing = [col for col in FEATURE_COLUMNS if col not in df_patients.columns]
    if missing:
        logger.warning("Missing feature columns in patients dataset: %s", ", ".join(missing))
    if not available:
        raise ValueError("No feature columns found in patients-* file")
    return df_patients[available].copy()


def clean_metadata(df_metadata: pd.DataFrame) -> pd.DataFrame:
    to_drop = [col for col in SENSITIVE_METADATA_COLUMNS if col in df_metadata.columns]
    return df_metadata.drop(columns=to_drop, errors="ignore")


def resolve_input_paths(input_path: Path) -> Tuple[Path, Path, Path]:
    metadata_candidates = [
        input_path / "metadata.parquet",
        input_path / "consolidated_metadata.parquet",
        input_path / "consolidated" / "consolidated_metadata.parquet",
        input_path / "metadata.csv",
        input_path / "consolidated_metadata.csv",
        input_path / "consolidated" / "consolidated_metadata.csv",
    ]
    waveforms_candidates = [
        input_path / "waveforms.parquet",
        input_path / "consolidated_waveforms.parquet",
        input_path / "consolidated" / "consolidated_waveforms.parquet",
        input_path / "waveforms.csv",
        input_path / "consolidated_waveforms.csv",
        input_path / "consolidated" / "consolidated_waveforms.csv",
    ]

    metadata_named_recursive = sorted(input_path.rglob("metadata.parquet"))
    metadata_dated_recursive = sorted(input_path.rglob("metadata_*.parquet"))
    waveforms_named_recursive = sorted(input_path.rglob("waveforms.parquet"))
    waveforms_dated_recursive = sorted(input_path.rglob("waveforms_*.parquet"))
    metadata_recursive = sorted(input_path.rglob("consolidated_metadata.parquet"))
    waveforms_recursive = sorted(input_path.rglob("consolidated_waveforms.parquet"))
    if metadata_named_recursive:
        metadata_candidates.insert(0, metadata_named_recursive[-1])
    if metadata_dated_recursive:
        metadata_candidates.insert(0, metadata_dated_recursive[-1])
    if waveforms_named_recursive:
        waveforms_candidates.insert(0, waveforms_named_recursive[-1])
    if waveforms_dated_recursive:
        waveforms_candidates.insert(0, waveforms_dated_recursive[-1])
    if metadata_recursive:
        metadata_candidates.insert(0, metadata_recursive[-1])
    if waveforms_recursive:
        waveforms_candidates.insert(0, waveforms_recursive[-1])

    metadata_path = next((path for path in metadata_candidates if path.exists()), None)
    waveforms_path = next((path for path in waveforms_candidates if path.exists()), None)
    patients_path = find_latest_patients_file(input_path)

    if metadata_path is None:
        raise FileNotFoundError(
            f"File not found: consolidated_metadata.parquet under input directory {input_path}"
        )
    if waveforms_path is None:
        raise FileNotFoundError(
            f"File not found: consolidated_waveforms.parquet under input directory {input_path}"
        )
    if not patients_path:
        raise FileNotFoundError("No patients-* file found in input directory")

    return metadata_path, waveforms_path, patients_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extracts ERG datasets: clean metadata, preserve waveforms, and export A/B-wave features."
    )
    parser.add_argument("--input", required=True, help="Directory with consolidated hashed data")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--base", default=".", help="Base directory")
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of reading threads (default: auto)",
    )
    parser.add_argument(
        "--block-size-mb",
        type=int,
        default=64,
        help="CSV block size for waveforms in MB",
    )
    parser.add_argument(
        "--name-prefix",
        default="erg",
        help="Prefix used in generated output filenames",
    )
    parser.add_argument(
        "--compact-names",
        action="store_true",
        help="Use short output names: metadata/waveforms/features/waveform_types",
    )
    parser.add_argument(
        "--name-date-suffix",
        default="",
        help="Optional suffix for output names (example: 20260417_101500)",
    )
    parser.add_argument(
        "--skip-metadata-output",
        action="store_true",
        help="Skip writing metadata parquet when input is already anonymized",
    )
    return parser


def run(args: argparse.Namespace) -> None:
    base_dir = resolve_base_dir(args.base)
    input_dir = resolve_input_path(base_dir, args.input, must_exist=True)
    out_dir = resolve_output_dir(base_dir, args.output, create=True)

    metadata_path, waveforms_path, patients_path = resolve_input_paths(input_dir)

    logger.info("Reading metadata: %s", metadata_path.name)
    df_metadata = load_dataframe(metadata_path)
    logger.info("Reading patients: %s", patients_path.name)
    df_patients = load_dataframe(patients_path)

    df_metadata_clean = clean_metadata(df_metadata)
    df_features = extract_features(df_patients)

    date_suffix = (getattr(args, "name_date_suffix", "") or "").strip()

    def _name(base: str, ext: str) -> str:
        return f"{base}_{date_suffix}.{ext}" if date_suffix else f"{base}.{ext}"

    if getattr(args, "compact_names", False):
        metadata_out = out_dir / _name("metadata", "parquet")
        waveforms_out = out_dir / _name("waveforms", "parquet")
        waveform_dim_csv_out = out_dir / _name("waveform_types", "csv")
        waveform_dim_parquet_out = out_dir / _name("waveform_types", "parquet")
        features_csv_out = out_dir / _name("patients-features", "csv")
        features_parquet_out = out_dir / _name("patients-features", "parquet")
    else:
        data_coleta = resolve_data_coleta()
        logger.info("Collection date key: %s", data_coleta)

        prefix = (getattr(args, "name_prefix", "erg") or "erg").strip()
        metadata_out = out_dir / f"{prefix}_metadata_{data_coleta}.parquet"
        waveforms_out = out_dir / f"{prefix}_waveforms_{data_coleta}.parquet"
        waveform_dim_csv_out = out_dir / f"{prefix}_waveform_types_{data_coleta}.csv"
        waveform_dim_parquet_out = out_dir / f"{prefix}_waveform_types_{data_coleta}.parquet"
        features_csv_out = out_dir / f"{prefix}_features_{data_coleta}.csv"
        features_parquet_out = out_dir / f"{prefix}_features_{data_coleta}.parquet"

    if not getattr(args, "skip_metadata_output", False):
        df_metadata_clean.to_parquet(metadata_out, index=False)

    logger.info("Processing waveforms in chunks")
    use_threads = args.workers is None or args.workers > 1

    waveform_dim_rows = [
        {
            "waveform_type_id": waveform_type_id,
            "waveform_type": waveform_type,
            "waveform_description": WAVEFORM_TYPE_DESCRIPTIONS.get(waveform_type, ""),
        }
        for waveform_type, waveform_type_id in WAVEFORM_TYPE_MAP.items()
    ]
    waveform_dim_df = pd.DataFrame(waveform_dim_rows).sort_values(by="waveform_type_id")
    waveform_dim_df.to_csv(waveform_dim_csv_out, index=False, encoding="utf-8-sig")
    waveform_dim_df.to_parquet(waveform_dim_parquet_out, index=False)

    write_waveforms_parquet_chunked(
        waveforms_path,
        waveforms_out,
        WAVEFORM_COLUMNS_TO_DROP,
        max(1, args.block_size_mb),
        use_threads,
    )

    df_features.to_csv(features_csv_out, index=False, encoding="utf-8-sig")
    df_features.to_parquet(features_parquet_out, index=False)

    logger.info("Generated files:")
    if not getattr(args, "skip_metadata_output", False):
        logger.info("- %s", metadata_out)
    logger.info("- %s", waveforms_out)
    logger.info("- %s", waveform_dim_csv_out)
    logger.info("- %s", waveform_dim_parquet_out)
    logger.info("- %s", features_csv_out)
    logger.info("- %s", features_parquet_out)


def main() -> None:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
