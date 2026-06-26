"""Bridge module for the second pipeline flow.

This stage reads consolidated outputs and generates analytical Parquet datasets.
"""

from processing.erg_dataset_extraction import run as run_erg_dataset_extraction


def run_consolidated_to_parquet(args):
    run_erg_dataset_extraction(args)
