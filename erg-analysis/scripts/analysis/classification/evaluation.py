"""Model evaluation helpers: class balance audit, SMOTE, and classification metrics."""

from __future__ import annotations

import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import polars as pl
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

logger = logging.getLogger(__name__)

_SMOTE_THRESHOLD = 0.30


def log_class_balance(df: pl.DataFrame, label_col: str) -> dict[str, float]:
    """Log and return class distribution for a boolean label column."""
    total = len(df)
    true_count = int(df[label_col].sum() or 0)
    null_count = int(df[label_col].null_count())
    false_count = total - true_count - null_count

    true_pct = true_count / total * 100 if total else 0.0
    false_pct = false_count / total * 100 if total else 0.0
    null_pct = null_count / total * 100 if total else 0.0

    logger.info(
        "class_balance(%s): total=%d | True=%d (%.1f%%) | False=%d (%.1f%%) | null=%d (%.1f%%)",
        label_col, total,
        true_count, true_pct,
        false_count, false_pct,
        null_count, null_pct,
    )

    minority_pct = min(true_pct, false_pct)
    if null_count > 0:
        logger.warning(
            "class_balance: %d null labels (%.1f%%) will be excluded from training",
            null_count, null_pct,
        )
    if minority_pct < _SMOTE_THRESHOLD * 100:
        logger.warning(
            "class_balance: minority class is %.1f%% — SMOTE will be applied (threshold=%.0f%%)",
            minority_pct, _SMOTE_THRESHOLD * 100,
        )

    return {
        "true_count": true_count,
        "false_count": false_count,
        "null_count": null_count,
        "true_pct": true_pct,
        "false_pct": false_pct,
        "null_pct": null_pct,
    }


def apply_smote_if_needed(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    threshold: float = _SMOTE_THRESHOLD,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.Series]:
    """Apply SMOTE oversampling when minority class fraction is below threshold."""
    counts = y_train.value_counts()
    total = len(y_train)
    minority_frac = counts.min() / total if total else 0.0

    if minority_frac >= threshold:
        logger.info(
            "apply_smote_if_needed: minority=%.1f%% >= threshold=%.0f%% — skipping SMOTE",
            minority_frac * 100, threshold * 100,
        )
        return X_train, y_train

    try:
        from imblearn.over_sampling import SMOTE
    except ImportError as exc:
        raise ImportError(
            "imbalanced-learn is required for SMOTE. Install with: pip install imbalanced-learn"
        ) from exc

    logger.info(
        "apply_smote_if_needed: minority=%.1f%% < threshold=%.0f%% — applying SMOTE",
        minority_frac * 100, threshold * 100,
    )
    sm = SMOTE(random_state=random_state)
    X_res, y_res, *_ = sm.fit_resample(X_train, y_train)
    logger.info(
        "apply_smote_if_needed: %d → %d training samples after SMOTE",
        len(X_train), len(X_res),
    )
    return pd.DataFrame(X_res, columns=X_train.columns), pd.Series(y_res, name=y_train.name)


def evaluate_model(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> dict:
    """Compute and log basic classification metrics on the test set."""
    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    report = classification_report(y_test, y_pred)

    logger.info("evaluate_model results:")
    logger.info("  accuracy  = %.4f", accuracy)
    logger.info("  precision = %.4f", precision)
    logger.info("  recall    = %.4f", recall)
    logger.info("  f1        = %.4f", f1)
    logger.info("classification_report:\n%s", report)

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "classification_report": report,
        "y_pred": y_pred,
    }


