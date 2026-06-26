"""
This module is responsible for generating the report.

The report is a markdown file that contains two sections:
- Summary of Results: A summary of the results, including count, mean, std, min, 25%, 50%, 75%, and max.
- Detailed Results: The detailed results for each model.

The report is generated from a pandas DataFrame that contains the results of the analysis.
"""
import pandas as pd

def generate_report(results_df: pd.DataFrame, output_path: str):
    """
    Generates a report in markdown format.

    The report contains two sections:
    - Summary of Results: A summary of the results, including count, mean, std, min, 25%, 50%, 75%, and max.
    - Detailed Results: The detailed results for each model.

    The summary of results provides a quick overview of the performance of the models, while the detailed results provide a more in-depth view of the performance of each model.

    Args:
        results_df (pd.DataFrame): The DataFrame containing the results.
        output_path (str): The path to save the report to.
    """
    report = []
    report.append("# Translation Analysis Report")
    report.append("\n")

    report.append("## Summary of Results")
    report.append("\n")
    report.append(results_df.describe().to_markdown())
    report.append("\n")

    report.append("## Detailed Results")
    report.append("\n")
    report.append(results_df.to_markdown(index=False))
    report.append("\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
