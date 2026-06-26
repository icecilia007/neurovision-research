"""Classification submodule for supervised ML on ERG patient data."""

from analysis.classification.data_prep import (
    filter_annotated,
    binarize_column,
    expand_multilabel_column,
    join_label,
    aggregate_per_patient,
    split_train_test,
)
from analysis.classification.pipeline import (
    build_classification_pipeline,
    nested_cv_select_hyperparams,
    nested_cv_multiclass,
    nested_cv_multilabel,
)
from analysis.classification.evaluation import (
    log_class_balance,
    apply_smote_if_needed,
    evaluate_model,
    evaluate_binary_classifier,
    plot_confusion_matrix_from_counts,
)
from analysis.classification.feature_importance import run_feature_importance
from analysis.classification.persistence import (
    save_training_dataset,
    save_model,
    save_predictions,
    save_feature_importance,
)

__all__ = [
    "filter_annotated",
    "binarize_column",
    "expand_multilabel_column",
    "join_label",
    "aggregate_per_patient",
    "split_train_test",
    "build_classification_pipeline",
    "nested_cv_select_hyperparams",
    "nested_cv_multiclass",
    "nested_cv_multilabel",
    "log_class_balance",
    "apply_smote_if_needed",
    "evaluate_model",
    "evaluate_binary_classifier",
    "plot_confusion_matrix_from_counts",
    "run_feature_importance",
    "save_training_dataset",
    "save_model",
    "save_predictions",
    "save_feature_importance",
]
