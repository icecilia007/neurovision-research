"""
Cria previews para datasets Parquet de ERG.

Modos suportados:
1) Preview simples por limite de linhas (comportamento legado)
2) Preview por pacientes (preview2), preservando waveforms completos

Exemplo de uso (legado):
    python scripts/visualization/parquet_preview.py \
        --base . \
        --input output/data/anonymized/datasets \
        --output output/data/anonymized/datasets/preview \
        --limit 10

Exemplo de uso (preview2 — padrões automáticos a partir de --input):
    python scripts/visualization/parquet_preview.py \
        --base . \
        --input output/data/anonymized/datasets \
        --output output/data/anonymized/datasets/preview \
        --num-patients 10

Exemplo de uso (preview2 — caminhos explícitos, útil quando os arquivos
estão em diretórios diferentes ou com nomes fora do padrão):
    python scripts/visualization/parquet_preview.py \
        --base . \
        --output output/data/anonymized/datasets/preview \
        --num-patients 10 \
        --waveforms  output/data/anonymized/datasets/waveforms_20260424_190945.parquet \
        --metadata   output/data/anonymized/staging/metadata_20260424_190945.parquet \
        --features   output/data/anonymized/datasets/patients-features_20260424_190945.parquet \
        --waveform-types output/data/anonymized/datasets/waveform_types_20260424_190945.parquet
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pa_parquet


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def resolve_input_files(input_path: Path) -> List[Path]:
    if input_path.is_file() and input_path.suffix.lower() == ".parquet":
        return [input_path]
    if input_path.is_dir():
        return sorted(input_path.glob("*.parquet"))
    return []


def read_parquet_head(parquet_path: Path, limit: int) -> pd.DataFrame:
    pf = pa_parquet.ParquetFile(parquet_path)
    remaining = limit
    tables = []
    for row_group_idx in range(pf.num_row_groups):
        if remaining <= 0:
            break
        table = pf.read_row_group(row_group_idx)
        if table.num_rows > remaining:
            table = table.slice(0, remaining)
        tables.append(table)
        remaining -= table.num_rows

    if not tables:
        return pd.DataFrame()

    return pa.concat_tables(tables).to_pandas()


def resolve_latest_file(input_dir: Path, pattern: str) -> Path:
    files = sorted(input_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo encontrado para o padrao: {pattern}")
    return files[-1]


def resolve_erg_dataset_files(
    input_dir: Path,
    waveforms: Path | None = None,
    metadata: Path | None = None,
    features: Path | None = None,
    waveform_types: Path | None = None,
) -> Dict[str, Path]:
    """Resolve os 4 arquivos ERG necessários para o preview2.

    Quando um caminho explícito é fornecido ele tem precedência sobre a busca
    por padrão no diretório. Os padrões suportados (do mais específico ao mais
    genérico) são tentados em ordem até encontrar ao menos um arquivo.
    """
    def _resolve(explicit: Path | None, dir_: Path, *patterns: str) -> Path:
        if explicit is not None:
            return explicit
        for pat in patterns:
            try:
                return resolve_latest_file(dir_, pat)
            except FileNotFoundError:
                continue
        raise FileNotFoundError(
            f"Nenhum arquivo encontrado em {dir_} para os padrões: {list(patterns)}"
        )

    return {
        "waveforms":     _resolve(waveforms,     input_dir, "waveforms_*.parquet",       "erg_waveforms_*.parquet"),
        "metadata":      _resolve(metadata,      input_dir, "metadata_*.parquet",         "erg_metadata_*.parquet"),
        "features":      _resolve(features,      input_dir, "patients-features_*.parquet","erg_features_*.parquet"),
        "waveform_types":_resolve(waveform_types,input_dir, "waveform_types_*.parquet",   "erg_waveform_types_*.parquet"),
    }


def pick_first_patients_from_waveforms(waveforms_path: Path, num_patients: int) -> List[str]:
    pf = pa_parquet.ParquetFile(waveforms_path)
    selected: List[str] = []
    seen = set()

    for batch in pf.iter_batches(columns=["patient_unique_id"], batch_size=200_000):
        values = batch.column(0).to_pylist()
        for value in values:
            if value is None or value in seen:
                continue
            seen.add(value)
            selected.append(value)
            if len(selected) >= num_patients:
                return selected
    return selected


def filter_parquet_by_patients(parquet_path: Path, patient_ids: set[str]) -> pd.DataFrame:
    pf = pa_parquet.ParquetFile(parquet_path)
    chunks: List[pd.DataFrame] = []

    for batch in pf.iter_batches(batch_size=200_000):
        df_chunk = pa.Table.from_batches([batch]).to_pandas()
        if "patient_unique_id" not in df_chunk.columns:
            continue
        filtered = df_chunk[df_chunk["patient_unique_id"].isin(patient_ids)]
        if not filtered.empty:
            chunks.append(filtered)

    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks, ignore_index=True)


def build_preview2(
    input_dir: Path,
    out_dir: Path,
    num_patients: int,
    *,
    waveforms: Path | None = None,
    metadata: Path | None = None,
    features: Path | None = None,
    waveform_types: Path | None = None,
) -> None:
    files = resolve_erg_dataset_files(
        input_dir,
        waveforms=waveforms,
        metadata=metadata,
        features=features,
        waveform_types=waveform_types,
    )
    logger.info("Arquivos ERG selecionados: %s", {k: v.name for k, v in files.items()})

    selected_patients = pick_first_patients_from_waveforms(files["waveforms"], num_patients)
    if not selected_patients:
        raise ValueError("Nenhum patient_unique_id encontrado no dataset de waveforms")

    logger.info("Pacientes selecionados para preview2: %d", len(selected_patients))
    patient_set = set(selected_patients)

    waveforms_df = filter_parquet_by_patients(files["waveforms"], patient_set)
    metadata_df = filter_parquet_by_patients(files["metadata"], patient_set)
    features_df = filter_parquet_by_patients(files["features"], patient_set)
    waveform_types_df = pd.read_parquet(files["waveform_types"])

    for frame in [waveforms_df, metadata_df, features_df]:
        if "patient_unique_id" in frame.columns:
            frame["patient_unique_id"] = frame["patient_unique_id"].astype("string")
        if "test_id" in frame.columns:
            frame["test_id"] = frame["test_id"].astype("string")

    if waveforms_df.empty:
        raise ValueError("Preview2 nao pode ser gerado: waveforms vazio apos filtro por pacientes")

    if "waveform_type_id" in waveforms_df.columns and "waveform_type_id" in waveform_types_df.columns:
        waveforms_df["waveform_type_id"] = pd.to_numeric(waveforms_df["waveform_type_id"], errors="coerce")
        waveform_types_df["waveform_type_id"] = pd.to_numeric(waveform_types_df["waveform_type_id"], errors="coerce")
        waveforms_df = waveforms_df.merge(
            waveform_types_df[["waveform_type_id", "waveform_type"]],
            on="waveform_type_id",
            how="left",
        )

    # Propaga dimensoes experimentais para preservar unidade de analise por sinal.
    metadata_dims_cols = ["patient_unique_id", "test_id", "TestType", "TestedEye", "TestStepType"]
    if all(col in metadata_df.columns for col in metadata_dims_cols):
        metadata_dims = metadata_df[metadata_dims_cols].drop_duplicates(
            subset=["patient_unique_id", "test_id"],
            keep="first",
        )
        waveforms_df = waveforms_df.merge(
            metadata_dims,
            on=["patient_unique_id", "test_id"],
            how="left",
        )

    # Define dominio fisico esperado por waveform_type_id.
    if "waveform_type_id" in waveforms_df.columns:
        wf_id = pd.to_numeric(waveforms_df["waveform_type_id"], errors="coerce")
        waveforms_df["signal_type"] = "unknown"
        waveforms_df.loc[wf_id == 1, "signal_type"] = "pupil"
        waveforms_df.loc[wf_id.isin([2, 3]), "signal_type"] = "voltage"

    if "time_ms" in waveforms_df.columns:
        waveforms_df["time_ms"] = pd.to_numeric(waveforms_df["time_ms"], errors="coerce")
    sort_cols = [
        c
        for c in [
            "patient_unique_id",
            "test_id",
            "TestType",
            "waveform_type",
            "waveform_type_id",
            "TestedEye",
            "TestStepType",
            "time_ms",
        ]
        if c in waveforms_df.columns
    ]
    if sort_cols:
        waveforms_df = waveforms_df.sort_values(sort_cols, kind="stable")

    waveform_types_used = waveform_types_df
    if "waveform_type_id" in waveforms_df.columns and "waveform_type_id" in waveform_types_df.columns:
        used_ids = set(pd.to_numeric(waveforms_df["waveform_type_id"], errors="coerce").dropna().astype(int))
        waveform_types_used = waveform_types_df[
            waveform_types_df["waveform_type_id"].isin(used_ids)
        ].copy()

    waveforms_out = out_dir / "preview2_erg_waveforms.csv"
    metadata_out = out_dir / "preview2_erg_metadata.csv"
    features_out = out_dir / "preview2_erg_features.csv"
    waveform_types_out = out_dir / "preview2_erg_waveform_types.csv"

    waveforms_df.to_csv(waveforms_out, index=False, encoding="utf-8-sig")
    metadata_df.to_csv(metadata_out, index=False, encoding="utf-8-sig")
    features_df.to_csv(features_out, index=False, encoding="utf-8-sig")
    waveform_types_used.to_csv(waveform_types_out, index=False, encoding="utf-8-sig")

    logger.info("Preview2 gerado:")
    logger.info("- %s (linhas=%d)", waveforms_out, len(waveforms_df))
    logger.info("- %s (linhas=%d)", metadata_out, len(metadata_df))
    logger.info("- %s (linhas=%d)", features_out, len(features_df))
    logger.info("- %s (linhas=%d)", waveform_types_out, len(waveform_types_used))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera CSV com as primeiras linhas de arquivos Parquet."
    )
    parser.add_argument("--input", default=None, help="Arquivo Parquet ou diretório com Parquet (pode ser omitido no modo --num-patients com caminhos explícitos)")
    parser.add_argument("--output", required=True, help="Diretorio de saida para o CSV")
    parser.add_argument("--base", default=".", help="Diretorio base (padrao: diretorio atual)")
    parser.add_argument("--limit", type=int, default=10, help="Quantidade de linhas (padrao: 10)")
    parser.add_argument(
        "--num-patients",
        type=int,
        default=None,
        nargs="?",
        const=10,
        help="Ativa o modo preview2 e define quantos pacientes incluir (padrao: 10 quando fornecido sem valor)",
    )
    parser.add_argument("--waveforms",     default=None, help="Caminho explícito para o arquivo de waveforms")
    parser.add_argument("--metadata",      default=None, help="Caminho explícito para o arquivo de metadata")
    parser.add_argument("--features",      default=None, help="Caminho explícito para o arquivo de features")
    parser.add_argument("--waveform-types",default=None, help="Caminho explícito para o arquivo de waveform_types")
    args = parser.parse_args()

    base_dir = Path(args.base).resolve()

    def _resolve_path(raw: str | None) -> Path | None:
        if raw is None:
            return None
        p = Path(raw)
        return p if p.is_absolute() else (base_dir / p).resolve()

    input_path = _resolve_path(args.input) or base_dir
    out_dir = Path(args.output)
    if not out_dir.is_absolute():
        out_dir = (base_dir / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.num_patients is not None:
        num_patients = max(1, args.num_patients)
        explicit_files = {k: _resolve_path(v) for k, v in {
            "waveforms":     args.waveforms,
            "metadata":      args.metadata,
            "features":      args.features,
            "waveform_types":args.waveform_types,
        }.items()}
        # --input pode ser omitido apenas quando os 4 caminhos são explícitos
        all_explicit = all(explicit_files.values())
        if not all_explicit and not input_path.is_dir():
            raise ValueError(
                "No modo --num-patients, forneça --input (diretório) "
                "ou os 4 caminhos explícitos (--waveforms, --metadata, --features, --waveform-types)"
            )
        if all_explicit:
            input_path = input_path  # input_dir não será usado; qualquer valor serve
        build_preview2(
            input_path, out_dir, num_patients,
            waveforms=explicit_files["waveforms"],
            metadata=explicit_files["metadata"],
            features=explicit_files["features"],
            waveform_types=explicit_files["waveform_types"],
        )
        return

    files = resolve_input_files(input_path)
    if not files:
        logger.error("Nenhum arquivo Parquet encontrado em %s", input_path)
        return

    limit = max(1, args.limit)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    for parquet_path in files:
        logger.info("Lendo %s", parquet_path.name)
        preview = read_parquet_head(parquet_path, limit)

        csv_name = f"preview_{parquet_path.stem}_{timestamp}.csv"
        csv_path = out_dir / csv_name
        preview.to_csv(csv_path, index=False, encoding="utf-8-sig")
        logger.info("Preview salvo: %s", csv_path)


if __name__ == "__main__":
    main()
