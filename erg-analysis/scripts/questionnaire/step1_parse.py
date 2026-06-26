"""Phase 1 — Parse questionnaire JSON into a flat Parquet/CSV.

Usage:
  python -m scripts.questionnaire.step1_parse \\
      --questionnaire-input cardiff-questionnaire-responses/questionnaire_3_report_05-30-2026.json \\
      --output output/questionnaire/3 \\
      --base .
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.logging_utils import configure_logging
from common.path_utils import resolve_base_dir, resolve_input_path, resolve_output_dir
from common.questionnaire_parser import parse_questionnaire_file

logger = logging.getLogger(__name__)


def run(args: argparse.Namespace) -> None:
    base    = resolve_base_dir(args.base)
    run_tag = args.run_tag or datetime.now().strftime("%Y%m%d_%H%M%S")

    qs_path = resolve_input_path(base, args.questionnaire_input, must_exist=True)
    out_dir = resolve_output_dir(base, args.output, create=True)

    logger.info("Phase 1 — Parsing: %s", qs_path.name)
    parsed_df = parse_questionnaire_file(qs_path)

    q_id    = parsed_df["questionnaire_id"][0]    if "questionnaire_id"    in parsed_df.columns else "unknown"
    q_title = parsed_df["questionnaire_title"][0] if "questionnaire_title" in parsed_df.columns else ""
    logger.info("Questionnaire id=%s title='%s' | submissions=%d", q_id, q_title, len(parsed_df))

    out_base = out_dir / f"parsed_{run_tag}"
    parsed_df.write_parquet(str(out_base.with_suffix(".parquet")))
    parsed_df.write_csv(str(out_base.with_suffix(".csv")))
    logger.info("Written: %s (.parquet + .csv) — %d rows", out_base.stem, len(parsed_df))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase 1: parse questionnaire JSON → parquet/csv.")
    p.add_argument("--base",                 default=".")
    p.add_argument("--questionnaire-input",  required=True)
    p.add_argument("--output",               default="output/questionnaire")
    p.add_argument("--run-tag",              default=None, help="Override run tag (YYYYMMDD_HHMMSS)")
    return p


if __name__ == "__main__":
    configure_logging()
    run(build_parser().parse_args())
