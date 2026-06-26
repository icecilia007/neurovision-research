"""Feature importance computation using MDI and Permutation Importance.

References:
  https://scikit-learn.org/stable/auto_examples/ensemble/plot_forest_importances.html

MDI (Mean Decrease in Impurity) — fast but biased toward high-cardinality features.
Permutation Importance — slower, computed on test set, unbiased and more reliable.

Both methods are returned together so they can be compared side by side.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import polars as pl
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


def run_feature_importance(
    pipeline: Pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    feature_names: list[str],
    *,
    n_repeats: int = 10,
    random_state: int = 42,
    n_jobs: int = -1,
) -> pl.DataFrame:
    """Compute MDI and Permutation Importance for a fitted Pipeline.

    The pipeline must have a step named 'model' with a feature_importances_
    attribute (e.g. DecisionTreeClassifier or RandomForestClassifier).

    MDI importances are read from model.feature_importances_ — these correspond
    to the transformed feature space after preprocessing, so feature_names must
    match the post-preprocessing column order from ColumnTransformer.

    Permutation Importance is computed on X_test (original feature space) so
    feature_names here must match X_test columns.

    Args:
        pipeline: Fitted sklearn Pipeline (preprocessor + model steps).
        X_test: Test features in original (pre-preprocessing) space.
        y_test: True test labels.
        feature_names: Feature names matching X_test columns.
        n_repeats: Number of permutation repeats (higher = more stable).
        random_state: Reproducibility seed.
        n_jobs: Parallel jobs for permutation (-1 = all cores).

    Returns:
        Polars DataFrame sorted by permutation_mean descending:
          feature | mdi | permutation_mean | permutation_std
    """
    model = pipeline.named_steps["model"]

    # --- MDI ---
    mdi_values: np.ndarray = model.feature_importances_
    preprocessor = pipeline.named_steps["preprocessor"]
    try:
        transformed_feature_names = preprocessor.get_feature_names_out()
    except AttributeError:
        transformed_feature_names = [f"feature_{i}" for i in range(len(mdi_values))]

    mdi_series = pd.Series(mdi_values, index=transformed_feature_names)
    logger.info("MDI computed: %d transformed features", len(mdi_series))

    # --- Permutation Importance (on original feature space) ---
    perm_result = permutation_importance(
        pipeline,
        X_test,
        y_test,
        n_repeats=n_repeats,
        random_state=random_state,
        n_jobs=n_jobs,
    )
    perm_means = perm_result.importances_mean
    perm_stds = perm_result.importances_std
    logger.info(
        "Permutation Importance computed: %d features, %d repeats",
        len(perm_means), n_repeats,
    )

    perm_df = pl.DataFrame({
        "feature": feature_names,
        "permutation_mean": perm_means.tolist(),
        "permutation_std": perm_stds.tolist(),
    })

    # MDI: map back original feature name → max MDI of its derived columns (after OHE)
    mdi_map: dict[str, float] = {}
    for orig_feat in feature_names:
        matching = [v for k, v in zip(transformed_feature_names, mdi_values)
                    if orig_feat in k]
        mdi_map[orig_feat] = float(np.sum(matching)) if matching else 0.0

    result = perm_df.with_columns(
        pl.col("feature").map_elements(lambda f: mdi_map.get(f, 0.0), return_dtype=pl.Float64).alias("mdi")
    ).sort("permutation_mean", descending=True)

    logger.info("Top 5 features by permutation importance:")
    for row in result.head(5).iter_rows(named=True):
        logger.info(
            "  %-40s  perm=%.4f ± %.4f  mdi=%.4f",
            row["feature"], row["permutation_mean"], row["permutation_std"], row["mdi"],
        )

    return result.select(["feature", "mdi", "permutation_mean", "permutation_std"])
