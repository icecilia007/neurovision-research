"""
Clusterizacao exploratoria de ERG com foco em densidade (DBSCAN).

Entradas:
- CSV de features espectrais (padrao: erg_spectral_features.csv)

Regras aplicadas:
- Nao remove linhas com NaN
- Nao aplica normalizacao global
- Preserva magnitudes fisicas nas colunas numericas
- Clusteriza separadamente por waveform_type
- Opcional: clusterizar por waveform_type + TestStepType

Saidas:
- Dataset com coluna cluster
- Contagem por cluster
- Sumario de ruido (cluster = -1)
- Medias numericas por cluster
- Distribuicao de clusters por TestType e TestStepType
- Visualizacao PCA 2D por waveform_type (apenas para visualizacao)
"""

import argparse
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


ID_COLUMNS = ["patient_unique_id", "test_id"]
EXCLUDED_MODEL_COLUMNS = set(ID_COLUMNS + ["cluster"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clusterizacao exploratoria de ERG com DBSCAN separada por waveform_type."
    )
    parser.add_argument(
        "--input",
        default="outputs/hashed/erg/erg_spectral_features.csv",
        help="Arquivo CSV de entrada com features espectrais.",
    )
    parser.add_argument(
        "--output",
        default="outputs/hashed/erg/clustering",
        help="Diretorio de saida para resultados.",
    )
    parser.add_argument("--base", default=".", help="Diretorio base (padrao: diretorio atual)")
    parser.add_argument("--eps", type=float, default=0.5, help="Parametro eps do DBSCAN (padrao: 0.5)")
    parser.add_argument(
        "--min-samples",
        type=int,
        default=10,
        help="Parametro min_samples do DBSCAN (padrao: 10)",
    )
    parser.add_argument(
        "--pca-max-points",
        type=int,
        default=5000,
        help="Numero maximo de pontos no grafico PCA por waveform_type (padrao: 5000)",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Semente para amostragem de PCA (padrao: 42)",
    )
    parser.add_argument(
        "--pca-axis-percentile-low",
        type=float,
        default=1.0,
        help="Percentil inferior para ajuste robusto de eixo no PCA (padrao: 1.0).",
    )
    parser.add_argument(
        "--pca-axis-percentile-high",
        type=float,
        default=99.0,
        help="Percentil superior para ajuste robusto de eixo no PCA (padrao: 99.0).",
    )
    parser.add_argument(
        "--disable-pca-robust-axis",
        action="store_true",
        help="Desativa ajuste robusto de eixo no PCA (usa escala completa).",
    )
    parser.add_argument(
        "--partition-mode",
        choices=["waveform", "waveform_step"],
        default="waveform",
        help="Particionamento do clustering: waveform (padrao) ou waveform_step (waveform_type + TestStepType).",
    )
    return parser.parse_args()


def resolve_paths(base: str, input_path: str, output_dir: str) -> Tuple[Path, Path]:
    base_dir = Path(base).resolve()

    in_path = Path(input_path)
    if not in_path.is_absolute():
        in_path = (base_dir / in_path).resolve()

    out_dir = Path(output_dir)
    if not out_dir.is_absolute():
        out_dir = (base_dir / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    return in_path, out_dir


def split_feature_columns(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    candidate_cols = [c for c in df.columns if c not in EXCLUDED_MODEL_COLUMNS]

    numeric_cols: List[str] = []
    categorical_cols: List[str] = []
    for col in candidate_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)

    return numeric_cols, categorical_cols


def build_model_matrix(
    df_part: pd.DataFrame,
    numeric_cols: List[str],
    categorical_cols: List[str],
) -> Tuple[pd.DataFrame, List[str]]:
    if not numeric_cols and not categorical_cols:
        raise ValueError("Nenhuma feature disponivel para clusterizacao")

    blocks: List[pd.DataFrame] = []
    model_cols: List[str] = []

    if numeric_cols:
        num = df_part[numeric_cols].copy()
        blocks.append(num)
        model_cols.extend(num.columns.tolist())

    if categorical_cols:
        cat = df_part[categorical_cols].copy().fillna("MISSING").astype(str)
        cat_encoded = pd.get_dummies(cat, prefix=categorical_cols, dtype=np.int8)
        blocks.append(cat_encoded)
        model_cols.extend(cat_encoded.columns.tolist())

    X = pd.concat(blocks, axis=1)
    return X, model_cols


def nan_euclidean(u: np.ndarray, v: np.ndarray, min_valid: int = 5) -> float:
    mask = np.isfinite(u) & np.isfinite(v)

    if int(mask.sum()) < min_valid:
        return float(np.inf)

    diff = u[mask] - v[mask]
    return float(np.sqrt(np.mean(diff ** 2)))


def log_mean_distance_distribution(
    X: pd.DataFrame,
    waveform_type: str,
    min_samples: int,
) -> None:
    if len(X) < 2:
        logger.info("waveform_type=%s | Distancias: pontos insuficientes", waveform_type)
        return

    k = max(2, min(min_samples, len(X)))
    x_values = X.to_numpy(dtype=np.float64)
    nn = NearestNeighbors(
        n_neighbors=k,
        metric=nan_euclidean,
        metric_params={"min_valid": 5},
        algorithm="brute",
    )
    nn.fit(x_values)
    distances, _ = nn.kneighbors(x_values)
    mean_dist = distances.mean(axis=1)
    summary = pd.Series(mean_dist).describe(percentiles=[0.25, 0.5, 0.75, 0.9, 0.95]).to_dict()
    logger.info("waveform_type=%s | Distribuicao de distancias medias: %s", waveform_type, summary)


def run_dbscan(X: pd.DataFrame, eps: float, min_samples: int) -> np.ndarray:
    x_values = X.to_numpy(dtype=np.float64)
    model = DBSCAN(
        eps=eps,
        min_samples=min_samples,
        metric=nan_euclidean,
        metric_params={"min_valid": 5},
    )
    return model.fit_predict(x_values)


def plot_pca_clusters(
    X: pd.DataFrame,
    labels: np.ndarray,
    waveform_type: str,
    out_dir: Path,
    max_points: int,
    random_seed: int,
    robust_axis: bool,
    axis_percentile_low: float,
    axis_percentile_high: float,
) -> None:
    if len(X) < 2:
        return

    if len(X) > max_points:
        sampled_idx = X.sample(n=max_points, random_state=random_seed).index
        X_plot = X.loc[sampled_idx]
        labels_plot = labels[sampled_idx]
    else:
        X_plot = X
        labels_plot = labels

    if X_plot.shape[1] < 2:
        return

    pca = PCA(n_components=2, random_state=random_seed)
    coords = pca.fit_transform(X_plot)

    fig, ax = plt.subplots(figsize=(9, 6))

    unique_labels = sorted(np.unique(labels_plot))
    for cluster_id in unique_labels:
        mask = labels_plot == cluster_id
        color = "black" if cluster_id == -1 else None
        label = f"cluster {cluster_id}"
        ax.scatter(
            coords[mask, 0],
            coords[mask, 1],
            s=12,
            alpha=0.7,
            c=color,
            label=label,
        )

    ax.set_title(f"PCA 2D por cluster | waveform_type={waveform_type}")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.legend(loc="best", fontsize=8)
    ax.grid(alpha=0.2)

    if robust_axis:
        # Mantem todos os pontos no grafico, mas ajusta o viewport para a nuvem principal.
        x = coords[:, 0]
        y = coords[:, 1]

        if x.size >= 5 and y.size >= 5:
            x_lo, x_hi = np.nanpercentile(x, [axis_percentile_low, axis_percentile_high])
            y_lo, y_hi = np.nanpercentile(y, [axis_percentile_low, axis_percentile_high])

            x_span = x_hi - x_lo
            y_span = y_hi - y_lo

            if np.isfinite(x_span) and x_span > 0 and np.isfinite(y_span) and y_span > 0:
                x_pad = 0.08 * x_span
                y_pad = 0.08 * y_span
                ax.set_xlim(x_lo - x_pad, x_hi + x_pad)
                ax.set_ylim(y_lo - y_pad, y_hi + y_pad)

                out_of_view = int(((x < (x_lo - x_pad)) | (x > (x_hi + x_pad)) | (y < (y_lo - y_pad)) | (y > (y_hi + y_pad))).sum())
                if out_of_view > 0:
                    ax.text(
                        0.01,
                        0.01,
                        f"{out_of_view} ponto(s) fora do viewport robusto",
                        transform=ax.transAxes,
                        fontsize=8,
                        va="bottom",
                        ha="left",
                        bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "alpha": 0.7, "edgecolor": "none"},
                    )

    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", waveform_type)
    safe_name = safe_name.strip("._")
    if not safe_name:
        safe_name = "partition"
    plot_path = out_dir / f"pca_clusters_{safe_name}.png"
    fig.tight_layout()
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)


