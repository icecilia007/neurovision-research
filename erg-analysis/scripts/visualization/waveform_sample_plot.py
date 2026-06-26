"""
Plota waveforms para uma amostra de pacientes unicos.

Uso:
    python scripts/plot_waveform_sample.py \
        --base . \
        --input outputs/waveforms/consolidated/consolidated_waveforms.csv \
        --output outputs/plots/waveforms_sample \
        --num-patients 10

Tambem aceita diretorio em --input. Nesse caso tenta resolver automaticamente:
1) ultimo erg_waveforms_*.parquet
2) consolidated_waveforms.csv
3) ultimo *.parquet
"""

import argparse
import logging
import re
from pathlib import Path
from typing import Iterable, List

import matplotlib.pyplot as plt
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pa_parquet


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


REQUIRED_COLUMNS = ["patient_unique_id", "time_ms"]
SIGNAL_COLUMNS = ["voltage_uV", "pupil_mm"]
OPTIONAL_COLUMNS = ["test_id", "waveform_type_id", "waveform_type", "TestedEye", "TestStepType"]


def parse_patient_ids(raw: str | None) -> List[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def resolve_latest_file(input_dir: Path, pattern: str) -> Path | None:
    files = sorted(input_dir.glob(pattern))
    return files[-1] if files else None


def resolve_input_path(base_dir: Path, input_value: str) -> Path:
    input_path = Path(input_value)
    if not input_path.is_absolute():
        input_path = (base_dir / input_path).resolve()

    if input_path.is_file():
        return input_path

    if not input_path.is_dir():
        raise FileNotFoundError(f"Entrada nao encontrada: {input_path}")

    candidate = resolve_latest_file(input_path, "erg_waveforms_*.parquet")
    if candidate:
        return candidate

    consolidated = input_path / "consolidated_waveforms.csv"
    if consolidated.exists():
        return consolidated

    candidate = resolve_latest_file(input_path, "*.parquet")
    if candidate:
        return candidate

    raise FileNotFoundError(f"Nenhum arquivo de waveform encontrado em: {input_path}")


def get_available_columns(input_path: Path) -> List[str]:
    if input_path.suffix.lower() == ".csv":
        head = pd.read_csv(input_path, nrows=0)
        return [str(c) for c in head.columns]

    if input_path.suffix.lower() == ".parquet":
        pf = pa_parquet.ParquetFile(input_path)
        return [str(c) for c in pf.schema.names]

    raise ValueError(f"Formato nao suportado: {input_path.suffix}")


def iter_waveform_chunks(input_path: Path, columns: List[str], chunk_size: int) -> Iterable[pd.DataFrame]:
    if input_path.suffix.lower() == ".csv":
        for chunk in pd.read_csv(
            input_path,
            usecols=columns,
            chunksize=chunk_size,
            low_memory=False,
        ):
            yield chunk
        return

    if input_path.suffix.lower() == ".parquet":
        pf = pa_parquet.ParquetFile(input_path)
        for batch in pf.iter_batches(columns=columns, batch_size=chunk_size):
            yield pa.Table.from_batches([batch]).to_pandas()
        return

    raise ValueError(f"Formato nao suportado: {input_path.suffix}")


def pick_first_unique_patients(input_path: Path, chunk_size: int, num_patients: int) -> List[str]:
    selected: List[str] = []
    seen = set()

    columns = ["patient_unique_id"]
    for chunk in iter_waveform_chunks(input_path, columns, chunk_size):
        for patient_id in chunk["patient_unique_id"].dropna().astype(str):
            if patient_id in seen:
                continue
            seen.add(patient_id)
            selected.append(patient_id)
            if len(selected) >= num_patients:
                return selected

    return selected


def collect_rows_for_patients(
    input_path: Path,
    chunk_size: int,
    patient_ids: List[str],
    max_rows_per_patient: int,
) -> pd.DataFrame:
    target = set(patient_ids)
    counts = {pid: 0 for pid in patient_ids}
    rows: List[pd.DataFrame] = []

    available = set(get_available_columns(input_path))
    columns = [
        c
        for c in (REQUIRED_COLUMNS + SIGNAL_COLUMNS + OPTIONAL_COLUMNS)
        if c in available
    ]

    for chunk in iter_waveform_chunks(input_path, columns, chunk_size):
        if "patient_unique_id" not in chunk.columns:
            raise ValueError("Coluna patient_unique_id nao encontrada no input")

        chunk["patient_unique_id"] = chunk["patient_unique_id"].astype("string")
        filtered = chunk[chunk["patient_unique_id"].isin(target)].copy()
        if filtered.empty:
            continue

        if max_rows_per_patient > 0:
            limited: List[pd.DataFrame] = []
            for patient_id, group in filtered.groupby("patient_unique_id", sort=False):
                remaining = max_rows_per_patient - counts[str(patient_id)]
                if remaining <= 0:
                    continue
                if len(group) > remaining:
                    group = group.head(remaining)
                counts[str(patient_id)] += len(group)
                limited.append(group)

            if not limited:
                continue
            filtered = pd.concat(limited, ignore_index=True)

        rows.append(filtered)

        if max_rows_per_patient > 0 and all(counts[pid] >= max_rows_per_patient for pid in patient_ids):
            break

    if not rows:
        return pd.DataFrame(columns=columns)

    return pd.concat(rows, ignore_index=True)


def downsample_points(df: pd.DataFrame, max_points: int) -> pd.DataFrame:
    if len(df) <= max_points:
        return df
    step = max(1, len(df) // max_points)
    return df.iloc[::step].copy()


def sanitize_for_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)


def build_curve_label(group_key: object, group_cols: List[str]) -> str:
    if isinstance(group_key, tuple):
        values = list(group_key)
    else:
        values = [group_key]

    parts: List[str] = []
    for col, value in zip(group_cols, values):
        parts.append(f"{col}={value}")
    return " | ".join(parts)


def plot_patient_waveforms(
    patient_df: pd.DataFrame,
    patient_id: str,
    out_dir: Path,
    max_points_per_curve: int,
) -> Path | None:
    if patient_df.empty:
        return None

    patient_df = patient_df.copy()
    patient_df["time_ms"] = pd.to_numeric(patient_df["time_ms"], errors="coerce")
    for col in SIGNAL_COLUMNS:
        if col in patient_df.columns:
            patient_df[col] = pd.to_numeric(patient_df[col], errors="coerce")

    available_signals = [
        ("voltage_uV", "Voltage (uV)"),
        ("pupil_mm", "Pupil (mm)"),
    ]
    available_signals = [
        (col, title)
        for col, title in available_signals
        if col in patient_df.columns and patient_df[col].notna().any()
    ]

    if not available_signals:
        return None

    fig, axes = plt.subplots(len(available_signals), 1, figsize=(12, 4 * len(available_signals)))
    if len(available_signals) == 1:
        axes = [axes]

    for ax, (signal_col, signal_title) in zip(axes, available_signals):
        signal_df = patient_df.dropna(subset=["time_ms", signal_col]).copy()
        if signal_df.empty:
            ax.set_title(f"{signal_title} | sem dados")
            ax.grid(alpha=0.2)
            continue

        group_cols = [c for c in ["test_id", "waveform_type_id", "waveform_type", "TestedEye", "TestStepType"] if c in signal_df.columns]
        if not group_cols:
            group_cols = ["patient_unique_id"]

        grouped = list(signal_df.groupby(group_cols, dropna=False, sort=False))
        show_legend = len(grouped) <= 12

        for key, group in grouped:
            curve = group.sort_values("time_ms", kind="stable")
            curve = downsample_points(curve, max_points_per_curve)
            label = build_curve_label(key, group_cols)
            ax.plot(
                curve["time_ms"],
                curve[signal_col],
                linewidth=1.0,
                alpha=0.85,
                label=label if show_legend else None,
            )

        ax.set_title(signal_title)
        ax.set_xlabel("time_ms")
        ax.set_ylabel(signal_col)
        ax.grid(alpha=0.25)
        if show_legend:
            ax.legend(fontsize=7, loc="best")
        else:
            ax.text(
                0.01,
                0.99,
                f"{len(grouped)} curvas (legenda oculta)",
                transform=ax.transAxes,
                va="top",
                ha="left",
                fontsize=8,
                bbox={"facecolor": "white", "alpha": 0.7, "edgecolor": "none"},
            )

    fig.suptitle(f"Waveforms | patient_unique_id={patient_id}")
    fig.tight_layout()

    out_path = out_dir / f"waveform_{sanitize_for_filename(patient_id)}.png"
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Plota waveforms para uma amostra de pacientes unicos")
    parser.add_argument("--input", required=True, help="Arquivo de waveforms (.csv/.parquet) ou diretorio")
    parser.add_argument("--output", required=True, help="Diretorio de saida para imagens")
    parser.add_argument("--base", default=".", help="Diretorio base")
    parser.add_argument("--num-patients", type=int, default=10, help="Quantidade de pacientes unicos")
    parser.add_argument("--patient-ids", default=None, help="Lista de IDs separados por virgula")
    parser.add_argument("--chunk-size", type=int, default=200000, help="Chunk size de leitura")
    parser.add_argument(
        "--max-rows-per-patient",
        type=int,
        default=200000,
        help="Limite de linhas por paciente para plot (0 = sem limite)",
    )
    parser.add_argument(
        "--max-points-per-curve",
        type=int,
        default=3000,
        help="Maximo de pontos por curva para plot",
    )
    args = parser.parse_args()

    base_dir = Path(args.base).resolve()
    input_path = resolve_input_path(base_dir, args.input)

    out_dir = Path(args.output)
    if not out_dir.is_absolute():
        out_dir = (base_dir / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    available_cols = set(get_available_columns(input_path))
    missing_required = [c for c in REQUIRED_COLUMNS if c not in available_cols]
    if missing_required:
        raise ValueError(f"Colunas obrigatorias ausentes no input: {', '.join(missing_required)}")

    requested_patients = parse_patient_ids(args.patient_ids)
    if requested_patients:
        patient_ids = requested_patients[: max(1, args.num_patients)]
    else:
        patient_ids = pick_first_unique_patients(
            input_path=input_path,
            chunk_size=max(1, args.chunk_size),
            num_patients=max(1, args.num_patients),
        )

    if not patient_ids:
        raise ValueError("Nenhum patient_unique_id encontrado para plot")

    logger.info("Arquivo de entrada resolvido: %s", input_path)
    logger.info("Pacientes selecionados (%d): %s", len(patient_ids), patient_ids)

    sampled_rows = collect_rows_for_patients(
        input_path=input_path,
        chunk_size=max(1, args.chunk_size),
        patient_ids=patient_ids,
        max_rows_per_patient=max(0, args.max_rows_per_patient),
    )

    if sampled_rows.empty:
        raise ValueError("Nenhuma linha encontrada para os pacientes selecionados")

    saved_paths: List[Path] = []
    for patient_id in patient_ids:
        patient_df = sampled_rows[sampled_rows["patient_unique_id"].astype(str) == str(patient_id)].copy()
        out_path = plot_patient_waveforms(
            patient_df=patient_df,
            patient_id=str(patient_id),
            out_dir=out_dir,
            max_points_per_curve=max(100, int(args.max_points_per_curve)),
        )
        if out_path is not None:
            saved_paths.append(out_path)

    patients_txt = out_dir / "selected_patients.txt"
    patients_txt.write_text("\n".join(str(pid) for pid in patient_ids), encoding="utf-8")

    logger.info("Plots salvos: %d", len(saved_paths))
    logger.info("Lista de pacientes: %s", patients_txt)
    for path in saved_paths:
        logger.info("- %s", path)


if __name__ == "__main__":
    main()
