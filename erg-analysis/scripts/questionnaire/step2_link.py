"""Phase 2 — Record linkage: parsed parquet → linked parquet/csv.

Reads the parsed output from step1_parse and links each submission to a
prontuario using name + birth year + gender matching.

Usage:
  python -m scripts.questionnaire.step2_link \\
      --parsed-input output/questionnaire/3/parsed_20260605_120000.parquet \\
      --output output/questionnaire/3 \\
      --base .

Output: linked_<run_tag>.parquet/.csv  (parsed data + prontuario + score + phase)
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
from common.patient_lookup import build_patient_table, build_righteye_table
from questionnaire.record_linkage import _Query, _phase0_prontuario, match_record

logger = logging.getLogger(__name__)


def run_linkage(
    parsed_df: pl.DataFrame,
    patients: pl.DataFrame,
    re_table: pl.DataFrame,
    phase0: pl.DataFrame,
) -> pl.DataFrame:
    sub_ids = parsed_df["submission_id"].to_list()
    names   = parsed_df["identity_name"].to_list()
    dobs    = parsed_df["identity_dob"].to_list()
    sexes   = parsed_df["identity_sex"].to_list()

    result_sub_ids:   list[int] = []
    result_pronts:    list[str] = []
    result_decisions: list[str] = []
    result_scores:    list[int] = []
    result_phases:    list[str] = []

    for sub_id, raw_name, raw_dob, raw_sex in zip(sub_ids, names, dobs, sexes):
        query  = _Query(sub_id, raw_name or "", raw_dob or "", raw_sex or "")
        result = match_record(query, patients, re_table, phase0)
        result_sub_ids.append(sub_id)
        result_pronts.append(result["prontuario"] or "")
        result_decisions.append(result["decision"])
        result_scores.append(result["score"])
        result_phases.append(result["phase"])

    return pl.DataFrame({
        "submission_id": pl.Series(result_sub_ids, dtype=pl.Int64),
        "prontuario":    pl.Series(result_pronts,    dtype=pl.Utf8),
        "decision":      pl.Series(result_decisions, dtype=pl.Utf8),
        "score":         pl.Series(result_scores,    dtype=pl.Int32),
        "phase":         pl.Series(result_phases,    dtype=pl.Utf8),
    })


def run(args: argparse.Namespace) -> None:
    base    = resolve_base_dir(args.base)
    run_tag = args.run_tag or datetime.now().strftime("%Y%m%d_%H%M%S")

    parsed_path   = resolve_input_path(base, args.parsed_input,   must_exist=True)
    records_path  = resolve_input_path(base, args.records_input,  must_exist=True)
    mapping_root  = resolve_input_path(base, args.mapping_root,   must_exist=True)
    righteye_path = resolve_input_path(base, args.righteye_input, must_exist=True)
    out_dir       = resolve_output_dir(base, args.output, create=True)

    parsed_df = pl.read_parquet(str(parsed_path))
    logger.info("Loaded parsed: %d submissions", len(parsed_df))

    patients = build_patient_table(records_path, mapping_root)
    re_table = build_righteye_table(righteye_path)
    phase0   = _phase0_prontuario(patients, re_table)
    logger.info("Tables: patients=%d | RightEye=%d | phase0=%d",
                len(patients), len(re_table), len(phase0))

    linkage_df = run_linkage(parsed_df, patients, re_table, phase0)

    n_unique   = linkage_df.filter(pl.col("decision") == "MATCH_UNIQUE").height
    n_multiple = linkage_df.filter(pl.col("decision") == "MATCH_MULTIPLE").height
    n_none     = linkage_df.filter(pl.col("decision") == "NO_MATCH").height
    logger.info("Linkage: total=%d | MATCH_UNIQUE=%d | MATCH_MULTIPLE=%d | NO_MATCH=%d",
                len(parsed_df), n_unique, n_multiple, n_none)

    # Join back to parsed to produce the full linked file
    linked_df = parsed_df.join(
        linkage_df.filter(pl.col("decision") == "MATCH_UNIQUE")
                  .select(["submission_id", "prontuario", "score", "phase"]),
        on="submission_id",
        how="inner",
    )

    out_base = out_dir / f"linked_{run_tag}"
    linked_df.write_parquet(str(out_base.with_suffix(".parquet")))
    linked_df.write_csv(str(out_base.with_suffix(".csv")))
    logger.info("Written: %s (.parquet + .csv) — %d rows", out_base.stem, len(linked_df))
    logger.info("Revise %s.csv before running step3_features if needed.", out_base.stem)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase 2: record linkage → linked parquet/csv.")
    p.add_argument("--base",            default=".")
    p.add_argument("--parsed-input",    required=True,
                   help="Output of step1_parse (parsed_<tag>.parquet)")
    p.add_argument("--records-input",   default="patients-data/medical_records_history.parquet")
    p.add_argument("--mapping-root",    default="output/patients")
    p.add_argument("--righteye-input",  default="patients-data/data_right_eye.parquet")
    p.add_argument("--output",          default="output/questionnaire")
    p.add_argument("--run-tag",         default=None)
    return p


if __name__ == "__main__":
    configure_logging()
    run(build_parser().parse_args())
