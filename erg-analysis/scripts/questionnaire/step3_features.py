"""Phase 3 — Build feature dataset from linked parquet/csv.

Reads the linked output (from step2_link or a manually revised version),
drops identity PII columns, and produces a clean feature dataset with prontuario.

This is the step where you can substitute a manually revised linked file
to correct or remove erroneous linkage results before anonymization.

Usage:
  python -m scripts.questionnaire.step3_features \\
      --linked-input output/questionnaire/3/manual_revised_20260605.csv \\
      --output output/questionnaire/3 \\
      --base .

Output: features_<run_tag>.parquet/.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import polars as pl

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.logging_utils import configure_logging
from common.path_utils import resolve_base_dir, resolve_input_path, resolve_output_dir
from common.questionnaire_feature_builder import build_feature_dataset

logger = logging.getLogger(__name__)


def run(args: argparse.Namespace) -> None:
    base    = resolve_base_dir(args.base)
    run_tag = args.run_tag or datetime.now().strftime("%Y%m%d_%H%M%S")

    linked_path = resolve_input_path(base, args.linked_input, must_exist=True)
    out_dir     = resolve_output_dir(base, args.output, create=True)

    # Support both parquet and csv
    if linked_path.suffix == ".csv":
        linked_df = pl.read_csv(str(linked_path))
    else:
        linked_df = pl.read_parquet(str(linked_path))

    logger.info("Loaded linked: %d rows from %s", len(linked_df), linked_path.name)

    # build_feature_dataset expects parsed_df + linkage_df separately,
    # but linked already has both merged. We reconstruct the linkage_df
    # from the columns present in linked.
    linkage_df = linked_df.select([
        pl.col("submission_id").cast(pl.Int64),
        pl.col("prontuario").cast(pl.Utf8),
        pl.lit("MATCH_UNIQUE").alias("decision"),
    ])

    feature_df = build_feature_dataset(
        parsed_df=linked_df,
        linkage_df=linkage_df,
        keep_unmatched=False,
        extra_pii_captions=args.extra_pii.split(",") if args.extra_pii else None,
    )

    logger.info("Feature dataset: %d rows | %d columns", len(feature_df), len(feature_df.columns))

    out_base = out_dir / f"features_{run_tag}"
    feature_df.write_parquet(str(out_base.with_suffix(".parquet")))
    feature_df.write_csv(str(out_base.with_suffix(".csv")))
    logger.info("Written: %s (.parquet + .csv)", out_base.stem)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Phase 3: build feature dataset from linked file (drop PII, keep prontuario)."
    )
    p.add_argument("--base",          default=".")
    p.add_argument("--linked-input",  required=True,
                   help="linked_<tag>.parquet/.csv — or your manually revised version")
    p.add_argument("--output",        default="output/questionnaire")
    p.add_argument("--run-tag",       default=None)
    p.add_argument("--extra-pii",     default=None,
                   help="Comma-separated extra caption columns to drop (e.g. F2,QS7)")
    return p


if __name__ == "__main__":
    configure_logging()
    run(build_parser().parse_args())