def summarize_clusters(
    df_clustered: pd.DataFrame,
    numeric_cols: List[str],
    partition_cols: List[str],
) -> Dict[str, pd.DataFrame]:
    base_group_cols = partition_cols + ["cluster"]

    counts = (
        df_clustered.groupby(base_group_cols, dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(base_group_cols)
    )

    noise = (
        df_clustered.assign(is_noise=df_clustered["cluster"] == -1)
        .groupby(partition_cols, dropna=False)
        .agg(total=("cluster", "size"), noise_count=("is_noise", "sum"))
        .reset_index()
    )
    noise["noise_pct"] = np.where(noise["total"] > 0, 100.0 * noise["noise_count"] / noise["total"], 0.0)

    if numeric_cols:
        means = (
            df_clustered.groupby(base_group_cols, dropna=False)[numeric_cols]
            .mean(numeric_only=True)
            .reset_index()
        )
    else:
        means = pd.DataFrame(columns=base_group_cols)

    if "TestType" in df_clustered.columns:
        group_cols = partition_cols + ["cluster", "TestType"]
        by_test_type = (
            df_clustered.groupby(group_cols, dropna=False)
            .size()
            .reset_index(name="count")
            .sort_values(partition_cols + ["cluster", "count"], ascending=[True] * len(partition_cols) + [True, False])
        )
    else:
        by_test_type = pd.DataFrame(columns=partition_cols + ["cluster", "TestType", "count"])

    if "TestStepType" in df_clustered.columns:
        if "TestStepType" in partition_cols:
            group_cols = partition_cols + ["cluster"]
        else:
            group_cols = partition_cols + ["cluster", "TestStepType"]
        by_test_step = (
            df_clustered.groupby(group_cols, dropna=False)
            .size()
            .reset_index(name="count")
            .sort_values(partition_cols + ["cluster", "count"], ascending=[True] * len(partition_cols) + [True, False])
        )
    else:
        by_test_step = pd.DataFrame(columns=partition_cols + ["cluster", "TestStepType", "count"])

    return {
        "counts": counts,
        "noise": noise,
        "means": means,
        "by_test_type": by_test_type,
        "by_test_step": by_test_step,
    }


def run_density_clustering(
    df: pd.DataFrame,
    eps: float,
    min_samples: int,
    pca_max_points: int,
    random_seed: int,
    out_dir: Path,
    partition_mode: str,
    pca_robust_axis: bool,
    pca_axis_percentile_low: float,
    pca_axis_percentile_high: float,
) -> Tuple[pd.DataFrame, List[str]]:
    if "waveform_type" not in df.columns:
        raise ValueError("Coluna obrigatoria ausente: waveform_type")

    all_parts: List[pd.DataFrame] = []

    if partition_mode == "waveform_step":
        if "TestStepType" not in df.columns:
            raise ValueError("partition_mode=waveform_step requer coluna TestStepType")
        partition_cols = ["waveform_type", "TestStepType"]
    else:
        partition_cols = ["waveform_type"]

    for col in partition_cols:
        df[col] = df[col].fillna("UNKNOWN").astype(str)

    partitions = sorted(df[partition_cols].drop_duplicates().itertuples(index=False, name=None))

    for part_key in partitions:
        if len(partition_cols) == 1:
            part_key = (part_key,)

        mask = np.ones(len(df), dtype=bool)
        for col, value in zip(partition_cols, part_key):
            mask &= df[col] == value

        part = df[mask].copy()
        if part.empty:
            continue

        partition_label = " | ".join(f"{col}={value}" for col, value in zip(partition_cols, part_key))

        numeric_cols, categorical_cols = split_feature_columns(part)
        categorical_cols = [c for c in categorical_cols if c not in partition_cols]

        X, model_cols = build_model_matrix(part, numeric_cols, categorical_cols)

        logger.info(
            "%s | linhas=%d | features_modelo=%d",
            partition_label,
            len(part),
            len(model_cols),
        )

        log_mean_distance_distribution(X, partition_label, min_samples)
        labels = run_dbscan(X, eps=eps, min_samples=min_samples)

        part["cluster"] = labels
        all_parts.append(part)

        noise_pct = 100.0 * (labels == -1).sum() / len(labels)
        logger.info(
            "%s | clusters=%d | ruido=%d (%.2f%%)",
            partition_label,
            len(set(labels.tolist())) - (1 if -1 in labels else 0),
            int((labels == -1).sum()),
            noise_pct,
        )

        plot_pca_clusters(
            X=X,
            labels=labels,
            waveform_type=partition_label,
            out_dir=out_dir,
            max_points=pca_max_points,
            random_seed=random_seed,
            robust_axis=pca_robust_axis,
            axis_percentile_low=pca_axis_percentile_low,
            axis_percentile_high=pca_axis_percentile_high,
        )

    if not all_parts:
        raise ValueError("Nenhuma particao processada para clustering")

    return pd.concat(all_parts, ignore_index=True), partition_cols


def save_outputs(df_clustered: pd.DataFrame, out_dir: Path, partition_cols: List[str]) -> None:
    numeric_cols = df_clustered.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c not in ["cluster"]]

    summaries = summarize_clusters(df_clustered, numeric_cols, partition_cols)

    df_clustered.to_csv(out_dir / "erg_spectral_clustered.csv", index=False, encoding="utf-8-sig")
    summaries["counts"].to_csv(out_dir / "cluster_counts.csv", index=False, encoding="utf-8-sig")
    summaries["noise"].to_csv(out_dir / "cluster_noise_summary.csv", index=False, encoding="utf-8-sig")
    summaries["means"].to_csv(out_dir / "cluster_feature_means.csv", index=False, encoding="utf-8-sig")
    summaries["by_test_type"].to_csv(
        out_dir / "cluster_distribution_by_testtype.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summaries["by_test_step"].to_csv(
        out_dir / "cluster_distribution_by_teststeptype.csv",
        index=False,
        encoding="utf-8-sig",
    )

    total_noise = int((df_clustered["cluster"] == -1).sum())
    total_rows = len(df_clustered)
    total_noise_pct = (100.0 * total_noise / total_rows) if total_rows else 0.0
    logger.info("Percentual global de ruido: %.2f%% (%d/%d)", total_noise_pct, total_noise, total_rows)


