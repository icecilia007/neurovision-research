"""
Main script for running the translation analysis.
"""

print("IMPORT TORCH ANTES")
import torch
print("IMPORT TORCH DEPOIS")
import functools
import os
import argparse
import pandas as pd
from cardiff.config.config import Config, QuestionsOnlyConfig
from cardiff.data.data_loader import load_original_text, load_translations
from cardiff.metrics.metricx import metricx, MetricX
from cardiff.metrics.alt_metrics import (
    flesch_reading_ease,
    gulpease_index,
    flesch_kincaid_grade_level,
    gunning_fog_index,
    automated_readability_index,
    coleman_liau_index,
    final_readability_score,
)
from cardiff.metrics.semantic_similarity import (
    bertscore,
    comet,
)
from cardiff.reporting.reporting import generate_report
from cardiff.analysis.statistical_analysis import (
    friedman_test,
    nemenyi_test,
    bootstrap_ci,
)


if not hasattr(functools, "_HashedSeq"):
    from collections import namedtuple

    _CacheInfo = namedtuple("CacheInfo", ["hits", "misses", "maxsize", "currsize"])

    class _HashedSeq(list):
        """This class guarantees that a list-like object is hashable even if its contents are not."""

        __slots__ = "hashvalue"

        def __init__(self, tup, hash=hash):
            self[:] = tup
            self.hashvalue = hash(tup)

        def __hash__(self):
            return self.hashvalue

    functools._HashedSeq = _HashedSeq


def run_pipeline(config: Config, against: str, metric_scorer: MetricX | None = None):
    """
    Runs the analysis pipeline for a given configuration.

    Args:
        config (Config): The configuration object.
        against (str): The reference to compare against. Can be "human" or "original".
        metric_scorer (MetricX | None): An instance of MetricX to use for scoring. If None, a new instance will be created.
    """
    # Load data
    original_text = load_original_text(config.original_text_path)
    translations = load_translations(config.translations_path)

    # Get reference text
    if against == "human":
        reference_text = next(
            (
                t.content
                for t in translations
                if t.filename == config.human_translation_filename
            ),
            None,
        )
        if not reference_text:
            raise ValueError("Human translation not found.")
    elif against == "original":
        reference_text = original_text
    else:
        raise ValueError("Invalid reference specified. Must be 'human' or 'original'.")

    # Initialize results
    results = []
    # if not metric_scorer:
    #     metric_scorer = MetricX()

    # Process each translation
    for i, translation in enumerate(translations):
        print(
            f"Processing translation {i+1}/{len(translations)}: {translation.filename}"
        )
        try:
            # ALT Metrics
            alt_metrics = {
                "flesch_reading_ease": flesch_reading_ease(translation.content),
                "gulpease_index": gulpease_index(translation.content),
                "flesch_kincaid_grade_level": flesch_kincaid_grade_level(
                    translation.content
                ),
                "gunning_fog_index": gunning_fog_index(translation.content),
                "automated_readability_index": automated_readability_index(
                    translation.content
                ),
                "coleman_liau_index": coleman_liau_index(translation.content),
                "final_readability_score": final_readability_score(translation.content),
            }

            # Semantic Similarity Metrics
            semantic_similarity_metrics = {
                "bertscore": bertscore(translation.content, reference_text),
                "comet": comet(translation.content, reference_text, original_text),
            }

            # # MetricX Metrics
            # metricx_metrics = {
            #     "metricx_ref": metricx(
            #         candidate=translation.content,
            #         reference=reference_text,
            #         source=original_text,
            #         metric_instance=metric_scorer,
            #     ),
            #     "metricx_qe": metricx(
            #         candidate=translation.content,
            #         reference="",
            #         source=original_text,
            #         metric_instance=metric_scorer,
            #     ),
            # }

            # Combine results
            result = {
                "model": translation.model_name,
                "date": translation.date,
                "item": i,
                **alt_metrics,
                **semantic_similarity_metrics,
            }
            results.append(result)
        except Exception as e:
            print(f"Error processing {translation.filename}: {e}")

    # Create a DataFrame and save to CSV
    df = pd.DataFrame(results)
    output_dir = os.path.join(config.output_path, against)
    os.makedirs(output_dir, exist_ok=True)
    df.to_csv(os.path.join(output_dir, "analysis_results.csv"), index=False)

    # Generate report
    generate_report(df, os.path.join(output_dir, "report.md"))


