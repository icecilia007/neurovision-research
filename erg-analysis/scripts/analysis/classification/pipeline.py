"""sklearn Pipeline builder and nested CV hyperparameter selection for ERG classification.

References:
  https://medium.com/data-hackers/como-usar-pipelines-no-scikit-learn-1398a4cc6ae9
"""

from __future__ import annotations

import logging
from collections import Counter

import numpy as np
import polars as pl
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    matthews_corrcoef,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, KFold, RepeatedKFold, RepeatedStratifiedKFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

logger = logging.getLogger(__name__)


def build_classification_pipeline(
    numeric_cols: list[str | int],
    categorical_cols: list[str | int],
    estimator,
) -> Pipeline:
    """Build a full sklearn Pipeline: preprocessing → any sklearn estimator.

    Preprocessing:
      - Numeric: median imputation → StandardScaler
      - Categorical: most_frequent imputation → OneHotEncoder (handle_unknown=ignore)

    Columns may be string names (pandas DataFrames) or integer indices (numpy arrays).
    The caller is responsible for instantiating the estimator with desired parameters
    before passing it here.

    Args:
        numeric_cols: Column names or integer indices for numeric features.
        categorical_cols: Column names or integer indices for categorical features.
        estimator: Any unfitted sklearn estimator (e.g. DecisionTreeClassifier()).

    Returns:
        Unfitted sklearn Pipeline with steps: preprocessor → model.
    """
    numeric_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_cols),
            ("categorical", categorical_pipeline, categorical_cols),
        ],
        remainder="drop",
    )

    return Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("model", estimator),
    ])


def nested_cv_select_hyperparams(
    pipeline,
    X: np.ndarray,
    y: np.ndarray,
    param_grid: dict,
    *,
    n_splits_outer: int = 5,
    n_repeats_outer: int = 20,
    n_splits_inner: int = 5,
    random_state: int = 123,
) -> tuple[dict, pl.DataFrame, pl.DataFrame]:
    """Select best hyperparameters via nested cross-validation.

    Outer loop (RepeatedStratifiedKFold): estimates unbiased generalization performance.
    Inner loop (StratifiedKFold + GridSearchCV): selects best hyperparameters per fold.

    The param combination that wins the most outer folds is returned as best_params.
    Use it to instantiate the final estimator and train on the full training set —
    do NOT reuse any model fitted inside this function.

    Args:
        pipeline: Unfitted sklearn Pipeline from build_classification_pipeline.
        X: Feature matrix as numpy array (use integer column indices in pipeline).
        y: Label vector as numpy array.
        param_grid: GridSearchCV param_grid with 'model__' prefix on keys.
        n_splits_outer: Outer CV splits (default 5).
        n_repeats_outer: Outer CV repeats (default 20 → 100 outer folds total).
        n_splits_inner: Inner GridSearchCV folds (default 5).
        random_state: Seed for all CV splits.

    Returns:
        (best_params, nested_cv_summary, best_params_summary)
        - best_params: dict without 'model__' prefix — use directly to instantiate estimator
        - nested_cv_summary: Polars DataFrame with mean/std/median/CI per metric
        - best_params_summary: Polars DataFrame of winning param combos sorted by count desc
    """
    inner_cv = StratifiedKFold(n_splits=n_splits_inner, shuffle=True, random_state=random_state)
    outer_cv = RepeatedStratifiedKFold(
        n_splits=n_splits_outer, n_repeats=n_repeats_outer, random_state=random_state
    )

    total_folds = n_splits_outer * n_repeats_outer
    outer_rows: list[dict] = []
    best_params_outer: list[dict] = []

    for fold_idx, (train_idx, test_idx) in enumerate(outer_cv.split(X, y), start=1):
        X_tr, X_te = X[train_idx], X[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]

        search = GridSearchCV(
            estimator=clone(pipeline),
            param_grid=param_grid,
            scoring="balanced_accuracy",
            cv=inner_cv,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_tr, y_tr)

        best_model = search.best_estimator_
        y_pred = best_model.predict(X_te)

        if hasattr(best_model, "predict_proba"):
            y_score = best_model.predict_proba(X_te)[:, 1]
        else:
            y_score = best_model.decision_function(X_te)

        outer_rows.append({
            "outer_fold": fold_idx,
            "balanced_accuracy": balanced_accuracy_score(y_te, y_pred),
            "roc_auc": roc_auc_score(y_te, y_score),
            "average_precision": average_precision_score(y_te, y_score),
            "f1": f1_score(y_te, y_pred, zero_division=0),
            "matthews_corrcoef": matthews_corrcoef(y_te, y_pred),
        })
        best_params_outer.append(search.best_params_)

        if fold_idx % 20 == 0:
            logger.info("nested_cv_select_hyperparams: fold %d/%d done", fold_idx, total_folds)

    nested_cv_folds = pl.DataFrame(outer_rows)

    summary_rows = []
    for metric in ["balanced_accuracy", "roc_auc", "average_precision", "f1", "matthews_corrcoef"]:
        vals = nested_cv_folds.get_column(metric)
        summary_rows.append({
            "metric": metric,
            "mean": float(vals.mean()),
            "std": float(vals.std()),
            "median": float(vals.median()),
            "q025": float(vals.quantile(0.025)),
            "q975": float(vals.quantile(0.975)),
        })

    nested_cv_summary = (
        pl.DataFrame(summary_rows)
        .select(["metric", "mean", "std", "median", "q025", "q975"])
        .sort("metric")
    )

    params_counter = Counter(tuple(sorted(p.items())) for p in best_params_outer)
    best_params_rows = []
    for params_tuple, count in params_counter.items():
        row = {k: v for k, v in params_tuple}
        row["count"] = count
        best_params_rows.append(row)

    best_params_summary = pl.DataFrame(best_params_rows).sort("count", descending=True)

    top_row = best_params_summary.row(0, named=True)
    best_params = {
        k.replace("model__", ""): v
        for k, v in top_row.items()
        if k != "count"
    }

    logger.info(
        "nested_cv_select_hyperparams: %d outer folds completed | best_params=%s",
        total_folds, best_params,
    )

    return best_params, nested_cv_summary, best_params_summary


