"""
This module implements the statistical analysis of the results.

The statistical analysis is used to determine if there is a significant difference between the performance of the models.

This module implements the following statistical tests:
- Friedman test: This is a non-parametric statistical test used to detect differences in treatments across multiple test attempts.
- Nemenyi post-hoc test: This is a post-hoc test used to determine which groups are significantly different from each other.
- Bootstrap confidence interval: This is a method for constructing confidence intervals from a bootstrapped sample.

References:
- Friedman test: https://en.wikipedia.org/wiki/Friedman_test
- Nemenyi test: https://en.wikipedia.org/wiki/Nemenyi_test
- Bootstrap confidence interval: https://en.wikipedia.org/wiki/Bootstrapping_(statistics)#Bootstrap_confidence_intervals
"""
import pandas as pd
from scipy.stats import friedmanchisquare
from scikit_posthocs import posthoc_nemenyi_friedman
import numpy as np

def friedman_test(df: pd.DataFrame, metric: str) -> tuple[float, float]:
    """
    Performs the Friedman test on the given dataframe and metric.

    The Friedman test is a non-parametric statistical test used to detect differences in treatments across multiple test attempts.
    In this case, the treatments are the different models, and the test attempts are the different items in the questionnaire.

    The null hypothesis is that there is no difference between the performance of the models.
    If the p-value is less than 0.05, we reject the null hypothesis and conclude that there is a significant difference between the models.

    Args:
        df (pd.DataFrame): The dataframe with the results.
        metric (str): The metric to perform the test on.

    Returns:
        tuple: A tuple containing the statistic and the p-value.
    """
    # Pivot the dataframe to have the models as columns and the items as rows
    pivot_df = df.pivot(index="item", columns="model", values=metric)
    
    # Perform the Friedman test
    stat, p_value = friedmanchisquare(*[pivot_df[col] for col in pivot_df.columns])
    
    return stat, p_value

def nemenyi_test(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """
    Performs the Nemenyi post-hoc test on the given dataframe and metric.

    The Nemenyi test is a post-hoc test used to determine which groups are significantly different from each other.
    In this case, the groups are the different models.

    The test returns a dataframe with the p-values for each pair of models.
    If the p-value is less than 0.05, we can conclude that there is a significant difference between the two models.

    Args:
        df (pd.DataFrame): The dataframe with the results.
        metric (str): The metric to perform the test on.

    Returns:
        pd.DataFrame: A dataframe with the Nemenyi test results.
    """
    # Pivot the dataframe to have the models as columns and the items as rows
    pivot_df = df.pivot(index="item", columns="model", values=metric)
    
    # Perform the Nemenyi test
    nemenyi_df = posthoc_nemenyi_friedman(pivot_df)
    
    return nemenyi_df

def bootstrap_ci(df: pd.DataFrame, metric: str, model: str, n_bootstraps: int = 1000) -> tuple[float, float]:
    """
    Calculates the bootstrap confidence interval for a given metric and model.

    Bootstrapping is a statistical method for estimating the sampling distribution of an estimator by sampling with replacement from the original sample.
    In this case, we are using bootstrapping to estimate the confidence interval of the mean of the scores for a given model and metric.

    The confidence interval is a range of values that is likely to contain the true mean of the scores.
    If the confidence intervals of two models overlap, we can conclude that there is no significant difference between the two models.

    Args:
        df (pd.DataFrame): The dataframe with the results.
        metric (str): The metric to calculate the confidence interval for.
        model (str): The model to calculate the confidence interval for.
        n_bootstraps (int, optional): The number of bootstraps to perform. Defaults to 1000.

    Returns:
        tuple: A tuple containing the lower and upper bounds of the confidence interval.
    """
    # Get the scores for the given model and metric
    scores = df[df["model"] == model][metric].values
    
    # Perform bootstrap resampling
    bootstrapped_scores = []
    for _ in range(n_bootstraps):
        bootstrap_sample = np.random.choice(scores, size=len(scores), replace=True)
        bootstrapped_scores.append(np.mean(bootstrap_sample))
    
    # Calculate the confidence interval
    lower_bound = np.percentile(bootstrapped_scores, 2.5)
    upper_bound = np.percentile(bootstrapped_scores, 97.5)
    
    return lower_bound, upper_bound