"""
Extrai descritores espectrais de waveforms ERG por sinal completo.

Unidade de processamento:
    (patient_unique_id, test_id, waveform_type)

Descritores extraidos:
- FFT: energia total, media/esvio do espectro e frequencia dominante
- Welch: frequencia de pico, energia total, centroid espectral
- Wavelet (DWT): energia por nivel, energia relativa por nivel, entropia wavelet

Exemplo de uso:
    python scripts/extract_erg_spectral_features.py \
        --base . \
        --input outputs/hashed/erg \
        --output outputs/hashed/erg
    python scripts/extract_erg_spectral_features.py --base . --input outputs/hashed/erg --output outputs/hashed/erg
"""

import argparse
import os
import hashlib
import logging
import math
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pa_parquet
import pywt
from scipy.signal import welch


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


GROUP_COLUMNS = ["patient_unique_id", "test_id", "TestType", "waveform_type", "TestedEye", "TestStepType"]
BUCKET_COLUMNS = [
    "patient_unique_id",
    "test_id",
    "TestType",
    "waveform_type",
    "TestedEye",
    "TestStepType",
    "signal_type",
    "time_ms",
    "signal_value",
]


def resolve_latest_file(input_dir: Path, pattern: str) -> Path:
    files = sorted(input_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo encontrado para o padrao: {pattern}")
    return files[-1]


def resolve_preview_csv(input_dir: Path, base_name: str) -> Optional[Path]:
    preferred = input_dir / f"preview2_{base_name}.csv"
    if preferred.exists():
        return preferred
    candidates = sorted(input_dir.glob(f"preview_{base_name}_*.csv"))
    if candidates:
        return candidates[-1]
    return None


def resolve_waveform_inputs(
    input_dir: Path,
    metadata_dir: Optional[Path] = None,
) -> Tuple[Path, Path, Optional[Path], Optional[Path], bool]:
    waveforms_preview = resolve_preview_csv(input_dir, "erg_waveforms")
    metadata_preview = resolve_preview_csv(input_dir, "erg_metadata")

    if waveforms_preview and metadata_preview:
        waveform_types_parquet = sorted(input_dir.glob("erg_waveform_types_*.parquet"))
        waveform_types_csv = sorted(input_dir.glob("preview2_erg_waveform_types.csv"))
        if not waveform_types_csv:
            waveform_types_csv = sorted(input_dir.glob("preview_erg_waveform_types_*.csv"))

        types_parquet_path = waveform_types_parquet[-1] if waveform_types_parquet else None
        types_csv_path = waveform_types_csv[-1] if waveform_types_csv else None
        return waveforms_preview, metadata_preview, types_parquet_path, types_csv_path, True

    # waveforms: padrão antigo (erg_waveforms_*) depois padrão novo (waveforms_*)
    waveforms_candidates = sorted(input_dir.glob("erg_waveforms_*.parquet"))
    if not waveforms_candidates:
        waveforms_candidates = sorted(input_dir.glob("waveforms_*.parquet"))
    if not waveforms_candidates:
        raise FileNotFoundError(f"Nenhum arquivo de waveforms encontrado em {input_dir}")
    waveforms_path = waveforms_candidates[-1]

    # metadata: padrão antigo (erg_metadata_*) depois padrão novo em metadata_dir ou input_dir
    search_dirs = [input_dir] if metadata_dir is None else [metadata_dir, input_dir]
    metadata_path: Optional[Path] = None
    for d in search_dirs:
        candidates = sorted(d.glob("erg_metadata_*.parquet"))
        if not candidates:
            candidates = sorted(d.glob("metadata_*.parquet"))
        if candidates:
            metadata_path = candidates[-1]
            break
    if metadata_path is None:
        searched = ", ".join(str(d) for d in search_dirs)
        raise FileNotFoundError(f"Nenhum arquivo de metadata encontrado em: {searched}")

    # waveform_types: padrão antigo depois padrão novo
    waveform_types_parquet = sorted(input_dir.glob("erg_waveform_types_*.parquet"))
    if not waveform_types_parquet:
        waveform_types_parquet = sorted(input_dir.glob("waveform_types_*.parquet"))
    waveform_types_csv = sorted(input_dir.glob("erg_waveform_types_*.csv"))
    if not waveform_types_csv:
        waveform_types_csv = sorted(input_dir.glob("waveform_types_*.csv"))

    types_parquet_path = waveform_types_parquet[-1] if waveform_types_parquet else None
    types_csv_path = waveform_types_csv[-1] if waveform_types_csv else None
    return waveforms_path, metadata_path, types_parquet_path, types_csv_path, False


def load_waveform_type_map(types_parquet_path: Optional[Path], types_csv_path: Optional[Path]) -> Dict[int, str]:
    if types_parquet_path and types_parquet_path.exists():
        df = pd.read_parquet(types_parquet_path)
    elif types_csv_path and types_csv_path.exists():
        df = pd.read_csv(types_csv_path, low_memory=False)
    else:
        return {}

    if "waveform_type_id" not in df.columns or "waveform_type" not in df.columns:
        return {}

    df["waveform_type_id"] = pd.to_numeric(df["waveform_type_id"], errors="coerce")
    df = df.dropna(subset=["waveform_type_id", "waveform_type"])
    return {int(row.waveform_type_id): str(row.waveform_type) for row in df.itertuples(index=False)}


def setup_file_logging(base_dir: Path, timestamp: str) -> Path:
    log_dir = base_dir / "tmp" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"extract_erg_spectral_features_{timestamp}.txt"

    root_logger = logging.getLogger()
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    root_logger.addHandler(file_handler)
    return log_path


def validate_metadata_uniqueness(
    metadata_dims_df: pd.DataFrame,
    strict: bool,
) -> None:
    key_cols = ["patient_unique_id", "test_id"]
    dim_cols = ["TestType", "TestedEye", "TestStepType"]

    grouped = metadata_dims_df.groupby(key_cols, dropna=False)[dim_cols].nunique(dropna=True)
    ambiguous_mask = (grouped > 1).any(axis=1)
    ambiguous = grouped[ambiguous_mask]

    if ambiguous.empty:
        logger.info("Validacao metadata: sem ambiguidade para chave (patient_unique_id, test_id)")
        return

    logger.warning(
        "Validacao metadata: %d chaves com dimensoes ambiguas em (patient_unique_id, test_id)",
        len(ambiguous),
    )
    logger.warning("Amostra de ambiguidades:\n%s", ambiguous.head(20).to_string())

    if strict:
        raise ValueError(
            "Ambiguidade em metadata para chave (patient_unique_id, test_id). "
            "Use chaves mais especificas ou rode sem --strict-metadata-uniqueness para seguir com keep='first'."
        )


def read_metadata_dimensions_from_csv(metadata_path: Path, batch_size: int) -> pd.DataFrame:
    if is_lfs_pointer_csv(metadata_path):
        raise RuntimeError(
            f"Arquivo CSV esta como ponteiro Git LFS: {metadata_path}. "
            "Execute 'git lfs pull' para baixar o conteudo real."
        )

    needed = ["patient_unique_id", "test_id", "TestType", "TestedEye", "TestStepType"]
    chunks: List[pd.DataFrame] = []

    for chunk in pd.read_csv(metadata_path, usecols=needed, chunksize=batch_size, low_memory=False):
        chunk = chunk.dropna(subset=["patient_unique_id", "test_id"])
        chunks.append(chunk)

    if not chunks:
        return pd.DataFrame(columns=needed)

    df = pd.concat(chunks, ignore_index=True)
    df["patient_unique_id"] = df["patient_unique_id"].astype("string")
    df["test_id"] = df["test_id"].astype("string")
    df = df.drop_duplicates(subset=["patient_unique_id", "test_id"], keep="first")
    return df


def load_metadata_dimensions(metadata_path: Path, batch_size: int) -> pd.DataFrame:
    if metadata_path.suffix.lower() == ".csv":
        return read_metadata_dimensions_from_csv(metadata_path, batch_size)

    pf = pa_parquet.ParquetFile(metadata_path)
    needed = [c for c in ["patient_unique_id", "test_id", "TestType", "TestedEye", "TestStepType"] if c in pf.schema.names]
    missing = [c for c in ["patient_unique_id", "test_id", "TestType", "TestedEye", "TestStepType"] if c not in needed]
    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes no metadata: {', '.join(missing)}")

    chunks: List[pd.DataFrame] = []
    for batch in pf.iter_batches(columns=needed, batch_size=batch_size):
        chunk = pa.Table.from_batches([batch]).to_pandas()
        chunk = chunk.dropna(subset=["patient_unique_id", "test_id"])
        chunks.append(chunk)

    if not chunks:
        return pd.DataFrame(columns=["patient_unique_id", "test_id", "TestType", "TestedEye", "TestStepType"])

    df = pd.concat(chunks, ignore_index=True)
    df["patient_unique_id"] = df["patient_unique_id"].astype("string")
    df["test_id"] = df["test_id"].astype("string")
    df = df.drop_duplicates(subset=["patient_unique_id", "test_id"], keep="first")
    return df


def is_lfs_pointer_csv(path: Path) -> bool:
    if path.suffix.lower() != ".csv" or not path.exists():
        return False
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            first_line = fh.readline().strip()
        return first_line == "version https://git-lfs.github.com/spec/v1"
    except OSError:
        return False


def resolve_signal(row: pd.Series) -> Tuple[float, Optional[str]]:
    wf_id = pd.to_numeric(row.get("waveform_type_id"), errors="coerce")

    if wf_id == 1:
        return row.get("pupil_mm"), "pupil"
    if wf_id in (2, 3):
        return row.get("voltage_uV"), "voltage"
    return None, None


def estimate_sampling_rate_hz(time_ms: np.ndarray) -> float:
    if time_ms.size < 2:
        return math.nan
    diffs = np.diff(time_ms)
    diffs = diffs[np.isfinite(diffs)]
    diffs = diffs[diffs > 0]
    if diffs.size == 0:
        return math.nan
    dt_ms = np.median(diffs)
    if dt_ms <= 0:
        return math.nan
    return float(1000.0 / dt_ms)


def preprocess_signal(signal_arr: np.ndarray) -> Optional[np.ndarray]:
    signal_series = pd.Series(signal_arr, dtype="float64")
    if signal_series.isna().all():
        return None
    signal_series = signal_series.interpolate(limit_direction="both")
    return signal_series.to_numpy(dtype=np.float64)


def extract_fft_features(signal_arr: np.ndarray, fs_hz: float) -> Dict[str, float]:
    centered = signal_arr - np.mean(signal_arr)
    spectrum = np.fft.rfft(centered)
    magnitudes = np.abs(spectrum)

    energy_total = float(np.sum(magnitudes ** 2))
    mean_mag = float(np.mean(magnitudes))
    std_mag = float(np.std(magnitudes))

    if np.isfinite(fs_hz):
        freqs = np.fft.rfftfreq(centered.size, d=1.0 / fs_hz)
        dominant_freq = float(freqs[int(np.argmax(magnitudes))])
    else:
        dominant_freq = math.nan

    return {
        "fft_energy_total": energy_total,
        "fft_magnitude_mean": mean_mag,
        "fft_magnitude_std": std_mag,
        "fft_dominant_freq_hz": dominant_freq,
    }


def extract_welch_features(signal_arr: np.ndarray, fs_hz: float) -> Dict[str, float]:
    if not np.isfinite(fs_hz) or signal_arr.size < 8:
        return {
            "welch_peak_freq_hz": math.nan,
            "welch_total_energy": math.nan,
            "welch_spectral_centroid_hz": math.nan,
        }

    nperseg = min(256, signal_arr.size)
    freqs, psd = welch(signal_arr, fs=fs_hz, nperseg=nperseg, detrend="constant")
    if psd.size == 0:
        return {
            "welch_peak_freq_hz": math.nan,
            "welch_total_energy": math.nan,
            "welch_spectral_centroid_hz": math.nan,
        }

    peak_freq = float(freqs[int(np.argmax(psd))])
    total_energy = float(np.trapezoid(psd, freqs))
    psd_sum = float(np.sum(psd))
    centroid = float(np.sum(freqs * psd) / psd_sum) if psd_sum > 0 else math.nan

    return {
        "welch_peak_freq_hz": peak_freq,
        "welch_total_energy": total_energy,
        "welch_spectral_centroid_hz": centroid,
    }


def extract_wavelet_features(
    signal_arr: np.ndarray,
    wavelet_name: str,
    max_levels: int,
) -> Dict[str, float]:
    wavelet = pywt.Wavelet(wavelet_name)
    max_possible_level = pywt.dwt_max_level(signal_arr.size, wavelet.dec_len)
    level = max(1, min(max_levels, max_possible_level))

    coeffs = pywt.wavedec(signal_arr, wavelet_name, level=level)
    energies = [float(np.sum(np.square(c))) for c in coeffs]
    total_energy = float(np.sum(energies))

    features: Dict[str, float] = {
        "wavelet_total_energy": total_energy,
    }

    for idx in range(1, max_levels + 1):
        features[f"wavelet_energy_l{idx}"] = math.nan
        features[f"wavelet_rel_energy_l{idx}"] = math.nan

    for idx, energy in enumerate(energies, start=1):
        if idx > max_levels:
            break
        rel_energy = (energy / total_energy) if total_energy > 0 else math.nan
        features[f"wavelet_energy_l{idx}"] = float(energy)
        features[f"wavelet_rel_energy_l{idx}"] = float(rel_energy) if np.isfinite(rel_energy) else math.nan

    rel_vals = np.asarray(
        [features[f"wavelet_rel_energy_l{idx}"] for idx in range(1, max_levels + 1)],
        dtype=np.float64,
    )
    rel_vals = rel_vals[np.isfinite(rel_vals)]
    rel_vals = rel_vals[rel_vals > 0]
    entropy = float(-np.sum(rel_vals * np.log2(rel_vals))) if rel_vals.size else math.nan
    features["wavelet_entropy"] = entropy

    return features


def hash_bucket(
    patient_id: str,
    test_id: str,
    test_type: str,
    waveform_type: str,
    tested_eye: str,
    test_step_type: str,
    num_buckets: int,
) -> int:
    key = f"{patient_id}|{test_id}|{test_type}|{waveform_type}|{tested_eye}|{test_step_type}".encode("utf-8")
    digest = hashlib.blake2b(key, digest_size=4).digest()
    return int.from_bytes(digest, "little") % num_buckets


def prepare_waveform_chunk(
    df: pd.DataFrame,
    metadata_dims_df: pd.DataFrame,
    waveform_type_map: Dict[int, str],
) -> pd.DataFrame:
    required_any = {"voltage_uV", "pupil_mm"}
    missing_required = [c for c in ["patient_unique_id", "test_id", "time_ms"] if c not in df.columns]
    if missing_required:
        raise ValueError(f"Colunas obrigatorias ausentes no dataset: {', '.join(missing_required)}")
    if not required_any.intersection(df.columns):
        raise ValueError("Dataset nao contem colunas de sinal esperadas: voltage_uV/pupil_mm")

    if "waveform_type" in df.columns:
        waveform_type_series = df["waveform_type"]
    elif "waveform_type_id" in df.columns:
        wf_ids = pd.to_numeric(df["waveform_type_id"], errors="coerce")
        waveform_type_series = wf_ids.map(waveform_type_map)
        waveform_type_series = waveform_type_series.fillna("unknown")
    else:
        waveform_type_series = pd.Series(["unknown"] * len(df), index=df.index)

    # Evita apply linha-a-linha: para grandes volumes, mascara vetorizada reduz
    # bastante o custo de CPU na preparacao do chunk.
    if "waveform_type_id" in df.columns:
        wf_ids = pd.to_numeric(df["waveform_type_id"], errors="coerce")
    else:
        wf_ids = pd.Series(np.nan, index=df.index)

    voltage_series = pd.to_numeric(df["voltage_uV"], errors="coerce") if "voltage_uV" in df.columns else pd.Series(np.nan, index=df.index)
    is_voltage = wf_ids.isin([2, 3])

    signal_series = voltage_series.where(is_voltage, np.nan)
    signal_type_series = pd.Series(np.where(is_voltage, "voltage", pd.NA), index=df.index, dtype="string")

    out = pd.DataFrame(
        {
            "patient_unique_id": df["patient_unique_id"].astype("string"),
            "test_id": df["test_id"].astype("string"),
            "waveform_type": waveform_type_series,
            "time_ms": pd.to_numeric(df["time_ms"], errors="coerce"),
            "signal_value": signal_series,
            "signal_type": signal_type_series,
        }
    )

    out = out[out["signal_type"] == "voltage"]

    out = out.merge(
        metadata_dims_df,
        on=["patient_unique_id", "test_id"],
        how="left",
    )
    out["TestType"] = out["TestType"].fillna("unknown_test")
    out["TestedEye"] = out["TestedEye"].fillna("unknown_eye")
    out["TestStepType"] = out["TestStepType"].fillna("unknown_step")

    out = out.dropna(subset=["patient_unique_id", "test_id", "waveform_type", "time_ms"])
    return out


def write_bucket_rows(df_chunk: pd.DataFrame, bucket_paths: List[Path], header_written: set[int]) -> None:
    if df_chunk.empty:
        return

    key_series = (
        df_chunk["patient_unique_id"].astype("string")
        + "|"
        + df_chunk["test_id"].astype("string")
        + "|"
        + df_chunk["TestType"].astype("string")
        + "|"
        + df_chunk["waveform_type"].astype("string")
        + "|"
        + df_chunk["TestedEye"].astype("string")
        + "|"
        + df_chunk["TestStepType"].astype("string")
    )
    unique_keys = pd.unique(key_series)
    key_to_bucket = {
        key: hash_bucket(
            patient_id=key.split("|", 5)[0],
            test_id=key.split("|", 5)[1],
            test_type=key.split("|", 5)[2],
            waveform_type=key.split("|", 5)[3],
            tested_eye=key.split("|", 5)[4],
            test_step_type=key.split("|", 5)[5],
            num_buckets=len(bucket_paths),
        )
        for key in unique_keys
    }

    df_chunk = df_chunk.assign(_bucket=key_series.map(key_to_bucket).astype(np.int32))
    for bucket in sorted(df_chunk["_bucket"].unique()):
        bucket_rows = df_chunk[df_chunk["_bucket"] == bucket][BUCKET_COLUMNS]
        out_path = bucket_paths[int(bucket)]
        write_header = int(bucket) not in header_written
        bucket_rows.to_csv(out_path, mode="a", index=False, header=write_header)
        header_written.add(int(bucket))


def log_waveform_sizes(df: pd.DataFrame) -> None:
    if df.empty:
        logger.info("Bucket vazio para distribuicao de pontos por waveform")
        return

    sizes = df.groupby(GROUP_COLUMNS).size().reset_index(name="num_points")
    logger.info("Distribuicao de pontos por waveform:")
    logger.info("\n%s", sizes["num_points"].describe())

    small = sizes[sizes["num_points"] < 50]
    if not small.empty:
        logger.warning("Waveforms com poucos pontos detectados: %d", len(small))
        logger.warning("\n%s", small.head(20).to_string(index=False))


def validate_time_order(grouped: pd.core.groupby.generic.DataFrameGroupBy) -> None:
    for key, group_df in grouped:
        ordered = pd.to_numeric(group_df["time_ms"], errors="coerce").is_monotonic_increasing
        if not ordered:
            logger.warning("Waveform desordenado: %s", key)


def detect_time_gaps(grouped: pd.core.groupby.generic.DataFrameGroupBy) -> None:
    for key, group_df in grouped:
        t = pd.to_numeric(group_df["time_ms"], errors="coerce").to_numpy(dtype=np.float64)
        if t.size < 3:
            continue
        t = np.sort(t)
        diffs = np.diff(t)
        finite = diffs[np.isfinite(diffs)]
        finite = finite[finite > 0]
        if finite.size == 0:
            continue
        median = np.median(finite)
        if median <= 0:
            continue
        if np.any(finite > 3 * median):
            logger.warning("Gap temporal detectado: %s", key)


def bucketize_waveforms(
    waveforms_path: Path,
    bucket_paths: List[Path],
    metadata_dims_df: pd.DataFrame,
    waveform_type_map: Dict[int, str],
    batch_size: int,
) -> None:
    if waveforms_path.suffix.lower() == ".csv":
        bucketize_waveforms_csv(
            waveforms_path=waveforms_path,
            bucket_paths=bucket_paths,
            metadata_dims_df=metadata_dims_df,
            waveform_type_map=waveform_type_map,
            batch_size=batch_size,
        )
        return

    pf = pa_parquet.ParquetFile(waveforms_path)
    header_written: set[int] = set()

    columns = [
        c
        for c in ["patient_unique_id", "test_id", "waveform_type", "waveform_type_id", "time_ms", "voltage_uV", "pupil_mm"]
        if c in pf.schema.names
    ]
    logger.info("Lendo waveforms em batches com colunas: %s", columns)

    processed_batches = 0
    total_rows = 0
    total_prepared = 0
    for batch in pf.iter_batches(columns=columns, batch_size=batch_size):
        df = pa.Table.from_batches([batch]).to_pandas()
        prepared = prepare_waveform_chunk(df, metadata_dims_df, waveform_type_map)
        write_bucket_rows(prepared, bucket_paths, header_written)

        total_rows += len(df)
        total_prepared += len(prepared)

        processed_batches += 1
        if processed_batches % 20 == 0:
            logger.info("Batches processados: %d", processed_batches)

    logger.info("Bucketizacao concluida. Buckets escritos: %d", len(header_written))
    logger.info("Total linhas lidas: %d", total_rows)
    logger.info("Total linhas apos preparo: %d", total_prepared)
    retention = (100.0 * total_prepared / total_rows) if total_rows else 0.0
    logger.info("Retencao: %.2f%%", retention)


def bucketize_waveforms_csv(
    waveforms_path: Path,
    bucket_paths: List[Path],
    metadata_dims_df: pd.DataFrame,
    waveform_type_map: Dict[int, str],
    batch_size: int,
) -> None:
    if is_lfs_pointer_csv(waveforms_path):
        raise RuntimeError(
            f"Arquivo CSV de waveforms esta como ponteiro Git LFS: {waveforms_path}. "
            "Execute 'git lfs pull' para baixar o conteudo real."
        )

    header_written: set[int] = set()
    processed_batches = 0
    total_rows = 0
    total_prepared = 0

    for chunk in pd.read_csv(waveforms_path, chunksize=batch_size, low_memory=False):
        prepared = prepare_waveform_chunk(chunk, metadata_dims_df, waveform_type_map)
        write_bucket_rows(prepared, bucket_paths, header_written)

        total_rows += len(chunk)
        total_prepared += len(prepared)

        processed_batches += 1
        if processed_batches % 20 == 0:
            logger.info("Batches CSV processados: %d", processed_batches)

    logger.info("Bucketizacao CSV concluida. Buckets escritos: %d", len(header_written))
    logger.info("Total linhas lidas: %d", total_rows)
    logger.info("Total linhas apos preparo: %d", total_prepared)
    retention = (100.0 * total_prepared / total_rows) if total_rows else 0.0
    logger.info("Retencao: %.2f%%", retention)


def build_group_feature_row(
    grouped_df: pd.DataFrame,
    wavelet_name: str,
    max_wavelet_levels: int,
    min_samples: int,
) -> Optional[Dict[str, float]]:
    grouped_df = grouped_df.sort_values("time_ms", kind="stable")
    time_ms = np.asarray(grouped_df["time_ms"].to_numpy(), dtype=np.float64)
    signal_arr = np.asarray(grouped_df["signal_value"].to_numpy(), dtype=np.float64)

    if not np.all(np.isfinite(time_ms)):
        logger.warning(
            "Waveform com time_ms invalido (descartado): %s",
            tuple(grouped_df[c].iloc[0] for c in GROUP_COLUMNS),
        )
        return None

    signal_arr = preprocess_signal(signal_arr)
    if signal_arr is None:
        logger.warning(
            "Waveform com signal_value totalmente ausente (descartado): %s",
            tuple(grouped_df[c].iloc[0] for c in GROUP_COLUMNS),
        )
        return None

    n = signal_arr.size
    if n < min_samples:
        return None

    fs_hz = estimate_sampling_rate_hz(time_ms)

    row: Dict[str, float] = {
        "patient_unique_id": str(grouped_df["patient_unique_id"].iloc[0]),
        "test_id": str(grouped_df["test_id"].iloc[0]),
        "TestType": str(grouped_df["TestType"].iloc[0]),
        "waveform_type": str(grouped_df["waveform_type"].iloc[0]),
        "TestedEye": str(grouped_df["TestedEye"].iloc[0]),
        "TestStepType": str(grouped_df["TestStepType"].iloc[0]),
        "signal_type": str(grouped_df["signal_type"].iloc[0]),
        "signal_length": int(n),
        "sampling_rate_hz": float(fs_hz) if np.isfinite(fs_hz) else math.nan,
    }
    row.update(extract_fft_features(signal_arr, fs_hz))
    row.update(extract_welch_features(signal_arr, fs_hz))
    row.update(extract_wavelet_features(signal_arr, wavelet_name, max_wavelet_levels))
    return row


def process_bucket_file(
    bucket_path: Path,
    wavelet_name: str,
    max_wavelet_levels: int,
    min_samples: int,
) -> List[Dict[str, float]]:
    if not bucket_path.exists() or bucket_path.stat().st_size == 0:
        return []

    df = pd.read_csv(bucket_path, low_memory=False)
    if df.empty:
        return []

    log_waveform_sizes(df)
    validate_time_order(df.groupby(GROUP_COLUMNS, sort=False))
    detect_time_gaps(df.groupby(GROUP_COLUMNS, sort=False))

    rows: List[Dict[str, float]] = []
    grouped = df.groupby(GROUP_COLUMNS, sort=False)
    for _, group_df in grouped:
        row = build_group_feature_row(group_df, wavelet_name, max_wavelet_levels, min_samples)
        if row is not None:
            rows.append(row)

    return rows


def process_all_buckets(
    bucket_paths: List[Path],
    wavelet_name: str,
    max_wavelet_levels: int,
    min_samples: int,
    workers: int,
) -> List[Dict[str, float]]:
    all_rows: List[Dict[str, float]] = []
    total = len(bucket_paths)

    if workers <= 1:
        for idx, bucket_path in enumerate(bucket_paths, start=1):
            rows = process_bucket_file(
                bucket_path=bucket_path,
                wavelet_name=wavelet_name,
                max_wavelet_levels=max_wavelet_levels,
                min_samples=min_samples,
            )
            if rows:
                all_rows.extend(rows)
            if idx % 10 == 0 or idx == total:
                logger.info("Buckets processados: %d/%d", idx, total)
        return all_rows

    logger.info("Processando buckets em paralelo com workers=%d", workers)
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(
                process_bucket_file,
                bucket_path,
                wavelet_name,
                max_wavelet_levels,
                min_samples,
            ): bucket_path
            for bucket_path in bucket_paths
        }

        for future in as_completed(future_map):
            bucket_path = future_map[future]
            rows = future.result()
            if rows:
                all_rows.extend(rows)
            done += 1
            if done % 10 == 0 or done == total:
                logger.info("Buckets processados: %d/%d | ultimo=%s", done, total, bucket_path.name)

    return all_rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrai descritores espectrais ERG (FFT, Welch, Wavelet) por waveform completo."
    )
    parser.add_argument("--input", required=True, help="Diretorio com arquivos erg_*.parquet")
    parser.add_argument("--output", required=True, help="Diretorio de saida")
    parser.add_argument("--base", default=".", help="Diretorio base (padrao: diretorio atual)")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50000,
        help="Quantidade de linhas por batch/chunk (padrao: 50000; recomendado para HDD/RAM moderada)",
    )
    parser.add_argument(
        "--num-buckets",
        type=int,
        default=64,
        help="Numero de buckets temporarios para processamento externo (padrao: 64)",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=32,
        help="Quantidade minima de pontos do sinal para extracao (padrao: 32)",
    )
    parser.add_argument(
        "--wavelet",
        default="db4",
        help="Wavelet da DWT (padrao: db4)",
    )
    parser.add_argument(
        "--max-wavelet-levels",
        type=int,
        default=5,
        help="Numero maximo de niveis wavelet para exportar (padrao: 5)",
    )
    parser.add_argument(
        "--output-file",
        default="erg_spectral_features.csv",
        help="Nome do arquivo de saida (padrao: erg_spectral_features.csv)",
    )
    parser.add_argument(
        "--output-format",
        choices=["csv", "parquet", "both"],
        default="both",
        help="Formato de saida: csv, parquet ou both (padrao: both)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, (os.cpu_count() or 1) - 1),
        help="Quantidade de processos para extracao por bucket (padrao: cpu_count-1)",
    )
    parser.add_argument(
        "--strict-metadata-uniqueness",
        action="store_true",
        help="Falha a execucao se houver ambiguidade de TestType/TestedEye/TestStepType para a mesma chave (patient_unique_id, test_id).",
    )
    parser.add_argument(
        "--metadata-input",
        default=None,
        help="Diretorio alternativo para buscar metadata_*.parquet (ex: output/data/anonymized/staging)",
    )
    args = parser.parse_args()

    base_dir = Path(args.base).resolve()

    input_dir = Path(args.input)
    if not input_dir.is_absolute():
        input_dir = (base_dir / input_dir).resolve()

    metadata_dir: Optional[Path] = None
    if getattr(args, "metadata_input", None):
        metadata_dir = Path(args.metadata_input)
        if not metadata_dir.is_absolute():
            metadata_dir = (base_dir / metadata_dir).resolve()

    out_dir = Path(args.output)
    if not out_dir.is_absolute():
        out_dir = (base_dir / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    num_buckets = max(8, int(args.num_buckets))
    batch_size = max(10_000, int(args.batch_size))
    min_samples = max(8, int(args.min_samples))
    max_wavelet_levels = max(1, int(args.max_wavelet_levels))
    workers = max(1, int(args.workers))

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = setup_file_logging(base_dir, timestamp)
    logger.info("Log detalhado salvo em: %s", log_path)

    waveforms_path, metadata_path, types_parquet_path, types_csv_path, using_preview = resolve_waveform_inputs(input_dir, metadata_dir)
    waveform_type_map = load_waveform_type_map(types_parquet_path, types_csv_path)
    metadata_dims_df = load_metadata_dimensions(metadata_path, batch_size=batch_size)
    validate_metadata_uniqueness(metadata_dims_df, strict=args.strict_metadata_uniqueness)

    logger.info("Waveforms: %s", waveforms_path)
    logger.info("Metadata: %s", metadata_path)
    logger.info("Fonte de entrada: %s", "preview CSV" if using_preview else "base Parquet")
    logger.info("Waveform types mapeados: %d", len(waveform_type_map))
    logger.info("Dimensoes de metadata carregadas: %d", len(metadata_dims_df))

    tmp_dir = out_dir / f".tmp_spectral_{timestamp}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    bucket_paths = [tmp_dir / f"bucket_{idx:03d}.csv" for idx in range(num_buckets)]

    try:
        t0 = time.perf_counter()
        logger.info("Iniciando bucketizacao em disco para processamento em grande volume")
        bucketize_waveforms(
            waveforms_path=waveforms_path,
            bucket_paths=bucket_paths,
            metadata_dims_df=metadata_dims_df,
            waveform_type_map=waveform_type_map,
            batch_size=batch_size,
        )
        logger.info("Tempo bucketizacao: %.1fs", time.perf_counter() - t0)

        t1 = time.perf_counter()
        logger.info("Iniciando extracao de descritores por bucket")
        all_rows = process_all_buckets(
            bucket_paths=bucket_paths,
            wavelet_name=args.wavelet,
            max_wavelet_levels=max_wavelet_levels,
            min_samples=min_samples,
            workers=workers,
        )
        logger.info("Tempo extracao buckets: %.1fs", time.perf_counter() - t1)

        result_df = pd.DataFrame(all_rows)
        result_df = result_df.sort_values(GROUP_COLUMNS, kind="stable") if not result_df.empty else result_df

        stem = Path(args.output_file).stem
        output_format = getattr(args, "output_format", "both")

        if output_format in ("csv", "both"):
            csv_path = out_dir / f"{stem}.csv"
            result_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            logger.info("CSV gerado: %s (linhas=%d)", csv_path, len(result_df))

        if output_format in ("parquet", "both"):
            parquet_path = out_dir / f"{stem}.parquet"
            result_df.to_parquet(parquet_path, index=False)
            logger.info("Parquet gerado: %s (linhas=%d)", parquet_path, len(result_df))
        logger.info("Tempo total: %.1fs", time.perf_counter() - t0)

    finally:
        for bucket_path in bucket_paths:
            if bucket_path.exists():
                bucket_path.unlink()
        if tmp_dir.exists():
            tmp_dir.rmdir()


if __name__ == "__main__":
    main()