def nested_cv_multiclass(
    pipeline,
    X: np.ndarray,
    y: np.ndarray,
    param_grid: dict,
    *,
    n_splits_outer: int = 5,
    n_repeats_outer: int = 20,
    n_splits_inner: int = 5,
    random_state: int = 123,
) -> tuple[dict, pl.DataFrame, pl.DataFrame]:
    """Like nested_cv_select_hyperparams but adapted for multi-class targets.

    Differences from the binary version:
      - roc_auc: OVR macro (nan when not computable for a fold)
      - f1: macro average
      - average_precision: omitted (nan placeholder)

    Args and returns are identical to nested_cv_select_hyperparams.
    """
    inner_cv = StratifiedKFold(n_splits=n_splits_inner, shuffle=True, random_state=random_state)
    outer_cv = RepeatedStratifiedKFold(
        n_splits=n_splits_outer, n_repeats=n_repeats_outer, random_state=random_state
    )

    total_folds = n_splits_outer * n_repeats_outer
    outer_rows: list[dict] = []
    best_params_outer: list[dict] = []

    for fold_idx, (train_idx, test_idx) in enumerate(outer_cv.split(X, y), start=1):
        X_tr, X_te = X[train_idx], X[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]

        search = GridSearchCV(
            estimator=clone(pipeline),
            param_grid=param_grid,
            scoring="balanced_accuracy",
            cv=inner_cv,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_tr, y_tr)

        best_model = search.best_estimator_
        y_pred = best_model.predict(X_te)

        roc_val = float("nan")
        if hasattr(best_model, "predict_proba"):
            try:
                roc_val = roc_auc_score(
                    y_te, best_model.predict_proba(X_te),
                    multi_class="ovr", average="macro",
                )
            except ValueError:
                pass

        outer_rows.append({
            "outer_fold": fold_idx,
            "balanced_accuracy": balanced_accuracy_score(y_te, y_pred),
            "roc_auc": roc_val,
            "average_precision": float("nan"),
            "f1": f1_score(y_te, y_pred, average="macro", zero_division=0),
            "matthews_corrcoef": matthews_corrcoef(y_te, y_pred),
        })
        best_params_outer.append(search.best_params_)

        if fold_idx % 20 == 0:
            logger.info("nested_cv_multiclass: fold %d/%d done", fold_idx, total_folds)

    nested_cv_folds = pl.DataFrame(outer_rows)

    summary_rows = []
    for metric in ["balanced_accuracy", "roc_auc", "f1", "matthews_corrcoef"]:
        vals = nested_cv_folds.get_column(metric).drop_nans()
        summary_rows.append({
            "metric": metric,
            "mean": float(vals.mean()) if len(vals) > 0 else float("nan"),
            "std": float(vals.std()) if len(vals) > 0 else float("nan"),
            "median": float(vals.median()) if len(vals) > 0 else float("nan"),
            "q025": float(vals.quantile(0.025)) if len(vals) > 0 else float("nan"),
            "q975": float(vals.quantile(0.975)) if len(vals) > 0 else float("nan"),
        })

    nested_cv_summary = (
        pl.DataFrame(summary_rows)
        .select(["metric", "mean", "std", "median", "q025", "q975"])
        .sort("metric")
    )

    params_counter = Counter(tuple(sorted(p.items())) for p in best_params_outer)
    best_params_rows = []
    for params_tuple, count in params_counter.items():
        row = {k: v for k, v in params_tuple}
        row["count"] = count
        best_params_rows.append(row)

    best_params_summary = pl.DataFrame(best_params_rows).sort("count", descending=True)

    top_row = best_params_summary.row(0, named=True)
    best_params = {
        k.replace("model__", ""): v
        for k, v in top_row.items()
        if k != "count"
    }

    logger.info(
        "nested_cv_multiclass: %d outer folds completed | best_params=%s",
        total_folds, best_params,
    )

    return best_params, nested_cv_summary, best_params_summary