def run_statistical_analysis(config: Config):
    """
    Runs the statistical analysis.

    Args:
        config (Config): The configuration object.
    """
    # Load results
    human_results_df = pd.read_csv(
        os.path.join(config.output_path, "human", "analysis_results.csv")
    )
    original_results_df = pd.read_csv(
        os.path.join(config.output_path, "original", "analysis_results.csv")
    )

    # Perform Friedman test
    friedman_human_stat, friedman_human_p_value = friedman_test(
        human_results_df, "comet"
    )
    friedman_original_stat, friedman_original_p_value = friedman_test(
        original_results_df, "comet"
    )

    # Perform Nemenyi test
    nemenyi_human_df = nemenyi_test(human_results_df, "comet")
    nemenyi_original_df = nemenyi_test(original_results_df, "comet")

    # Perform bootstrap CI
    models = human_results_df["model"].unique()
    bootstrap_ci_human = {}
    bootstrap_ci_original = {}
    for model in models:
        bootstrap_ci_human[model] = bootstrap_ci(human_results_df, "comet", model)
        bootstrap_ci_original[model] = bootstrap_ci(original_results_df, "comet", model)

    bootstrap_ci_human_metricx_ref = {}
    bootstrap_ci_original_metricx_ref = {}
    for model in models:
        bootstrap_ci_human_metricx_ref[model] = bootstrap_ci(
            human_results_df, "metricx_ref", model
        )
        bootstrap_ci_original_metricx_ref[model] = bootstrap_ci(
            original_results_df, "metricx_ref", model
        )

    bootstrap_ci_human_metricx_qe = {}
    bootstrap_ci_original_metricx_qe = {}
    for model in models:
        bootstrap_ci_human_metricx_qe[model] = bootstrap_ci(
            human_results_df, "metricx_qe", model
        )
        bootstrap_ci_original_metricx_qe[model] = bootstrap_ci(
            original_results_df, "metricx_qe", model
        )

    # Generate report
    report = []
    report.append("# Statistical Analysis Report")
    report.append("\n")

    report.append("## Friedman Test")
    report.append("\n")
    report.append("### Against Human Translation")
    report.append("\n")
    report.append(f"Statistic: {friedman_human_stat}")
    report.append("\n")
    report.append(f"P-value: {friedman_human_p_value}")
    report.append("\n")
    report.append("### Against Original Text")
    report.append("\n")
    report.append(f"Statistic: {friedman_original_stat}")
    report.append("\n")
    report.append(f"P-value: {friedman_original_p_value}")
    report.append("\n")

    report.append("## Nemenyi Test")
    report.append("\n")
    report.append("### Against Human Translation")
    report.append("\n")
    report.append(nemenyi_human_df.to_markdown())
    report.append("\n")
    report.append("### Against Original Text")
    report.append("\n")
    report.append(nemenyi_original_df.to_markdown())
    report.append("\n")

    report.append("## Bootstrap Confidence Intervals")
    report.append("\n")
    report.append("### Comet - Against Human Translation")
    report.append("\n")
    report.append(pd.DataFrame(bootstrap_ci_human).to_markdown())
    report.append("\n")
    report.append("### Comet - Against Original Text")
    report.append("\n")
    report.append(pd.DataFrame(bootstrap_ci_original).to_markdown())
    report.append("\n")
    report.append("### MetricX Ref - Against Human Translation")
    report.append("\n")
    report.append(pd.DataFrame(bootstrap_ci_human_metricx_ref).to_markdown())
    report.append("\n")
    report.append("### MetricX Ref - Against Original Text")
    report.append("\n")
    report.append(pd.DataFrame(bootstrap_ci_original_metricx_ref).to_markdown())
    report.append("\n")
    report.append("### MetricX QE - Against Human Translation")
    report.append("\n")
    report.append(pd.DataFrame(bootstrap_ci_human_metricx_qe).to_markdown())
    report.append("\n")
    report.append("### MetricX QE - Against Original Text")
    report.append("\n")
    report.append(pd.DataFrame(bootstrap_ci_original_metricx_qe).to_markdown())
    report.append("\n")

    with open(
        os.path.join(config.output_path, "statistical_analysis.md"),
        "w",
        encoding="utf-8",
    ) as f:
        f.write("\n".join(report))


def main():
    """
    Main function to run the analysis.
    """
    parser = argparse.ArgumentParser(description="Run the translation analysis.")
    parser.add_argument(
        "--config",
        type=str,
        default="default",
        help="The configuration to use. Can be 'default' or 'questions-only'.",
    )
    args = parser.parse_args()

    if args.config == "default":
        config = Config()
    elif args.config == "questions-only":
        config = QuestionsOnlyConfig()
    else:
        raise ValueError(
            "Invalid config specified. Must be 'default' or 'questions-only'."
        )

    # metric_scorer = MetricX()
    # run_pipeline(config, "human", metric_scorer)
    # run_pipeline(config, "original", metric_scorer)
    run_pipeline(config, "human")
    run_pipeline(config, "original")
    run_statistical_analysis(config)


if __name__ == "__main__":
    main()
