"""Phase 4 — Anonymize feature dataset: prontuario → bcrypt hash.

Reads the feature dataset (from step3_features), replaces prontuario with
the bcrypt hash from the ERG id_map, drops remaining PII, and writes the
final anonymized dataset to output/data/anonymized/datasets/.

Usage:
  python -m scripts.questionnaire.step4_anonymize \\
      --features-input output/questionnaire/3/features_20260605_120000.parquet \\
      --base .

Output: questionnaire_<id>_<run_tag>.parquet/.csv in output/data/anonymized/datasets/
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

from common.anonymization import anonymize_dataset, load_id_map
from common.logging_utils import configure_logging
from common.path_utils import resolve_base_dir, resolve_input_path, resolve_output_dir

logger = logging.getLogger(__name__)


def run(args: argparse.Namespace) -> None:
    base    = resolve_base_dir(args.base)
    run_tag = args.run_tag or datetime.now().strftime("%Y%m%d_%H%M%S")

    features_path = resolve_input_path(base, args.features_input, must_exist=True)
    out_dir       = resolve_output_dir(base, args.anon_datasets_dir, create=True)
    id_map_dir    = base / args.id_map_dir

    if features_path.suffix == ".csv":
        feature_df = pl.read_csv(str(features_path))
    else:
        feature_df = pl.read_parquet(str(features_path))

    # garantir que prontuario é Utf8 para o join com id_map
    if "prontuario" in feature_df.columns:
        feature_df = feature_df.with_columns(
            pl.col("prontuario").cast(pl.Utf8)
        )

    logger.info("Loaded features: %d rows from %s", len(feature_df), features_path.name)

    id_map = load_id_map(id_map_dir=id_map_dir)
    anon_df, audit = anonymize_dataset(feature_df, id_map)

    # infer questionnaire id from features if available
    q_id = "unknown"
    if "questionnaire_id" in feature_df.columns:
        q_id = str(feature_df["questionnaire_id"][0]).lower().replace(" ", "_")

    out_base = out_dir / f"questionnaire_{q_id}_{run_tag}"
    anon_df.write_parquet(str(out_base.with_suffix(".parquet")))
    anon_df.write_csv(str(out_base.with_suffix(".csv")))
    logger.info("Written: %s (.parquet + .csv) — %d rows", out_base.stem, len(anon_df))
    logger.info("Audit: input=%d | matched=%d | unmatched=%d | output=%d",
                audit["input_rows"], audit["matched_rows"],
                audit["unmatched_rows"], audit["output_rows"])


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Phase 4: anonymize feature dataset → output/data/anonymized/datasets/."
    )
    p.add_argument("--base",             default=".")
    p.add_argument("--features-input",   required=True,
                   help="features_<tag>.parquet/.csv from step3_features")
    p.add_argument("--id-map-dir",       default="output/data/anonymized",
                   help="Directory containing id_map_*.parquet")
    p.add_argument("--anon-datasets-dir", default="output/data/anonymized/datasets",
                   help="Output directory for anonymized dataset")
    p.add_argument("--run-tag",          default=None)
    return p


if __name__ == "__main__":
    configure_logging()
    run(build_parser().parse_args())