def main() -> None:
    args = parse_args()
    input_path, out_dir = resolve_paths(args.base, args.input, args.output)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    logger.info("Iniciando clusterizacao exploratoria: %s", timestamp)
    logger.info("Entrada: %s", input_path)
    logger.info("Saida: %s", out_dir)
    logger.info("Partition mode: %s", args.partition_mode)
    logger.info(
        "PCA robust axis: %s (p%.1f-p%.1f)",
        not args.disable_pca_robust_axis,
        args.pca_axis_percentile_low,
        args.pca_axis_percentile_high,
    )

    df = pd.read_csv(input_path, low_memory=False)

    df_clustered, partition_cols = run_density_clustering(
        df=df,
        eps=args.eps,
        min_samples=max(2, args.min_samples),
        pca_max_points=max(100, args.pca_max_points),
        random_seed=args.random_seed,
        out_dir=out_dir,
        partition_mode=args.partition_mode,
        pca_robust_axis=not args.disable_pca_robust_axis,
        pca_axis_percentile_low=float(args.pca_axis_percentile_low),
        pca_axis_percentile_high=float(args.pca_axis_percentile_high),
    )

    save_outputs(df_clustered, out_dir, partition_cols)
    logger.info("Clusterizacao finalizada com sucesso")


if __name__ == "__main__":
    main()
