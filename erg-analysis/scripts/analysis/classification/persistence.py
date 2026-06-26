"""Persistence helpers: save training data, model, predictions, and feature importance.

Output layout per run:
  output_root / model_name / target / run_date / run_tag /
    training_data_{run_tag}.parquet
    test_data_{run_tag}.parquet
    model_{run_tag}.joblib
    predictions_{run_tag}.parquet
    feature_importance_{run_tag}.parquet
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import polars as pl

logger = logging.getLogger(__name__)


def _run_dir(output_root: Path, model_name: str, target: str, run_tag: str) -> Path:
    """Resolve and create the per-run output directory.

    Structure: output_root / model_name / target / run_date / run_tag
    run_date is derived from run_tag prefix (first 8 chars = YYYYMMDD).
    """
    run_date = run_tag[:8] if len(run_tag) >= 8 else datetime.now().strftime("%Y%m%d")
    path = output_root / model_name / target / run_date / run_tag
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_training_dataset(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    ids_train: pd.Series,
    ids_test: pd.Series,
    output_root: Path,
    model_name: str,
    target: str,
    run_tag: str,
) -> tuple[Path, Path]:
    """Save train and test datasets as parquet for full reproducibility and audit.

    Returns:
        (train_path, test_path)
    """
    run_path = _run_dir(output_root, model_name, target, run_tag)

    def _build_df(X: pd.DataFrame, y, ids) -> pl.DataFrame:
        df = X.copy()
        df["patient_unique_id_hashed"] = np.asarray(ids)
        df[target] = np.asarray(y)
        df["run_tag"] = run_tag
        df["saved_at"] = datetime.now().isoformat()
        return pl.from_pandas(df)

    train_path = run_path / f"training_data_{run_tag}.parquet"
    test_path = run_path / f"test_data_{run_tag}.parquet"

    _build_df(X_train, y_train, ids_train).write_parquet(str(train_path))
    _build_df(X_test, y_test, ids_test).write_parquet(str(test_path))

    logger.info("Training dataset saved: %s (%d rows)", train_path.name, len(X_train))
    logger.info("Test dataset saved:     %s (%d rows)", test_path.name, len(X_test))
    return train_path, test_path


def save_model(
    pipeline,
    output_root: Path,
    model_name: str,
    target: str,
    run_tag: str,
) -> Path:
    """Serialize the fitted sklearn Pipeline with joblib.

    Returns:
        Path to saved .joblib file.
    """
    run_path = _run_dir(output_root, model_name, target, run_tag)
    model_path = run_path / f"model_{run_tag}.joblib"
    joblib.dump(pipeline, model_path)
    logger.info("Model saved: %s", model_path)
    return model_path


def save_predictions(
    y_true: pd.Series,
    y_pred,
    ids: pd.Series,
    output_root: Path,
    model_name: str,
    target: str,
    run_tag: str,
) -> Path:
    """Save predictions alongside ground truth for monitoring and audit.

    Returns:
        Path to saved predictions parquet.
    """
    run_path = _run_dir(output_root, model_name, target, run_tag)
    pred_path = run_path / f"predictions_{run_tag}.parquet"

    pl.DataFrame({
        "patient_unique_id_hashed": ids.tolist(),
        "y_true": y_true.tolist(),
        "y_pred": list(map(int, y_pred)),
        "correct": [int(t) == int(p) for t, p in zip(y_true.tolist(), y_pred)],
        "target": target,
        "run_tag": run_tag,
        "predicted_at": datetime.now().isoformat(),
    }).write_parquet(str(pred_path))

    accuracy = sum(int(t) == int(p) for t, p in zip(y_true.tolist(), y_pred)) / len(y_true)
    logger.info(
        "Predictions saved: %s (%d rows, accuracy=%.4f)",
        pred_path.name, len(y_true), accuracy,
    )
    return pred_path


def save_feature_importance(
    importance_df: pl.DataFrame,
    output_root: Path,
    model_name: str,
    target: str,
    run_tag: str,
) -> Path:
    """Save the feature importance DataFrame as parquet.

    Returns:
        Path to saved feature_importance parquet.
    """
    run_path = _run_dir(output_root, model_name, target, run_tag)
    fi_path = run_path / f"feature_importance_{run_tag}.parquet"

    importance_df.with_columns([
        pl.lit(target).alias("target"),
        pl.lit(run_tag).alias("run_tag"),
        pl.lit(datetime.now().isoformat()).alias("computed_at"),
    ]).write_parquet(str(fi_path))

    logger.info("Feature importance saved: %s (%d features)", fi_path.name, len(importance_df))
    return fi_path
