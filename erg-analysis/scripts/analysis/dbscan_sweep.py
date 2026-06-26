"""
Varredura em massa de parametros do DBSCAN para validar ruido (cluster = -1).

Entradas:
- CSV de features espectrais (padrao: outputs/hashed/erg/erg_spectral_features.csv)

Saidas:
- dbscan_sweep_by_waveform.csv  (resultado por waveform_type e combinacao)
- dbscan_sweep_global.csv       (agregado global por combinacao)

Exemplo:
python scripts/sweep_dbscan_noise.py --base . --input outputs/hashed/erg/erg_spectral_features.csv --output outputs/hashed/erg/preview/dbscan_sweep_step --partition-mode waveform_step --eps-values 30,100,300,1000,3000,10000 --min-samples-values 2,3,4,5,6 --workers 12

"""

import argparse
import logging
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from cluster_erg_density import (
    build_model_matrix,
    nan_euclidean,
    resolve_paths,
    split_feature_columns,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


_SWEEP_X_VALUES: Optional[np.ndarray] = None


def _init_sweep_worker(x_values: np.ndarray) -> None:
    global _SWEEP_X_VALUES
    _SWEEP_X_VALUES = x_values


def _run_combo_worker(eps: float, min_samples: int) -> Dict[str, float]:
    global _SWEEP_X_VALUES
    if _SWEEP_X_VALUES is None:
        raise RuntimeError("Matriz de features nao inicializada no worker")

    t0 = time.perf_counter()
    model = DBSCAN(
        eps=eps,
        min_samples=min_samples,
        metric=nan_euclidean,
        metric_params={"min_valid": 5},
    )
    labels = model.fit_predict(_SWEEP_X_VALUES)

    total = int(len(labels))
    noise_count = int((labels == -1).sum())
    noise_pct = (100.0 * noise_count / total) if total else 0.0
    unique_labels = set(labels.tolist())
    n_clusters = int(len(unique_labels) - (1 if -1 in unique_labels else 0))
    elapsed = time.perf_counter() - t0

    return {
        "eps": float(eps),
        "min_samples": int(min_samples),
        "total": total,
        "noise_count": noise_count,
        "noise_pct": float(noise_pct),
        "n_clusters": n_clusters,
        "elapsed": float(elapsed),
    }


def parse_float_list(raw: str) -> List[float]:
    values = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        values.append(float(token))
    if not values:
        raise ValueError("Lista de eps vazia")
    return sorted(set(values))


def parse_int_list(raw: str) -> List[int]:
    values = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        values.append(int(token))
    if not values:
        raise ValueError("Lista de min_samples vazia")
    return sorted(set(max(2, v) for v in values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Varredura de eps/min_samples para validar ruido do DBSCAN por waveform_type."
    )
    parser.add_argument(
        "--input",
        default="outputs/hashed/erg/erg_spectral_features.csv",
        help="Arquivo CSV de entrada com features espectrais.",
    )
    parser.add_argument(
        "--output",
        default="outputs/hashed/erg/dbscan_sweep",
        help="Diretorio de saida para resultados da varredura.",
    )
    parser.add_argument("--base", default=".", help="Diretorio base (padrao: diretorio atual)")
    parser.add_argument(
        "--eps-values",
        default="0.2,0.3,0.5,0.8,1.0",
        help="Lista de eps separados por virgula.",
    )
    parser.add_argument(
        "--min-samples-values",
        default="8,10,12,16,20",
        help="Lista de min_samples separados por virgula.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, (os.cpu_count() or 1) - 1),
        help="Numero de processos para paralelizar combinacoes (padrao: cpu_count-1).",
    )
    parser.add_argument(
        "--partition-mode",
        choices=["waveform", "waveform_step"],
        default="waveform",
        help="Particionamento do sweep: waveform (padrao) ou waveform_step (waveform_type + TestStepType).",
    )
    return parser.parse_args()


def iter_partitions(
    df: pd.DataFrame,
    partition_mode: str,
) -> Iterable[Tuple[str, str, str, pd.DataFrame, pd.DataFrame]]:
    if partition_mode == "waveform_step":
        if "TestStepType" not in df.columns:
            raise ValueError("partition_mode=waveform_step requer coluna TestStepType")

        wf_series = df["waveform_type"].fillna("UNKNOWN").astype(str)
        step_series = df["TestStepType"].fillna("UNKNOWN").astype(str)
        keys_df = pd.DataFrame({"waveform_type": wf_series, "TestStepType": step_series})
        keys = sorted(keys_df.drop_duplicates().itertuples(index=False, name=None))

        for waveform_type, test_step_type in keys:
            mask = (wf_series == waveform_type) & (step_series == test_step_type)
            part = df[mask].copy()
            if part.empty:
                continue

            numeric_cols, categorical_cols = split_feature_columns(part)
            categorical_cols = [c for c in categorical_cols if c not in ["waveform_type", "TestStepType"]]
            X, _ = build_model_matrix(part, numeric_cols, categorical_cols)
            partition_key = f"waveform_type={waveform_type}|TestStepType={test_step_type}"
            yield partition_key, waveform_type, test_step_type, part, X
        return

    waveform_values = df["waveform_type"].fillna("UNKNOWN").astype(str).unique().tolist()
    waveform_values = sorted(waveform_values)

    for waveform_type in waveform_values:
        part = df[df["waveform_type"].fillna("UNKNOWN").astype(str) == waveform_type].copy()
        if part.empty:
            continue

        numeric_cols, categorical_cols = split_feature_columns(part)
        categorical_cols = [c for c in categorical_cols if c != "waveform_type"]
        X, _ = build_model_matrix(part, numeric_cols, categorical_cols)
        partition_key = f"waveform_type={waveform_type}"
        yield partition_key, waveform_type, "", part, X


def run_sweep(
    df: pd.DataFrame,
    eps_values: List[float],
    min_samples_values: List[int],
    workers: int,
    partition_mode: str,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if "waveform_type" not in df.columns:
        raise ValueError("Coluna obrigatoria ausente: waveform_type")

    by_waveform_rows = []
    combos = [(eps, min_samples) for eps in eps_values for min_samples in min_samples_values]
    total_combos = len(combos)

    parts = list(iter_partitions(df, partition_mode=partition_mode))
    if not parts:
        raise ValueError("Nenhuma particao disponivel para sweep")

    for partition_key, waveform_type, test_step_type, _part, X in parts:
        logger.info("Preparado bloco partition=%s com %d linhas", partition_key, len(X))
        x_values = X.to_numpy(dtype=np.float64)
        _init_sweep_worker(x_values)

        if workers <= 1:
            for combo_idx, (eps, min_samples) in enumerate(combos, start=1):
                result = _run_combo_worker(eps, min_samples)
                by_waveform_rows.append(
                    {
                        "partition_key": partition_key,
                        "waveform_type": waveform_type,
                        "TestStepType": test_step_type,
                        "eps": result["eps"],
                        "min_samples": int(result["min_samples"]),
                        "total": int(result["total"]),
                        "noise_count": int(result["noise_count"]),
                        "noise_pct": float(result["noise_pct"]),
                        "n_clusters": int(result["n_clusters"]),
                    }
                )
                logger.info(
                    "partition=%s | combo=%d/%d | eps=%.4g | min_samples=%d | ruido=%.2f%% | clusters=%d | tempo=%.1fs",
                    partition_key,
                    combo_idx,
                    total_combos,
                    result["eps"],
                    int(result["min_samples"]),
                    result["noise_pct"],
                    int(result["n_clusters"]),
                    result["elapsed"],
                )
            continue

        logger.info("Paralelizando combinacoes em partition=%s com workers=%d", partition_key, workers)
        completed = 0
        with ProcessPoolExecutor(max_workers=workers, initializer=_init_sweep_worker, initargs=(x_values,)) as executor:
            future_map = {
                executor.submit(_run_combo_worker, eps, min_samples): (eps, min_samples)
                for eps, min_samples in combos
            }
            for future in as_completed(future_map):
                result = future.result()
                completed += 1
                by_waveform_rows.append(
                    {
                        "partition_key": partition_key,
                        "waveform_type": waveform_type,
                        "TestStepType": test_step_type,
                        "eps": result["eps"],
                        "min_samples": int(result["min_samples"]),
                        "total": int(result["total"]),
                        "noise_count": int(result["noise_count"]),
                        "noise_pct": float(result["noise_pct"]),
                        "n_clusters": int(result["n_clusters"]),
                    }
                )
                logger.info(
                    "partition=%s | combo=%d/%d | eps=%.4g | min_samples=%d | ruido=%.2f%% | clusters=%d | tempo=%.1fs",
                    partition_key,
                    completed,
                    total_combos,
                    result["eps"],
                    int(result["min_samples"]),
                    result["noise_pct"],
                    int(result["n_clusters"]),
                    result["elapsed"],
                )

    by_waveform = pd.DataFrame(by_waveform_rows)

    grouped = by_waveform.groupby(["eps", "min_samples"], dropna=False)
    global_df = grouped.agg(
        total=("total", "sum"),
        noise_count=("noise_count", "sum"),
        mean_noise_pct=("noise_pct", "mean"),
        waveform_types=("waveform_type", "nunique"),
        sum_clusters=("n_clusters", "sum"),
    ).reset_index()

    global_df["global_noise_pct"] = np.where(
        global_df["total"] > 0,
        100.0 * global_df["noise_count"] / global_df["total"],
        0.0,
    )

    global_df = global_df.sort_values(
        ["global_noise_pct", "sum_clusters", "eps", "min_samples"],
        ascending=[True, False, True, True],
    ).reset_index(drop=True)

    return by_waveform, global_df


def main() -> None:
    args = parse_args()

    input_path, out_dir = resolve_paths(args.base, args.input, args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    eps_values = parse_float_list(args.eps_values)
    min_samples_values = parse_int_list(args.min_samples_values)
    workers = max(1, int(args.workers))

    logger.info("Entrada: %s", input_path)
    logger.info("Saida: %s", out_dir)
    logger.info("Grid eps=%s", eps_values)
    logger.info("Grid min_samples=%s", min_samples_values)
    logger.info("Workers=%d", workers)
    logger.info("Partition mode=%s", args.partition_mode)

    df = pd.read_csv(input_path, low_memory=False)

    by_waveform, global_df = run_sweep(
        df=df,
        eps_values=eps_values,
        min_samples_values=min_samples_values,
        workers=workers,
        partition_mode=args.partition_mode,
    )

    by_waveform_path = out_dir / "dbscan_sweep_by_waveform.csv"
    global_path = out_dir / "dbscan_sweep_global.csv"

    by_waveform.to_csv(by_waveform_path, index=False, encoding="utf-8-sig")
    global_df.to_csv(global_path, index=False, encoding="utf-8-sig")

    logger.info("Arquivo salvo: %s", by_waveform_path)
    logger.info("Arquivo salvo: %s", global_path)
    logger.info("Top 10 combinacoes (menor ruido global):")
    logger.info("\n%s", global_df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