def evaluate_binary_classifier(
    model,
    X,
    y,
    model_name: str = "model",
    positive_label: int = 1,
    return_predictions: bool = False,
) -> pl.DataFrame | tuple[pl.DataFrame, pl.DataFrame]:
    """Evaluate a binary classifier and return a standardized Polars metrics DataFrame.

    Computes accuracy, balanced_accuracy, sensitivity, specificity, precision,
    f1, mcc, roc_auc, average_precision, and confusion matrix counts (tn/fp/fn/tp).

    Args:
        model: Fitted sklearn estimator or Pipeline.
        X: Feature matrix (pandas DataFrame or Polars DataFrame).
        y: True labels (pandas Series, numpy array, or Polars Series).
        model_name: Identifier string stored in the 'model' column.
        positive_label: The class label treated as positive (default 1).
        return_predictions: If True, also returns a DataFrame with y_true/y_pred/y_score.

    Returns:
        metrics_df (always), or (metrics_df, pred_df) when return_predictions=True.
    """
    y_true = y.to_numpy() if hasattr(y, "to_numpy") else np.asarray(y)
    y_pred = np.asarray(model.predict(X)).reshape(-1)

    classes_present = pl.Series(y_true).unique().to_list()
    if positive_label not in classes_present:
        classes_present.append(positive_label)

    negative_candidates = [c for c in classes_present if c != positive_label]
    negative_label = negative_candidates[0] if negative_candidates else (0 if positive_label != 0 else 1)

    y_score = None
    if hasattr(model, "predict_proba"):
        proba = np.asarray(model.predict_proba(X))
        if proba.ndim == 2:
            if hasattr(model, "classes_") and positive_label in list(model.classes_):
                pos_idx = list(model.classes_).index(positive_label)
            else:
                pos_idx = 1 if proba.shape[1] > 1 else 0
            y_score = proba[:, pos_idx]
        else:
            y_score = proba.reshape(-1)
    if y_score is None and hasattr(model, "decision_function"):
        y_score = np.asarray(model.decision_function(X)).reshape(-1)
        if hasattr(model, "classes_") and len(getattr(model, "classes_", [])) == 2:
            if list(model.classes_)[1] != positive_label:
                y_score = -y_score

    y_true_bin = (y_true == positive_label).astype(int)
    y_pred_bin = (y_pred == positive_label).astype(int)

    cm = confusion_matrix(y_true, y_pred, labels=[negative_label, positive_label])
    tn, fp, fn, tp = cm.ravel()

    roc_auc = roc_auc_score(y_true_bin, y_score) if y_score is not None else None
    avg_precision = average_precision_score(y_true_bin, y_score) if y_score is not None else None

    metrics_df = pl.DataFrame([{
        "model": model_name,
        "positive_label": positive_label,
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "sensitivity": recall_score(y_true, y_pred, pos_label=positive_label, zero_division=0),
        "specificity": recall_score(y_true, y_pred, pos_label=negative_label, zero_division=0),
        "precision": precision_score(y_true, y_pred, pos_label=positive_label, zero_division=0),
        "f1": f1_score(y_true, y_pred, pos_label=positive_label, zero_division=0),
        "mcc": matthews_corrcoef(y_true_bin, y_pred_bin),
        "roc_auc": roc_auc,
        "average_precision": avg_precision,
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }])

    if not return_predictions:
        return metrics_df

    pred_df = pl.DataFrame({
        "y_true": y_true,
        "y_pred": y_pred,
        "y_score": y_score if y_score is not None else np.full_like(y_pred, np.nan, dtype=float),
    })
    return metrics_df, pred_df


def plot_confusion_matrix_from_counts(
    tn: int,
    fp: int,
    fn: int,
    tp: int,
    title: str = "",
    *,
    ax=None,
) -> tuple:
    """Plot a confusion matrix from TN/FP/FN/TP counts.

    Args:
        tn, fp, fn, tp: Confusion matrix quadrant counts.
        title: Plot title.
        ax: Optional matplotlib Axes to draw on. Creates a new figure if None.

    Returns:
        (fig, ax) tuple.
    """
    cm = np.array([[tn, fp], [fn, tp]])
    if ax is None:
        fig, ax = plt.subplots(figsize=(4, 4))
    else:
        fig = ax.figure
    ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=["Controle (0)", "Neurodiv. (1)"],
    ).plot(ax=ax, colorbar=False)
    ax.set_title(title)
    plt.tight_layout()
    return fig, ax