def nested_cv_multilabel(
    pipeline,
    X: np.ndarray,
    y: np.ndarray,
    param_grid: dict,
    *,
    n_splits_outer: int = 5,
    n_repeats_outer: int = 20,
    n_splits_inner: int = 5,
    random_state: int = 123,
) -> tuple[dict, pl.DataFrame, pl.DataFrame]:
    """Nested CV for multi-label (multi-output) targets.

    DT and RF natively support 2-D y. Uses RepeatedKFold (not stratified)
    and mean balanced accuracy across output columns as the scoring metric.

    Args and returns are identical to nested_cv_select_hyperparams.
    """

    def _scorer(estimator, X_s, y_s):
        y_p = estimator.predict(X_s)
        scores = []
        for col in range(y_s.shape[1]):
            yt, yp = y_s[:, col], y_p[:, col]
            if len(np.unique(yt)) > 1:
                scores.append(balanced_accuracy_score(yt, yp))
        return float(np.mean(scores)) if scores else 0.0

    inner_cv = KFold(n_splits=n_splits_inner, shuffle=True, random_state=random_state)
    outer_cv = RepeatedKFold(
        n_splits=n_splits_outer, n_repeats=n_repeats_outer, random_state=random_state
    )

    total_folds = n_splits_outer * n_repeats_outer
    outer_rows: list[dict] = []
    best_params_outer: list[dict] = []

    for fold_idx, (train_idx, test_idx) in enumerate(outer_cv.split(X), start=1):
        X_tr, X_te = X[train_idx], X[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]

        search = GridSearchCV(
            estimator=clone(pipeline),
            param_grid=param_grid,
            scoring=_scorer,
            cv=inner_cv,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_tr, y_tr)

        best_model = search.best_estimator_
        y_pred = best_model.predict(X_te)

        ba_scores, f1_scores, mcc_scores = [], [], []
        for col in range(y_te.shape[1]):
            yt, yp = y_te[:, col], y_pred[:, col]
            if len(np.unique(yt)) > 1:
                ba_scores.append(balanced_accuracy_score(yt, yp))
                f1_scores.append(f1_score(yt, yp, zero_division=0))
                mcc_scores.append(matthews_corrcoef(yt, yp))

        outer_rows.append({
            "outer_fold": fold_idx,
            "balanced_accuracy": float(np.mean(ba_scores)) if ba_scores else float("nan"),
            "f1":                float(np.mean(f1_scores)) if f1_scores else float("nan"),
            "matthews_corrcoef": float(np.mean(mcc_scores)) if mcc_scores else float("nan"),
        })
        best_params_outer.append(search.best_params_)

        if fold_idx % 20 == 0:
            logger.info("nested_cv_multilabel: fold %d/%d done", fold_idx, total_folds)

    nested_cv_folds = pl.DataFrame(outer_rows)

    summary_rows = []
    for metric in ["balanced_accuracy", "f1", "matthews_corrcoef"]:
        vals = nested_cv_folds.get_column(metric).drop_nans()
        summary_rows.append({
            "metric": metric,
            "mean":   float(vals.mean())           if len(vals) > 0 else float("nan"),
            "std":    float(vals.std())            if len(vals) > 0 else float("nan"),
            "median": float(vals.median())         if len(vals) > 0 else float("nan"),
            "q025":   float(vals.quantile(0.025))  if len(vals) > 0 else float("nan"),
            "q975":   float(vals.quantile(0.975))  if len(vals) > 0 else float("nan"),
        })

    nested_cv_summary = (
        pl.DataFrame(summary_rows)
        .select(["metric", "mean", "std", "median", "q025", "q975"])
        .sort("metric")
    )

    params_counter = Counter(tuple(sorted(p.items())) for p in best_params_outer)
    best_params_rows = []
    for params_tuple, count in params_counter.items():
        row = {k: v for k, v in params_tuple}
        row["count"] = count
        best_params_rows.append(row)

    best_params_summary = pl.DataFrame(best_params_rows).sort("count", descending=True)

    top_row = best_params_summary.row(0, named=True)
    best_params = {
        k.replace("model__", ""): v
        for k, v in top_row.items()
        if k != "count"
    }

    logger.info(
        "nested_cv_multilabel: %d outer folds completed | best_params=%s",
        total_folds, best_params,
    )

    return best_params, nested_cv_summary, best_params_summary
