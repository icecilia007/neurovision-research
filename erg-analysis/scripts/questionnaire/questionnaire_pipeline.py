"""End-to-end questionnaire processing pipeline.

Phases:
  1. Parse      — questionnaire JSON → flat Polars DataFrame
  2. Link       — DataFrame → prontuario per submission via record_linkage
  3. Features   — join responses + prontuario, drop identity PII
  4. Anonymize  — prontuario → patient_unique_id (bcrypt hash), drop remaining PII

Outputs (all under output/questionnaire/<questionnaire_id>/):
  linked_<tag>.parquet/.csv      — full parsed data + prontuario (MATCH_UNIQUE only)
  features_<tag>.parquet/.csv    — clinical features + prontuario (pre-anonymization)
  anonymous_<tag>.parquet/.csv   — fully anonymized dataset
  linkage_report_<tag>.txt       — quantitative audit trail

Usage:
  python -m scripts.questionnaire.questionnaire_pipeline \\
      --questionnaire-input cardiff-questionnaire-responses/questionnaire_3_report_05-30-2026.json \\
      --base .
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
from common.questionnaire_feature_builder import build_feature_dataset
from common.questionnaire_parser import parse_questionnaire_file
from common.patient_lookup import build_patient_table, build_righteye_table
from questionnaire.record_linkage import (
    _Query,
    _phase0_prontuario,
    match_record,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# I/O helper
# ---------------------------------------------------------------------------

def _write(df: pl.DataFrame, base: Path) -> None:
    if df.is_empty():
        logger.warning("Empty DataFrame — skipping write to %s", base.stem)
        return
    df.write_parquet(str(base.with_suffix(".parquet")))
    df.write_csv(str(base.with_suffix(".csv")))
    logger.info("Written: %s (.parquet + .csv) — %d rows", base.stem, len(df))


# ---------------------------------------------------------------------------
# Phase 2: linkage — iterates over identity Series without full to_dicts()
# ---------------------------------------------------------------------------

def _run_linkage(
    parsed_df: pl.DataFrame,
    patients: pl.DataFrame,
    re_table: pl.DataFrame,
    phase0: pl.DataFrame,
) -> pl.DataFrame:
    """Run match_record for every submission in parsed_df.

    Reads only the three identity columns from the DataFrame instead of
    materialising the entire frame as Python dicts — avoids the O(N*cols)
    memory cost of to_dicts() for wide DataFrames.

    Returns DataFrame: [submission_id, prontuario, decision, score, phase]
    """
    sub_ids   = parsed_df["submission_id"].to_list()
    names     = parsed_df["identity_name"].to_list()
    dobs      = parsed_df["identity_dob"].to_list()
    sexes     = parsed_df["identity_sex"].to_list()

    result_sub_ids:   list[int]  = []
    result_pronts:    list[str]  = []
    result_decisions: list[str]  = []
    result_scores:    list[int]  = []
    result_phases:    list[str]  = []

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


# ---------------------------------------------------------------------------
# main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    questionnaire_path: Path,
    records_path: Path,
    mapping_root: Path,
    righteye_path: Path,
    id_map_dir: Path,
    output_base: Path,
    anon_datasets_dir: Path,
    run_tag: str,
    dry_run: bool,
) -> None:
    # ---- Phase 1: parse ----
    logger.info("Phase 1 — Parsing: %s", questionnaire_path.name)
    parsed_df = parse_questionnaire_file(questionnaire_path)
    total_submissions = len(parsed_df)

    q_id    = parsed_df["questionnaire_id"][0]  if "questionnaire_id"    in parsed_df.columns else "unknown"
    q_title = parsed_df["questionnaire_title"][0] if "questionnaire_title" in parsed_df.columns else ""
    logger.info("Questionnaire id=%s title='%s' | submissions=%d", q_id, q_title, total_submissions)

    # Intermediate outputs (linked, features, report) per questionnaire
    out_dir = resolve_output_dir(output_base, str(q_id), create=not dry_run)
    # Anonymized output follows project convention: output/data/anonymized/datasets/
    anon_out_dir = anon_datasets_dir
    if not dry_run:
        anon_out_dir.mkdir(parents=True, exist_ok=True)

    # ---- Phase 2: linkage ----
    logger.info("Phase 2 — Building patient tables")
    patients = build_patient_table(records_path, mapping_root)
    re_table = build_righteye_table(righteye_path)
    phase0   = _phase0_prontuario(patients, re_table)
    logger.info("Tables: patients=%d | RightEye=%d | phase0=%d",
                len(patients), len(re_table), len(phase0))

    logger.info("Phase 2 — Running linkage")
    linkage_df = _run_linkage(parsed_df, patients, re_table, phase0)

    decision_counts = (
        linkage_df.group_by("decision").len().sort("decision")
    )
    n_unique   = linkage_df.filter(pl.col("decision") == "MATCH_UNIQUE").height
    n_multiple = linkage_df.filter(pl.col("decision") == "MATCH_MULTIPLE").height
    n_none     = linkage_df.filter(pl.col("decision") == "NO_MATCH").height
    logger.info(
        "Linkage: total=%d | MATCH_UNIQUE=%d | MATCH_MULTIPLE=%d | NO_MATCH=%d",
        total_submissions, n_unique, n_multiple, n_none,
    )

    if dry_run:
        logger.info("[dry-run] Skipping file writes.")
        return

    # ---- Phase 3: linked (full data + prontuario, no PII drop yet) ----
    linked_df = (
        parsed_df
        .join(
            linkage_df.filter(pl.col("decision") == "MATCH_UNIQUE")
                      .select(["submission_id", "prontuario", "score", "phase"]),
            on="submission_id",
            how="inner",
        )
    )
    _write(linked_df, out_dir / f"linked_{run_tag}")

    # ---- Phase 3: feature dataset ----
    logger.info("Phase 3 — Building feature dataset")
    feature_df = build_feature_dataset(parsed_df, linkage_df, keep_unmatched=False)
    _write(feature_df, out_dir / f"features_{run_tag}")

    # ---- Phase 4: anonymization ----
    logger.info("Phase 4 — Anonymizing")
    anon_audit: dict = {}
    try:
        id_map = load_id_map(id_map_dir=id_map_dir)
        anon_df, anon_audit = anonymize_dataset(feature_df, id_map)
        # Save to project-standard anonymized datasets directory
        q_slug = str(q_id).lower().replace(" ", "_")
        _write(anon_df, anon_out_dir / f"questionnaire_{q_slug}_{run_tag}")
    except FileNotFoundError as exc:
        logger.warning("Anonymization skipped — id_map not found: %s", exc)
        logger.warning("Run the ERG hashing pipeline first to generate the id_map.")

    # ---- Quantitative audit report (A16) ----
    report_lines = [
        f"Questionnaire Pipeline Report — {run_tag}",
        f"File            : {questionnaire_path.name}",
        f"Title           : {q_title}",
        "",
        "=== Linkage ===",
        f"  Submissions total   : {total_submissions}",
        f"  MATCH_UNIQUE        : {n_unique}",
        f"  MATCH_MULTIPLE      : {n_multiple}",
        f"  NO_MATCH            : {n_none}",
        f"  Lost in linkage     : {total_submissions - n_unique}",
        "",
        "=== Features ===",
        f"  Rows in feature_df  : {len(feature_df)}",
        f"  Cols in feature_df  : {len(feature_df.columns)}",
    ]

    if anon_audit:
        report_lines += [
            "",
            "=== Anonymization ===",
            f"  Input rows          : {anon_audit.get('input_rows', '?')}",
            f"  Matched to id_map   : {anon_audit.get('matched_rows', '?')}",
            f"  Unmatched (dropped) : {anon_audit.get('unmatched_rows', '?')}",
            f"  Output rows         : {anon_audit.get('output_rows', '?')}",
            f"  Total lost          : {total_submissions - anon_audit.get('output_rows', 0)}",
        ]

    report_path = out_dir / f"linkage_report_{run_tag}.txt"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    logger.info("Report written: %s", report_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="End-to-end questionnaire pipeline: parse → link → features → anonymize."
    )
    p.add_argument("--base",                 default=".")
    p.add_argument("--questionnaire-input",  required=True,
                   help="Path to questionnaire JSON (nested API or legacy flat format)")
    p.add_argument("--records-input",        default="patients-data/medical_records_history.parquet")
    p.add_argument("--mapping-root",         default="output/patients")
    p.add_argument("--righteye-input",       default="patients-data/data_right_eye.parquet")
    p.add_argument("--id-map-dir",           default="output/data/anonymized",
                   help="Directory containing id_map_*.parquet (searched recursively)")
    p.add_argument("--output",               default="output/questionnaire",
                   help="Directory for intermediate outputs (linked, features, report)")
    p.add_argument("--anon-datasets-dir",    default="output/data/anonymized/datasets",
                   help="Directory for anonymized output — must match project convention")
    p.add_argument("--dry-run",              action="store_true")
    return p


def run(args: argparse.Namespace) -> None:
    base    = resolve_base_dir(args.base)
    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    run_pipeline(
        questionnaire_path = resolve_input_path(base, args.questionnaire_input, must_exist=True),
        records_path       = resolve_input_path(base, args.records_input,       must_exist=True),
        mapping_root       = resolve_input_path(base, args.mapping_root,        must_exist=True),
        righteye_path      = resolve_input_path(base, args.righteye_input,      must_exist=True),
        id_map_dir         = base / args.id_map_dir,
        output_base        = resolve_output_dir(base, args.output,            create=not args.dry_run),
        anon_datasets_dir  = resolve_output_dir(base, args.anon_datasets_dir, create=not args.dry_run),
        run_tag            = run_tag,
        dry_run            = args.dry_run,
    )


if __name__ == "__main__":
    configure_logging()
    run(build_parser().parse_args())
