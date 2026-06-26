"""Annotate patients_id_mapping with clinical data from medical_records_history.

Enriches every row in patients_id_mapping parquet files with three columns:

  - records_nome      : Nome from medical records
  - neurodivergencia  : Neurodivergencia field
  - laudo             : Laudo field (Sim/Nao)

Match strategy (in order):
  1. Prontuario exact match — mapping.prontuario == str(records.ID)
  2. Name prefix match     — one normalized name starts-with the other
                             (handles abbreviations: "izabelacsb" vs "izabelacecilia...")

Rows that cannot be matched are annotated with empty strings.

Outputs:
  - patients_id_mapping parquets are rewritten in-place with the three new columns
  - output/reports/annotation/annotation_audit_YYYYMMDD_HHMMSS.parquet
    (one row per unique patient_unique_id: match_method + annotated fields)
  - output/reports/annotation/unmatched_mapping_YYYYMMDD_HHMMSS.{parquet,csv}
    (mapping rows that could not be matched to any medical record)

Uses Polars + PyArrow (mapping is not a heavy dataset).
Medical records file is small enough to load fully in memory.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

import polars as pl
import pyarrow.parquet as pq

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.id_utils import match_name_prefix, normalize_name, normalize_prontuario, parse_patient_unique_id
from common.logging_utils import configure_logging
from common.path_utils import resolve_base_dir, resolve_input_path, resolve_output_dir
from common.value_utils import parse_bool_field


logger = logging.getLogger(__name__)

MAPPING_PATTERNS = ["patients_id_mapping-*.parquet"]

# String annotation columns written to patients_id_mapping
ANNOTATE_COLS_STR = ["records_nome", "neurodivergencia", "laudo", "sexo"]
# Boolean annotation columns (Sim/Não → bool)
ANNOTATE_COLS_BOOL = ["erg", "eye_tracking", "fdt", "sensibilidade_contraste", "daltonismo"]
# All annotation columns
ANNOTATE_COLS = ANNOTATE_COLS_STR + ANNOTATE_COLS_BOOL

# Source column names in medical_records_history
_RECORDS_STR_SOURCE: dict[str, str] = {
    "records_nome": "Nome",
    "neurodivergencia": "Neurodivergencia",
    "laudo": "Laudo",
    "sexo": "Sexo",
}
_RECORDS_BOOL_SOURCE: dict[str, str] = {
    "erg": "ERG",
    "eye_tracking": "Eye tracking",
    "fdt": "FDT",
    "sensibilidade_contraste": "Sensibilidade ao contraste",
    "daltonismo": "Daltonismo",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _find_mapping_files(root: Path) -> list[Path]:
    matches: list[Path] = []
    for pattern in MAPPING_PATTERNS:
        matches.extend(root.rglob(pattern))
    return sorted({p.resolve() for p in matches if p.exists()})


def _read_parquet_polars(path: Path) -> pl.DataFrame:
    return pl.read_parquet(list(path.rglob("*.parquet")) if path.is_dir() else path)


def _write_parquet_inplace(path: Path, df: pl.DataFrame) -> None:
    table = df.to_arrow()
    if path.is_dir():
        tmp = path.parent / (path.name + ".annotate_tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        pq.write_to_dataset(table, root_path=str(tmp))
        shutil.rmtree(path)
        tmp.rename(path)
    else:
        tmp = path.with_suffix(".annotate_tmp.parquet")
        pq.write_table(table, str(tmp))
        path.unlink()
        tmp.rename(path)


# ---------------------------------------------------------------------------
# build lookup from records
# ---------------------------------------------------------------------------

def _build_lookup(records: pl.DataFrame) -> tuple[dict[str, dict], dict[str, dict]]:
    """Returns (by_prontuario, by_name). Values: all ANNOTATE_COLS fields."""
    by_prontuario: dict[str, dict] = {}
    by_name: dict[str, dict] = {}

    for row in records.to_dicts():
        entry: dict = {
            dest: str(row.get(src) or "").strip()
            for dest, src in _RECORDS_STR_SOURCE.items()
        }
        for dest_col, src_col in _RECORDS_BOOL_SOURCE.items():
            entry[dest_col] = parse_bool_field(row.get(src_col))
        nome = entry["records_nome"]

        pront = normalize_prontuario(row.get("ID", ""))
        if pront:
            by_prontuario[pront] = entry

        norm_nome = normalize_name(nome)
        if norm_nome:
            by_name[norm_nome] = entry

    return by_prontuario, by_name


def _build_metadata_name_lookup(metadata_df: pl.DataFrame) -> dict[str, str]:
    """Returns {patient_unique_id -> normalized nome_paciente} from consolidated_metadata."""
    pid_col = "patient_unique_id"
    nome_col = "nome_paciente"
    if pid_col not in metadata_df.columns or nome_col not in metadata_df.columns:
        return {}
    lookup: dict[str, str] = {}
    for row in metadata_df.select([pid_col, nome_col]).unique(subset=[pid_col]).to_dicts():
        pid = str(row.get(pid_col) or "").strip()
        nome = normalize_name(str(row.get(nome_col) or ""))
        if pid and nome:
            lookup[pid] = nome
    return lookup


def _match_row(
    prontuario: str,
    nome_completo: str,
    patient_unique_id: str,
    by_prontuario: dict,
    by_name: dict,
    metadata_names: dict[str, str] | None = None,
) -> tuple[dict | None, str]:
    # 1. prontuario from dedicated column
    pront = normalize_prontuario(prontuario)

    # 2. fallback: extract prontuario from patient_unique_id
    if not pront and patient_unique_id:
        extracted_pront, _, _, _ = parse_patient_unique_id(patient_unique_id)
        pront = normalize_prontuario(extracted_pront or "")

    if pront and pront in by_prontuario:
        return by_prontuario[pront], "prontuario"

    # 3. name match using mapping's nome_completo
    norm_nome = normalize_name(nome_completo)
    if norm_nome:
        entry, method = match_name_prefix(norm_nome, by_name)
        if entry is not None:
            return entry, method

    # 4. fallback: try nome_paciente from consolidated_metadata for this patient_unique_id
    if metadata_names and patient_unique_id:
        alt_nome = metadata_names.get(patient_unique_id)
        if alt_nome and alt_nome != norm_nome:
            entry, method = match_name_prefix(alt_nome, by_name)
            if entry is not None:
                return entry, "name_metadata"

    return None, "not_found"


# ---------------------------------------------------------------------------
# annotate a single mapping file
# ---------------------------------------------------------------------------

def _resolve_sexo(manual: str, from_records: str, pid: str) -> str:
    """Records value prevails when present; falls back to manual; logs divergence."""
    manual_norm = manual.strip().lower()
    records_norm = from_records.strip().lower()
    if manual_norm and records_norm and manual_norm != records_norm:
        logger.warning(
            "sexo divergence pid=%s manual=%r records=%r — using records value",
            pid, manual, from_records,
        )
    if from_records.strip():
        return from_records
    return manual


def _annotate_file(
    path: Path,
    by_prontuario: dict,
    by_name: dict,
    dry_run: bool,
    metadata_names: dict[str, str] | None = None,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Returns (full_df_annotated, audit_df).
    audit_df has one row per unique patient_unique_id with match_method + annotated cols.
    """
    df = _read_parquet_polars(path)
    logger.info("%s: %d rows", path.name, len(df))

    prontuario_col = "prontuario" if "prontuario" in df.columns else None
    nome_col = "nome_completo" if "nome_completo" in df.columns else None
    pid_col = "patient_unique_id" if "patient_unique_id" in df.columns else None
    existing_sexo_col = "sexo" if "sexo" in df.columns else None

    str_cols: dict[str, list[str]] = {c: [] for c in ANNOTATE_COLS_STR}
    bool_cols: dict[str, list[bool | None]] = {c: [] for c in ANNOTATE_COLS_BOOL}
    match_methods: list[str] = []

    for row in df.to_dicts():
        pront = str(row.get(prontuario_col) or "") if prontuario_col else ""
        nome = str(row.get(nome_col) or "") if nome_col else ""
        pid = str(row.get(pid_col) or "") if pid_col else ""
        entry, method = _match_row(pront, nome, pid, by_prontuario, by_name, metadata_names)

        for col in ANNOTATE_COLS_STR:
            if col == "sexo":
                manual = str(row.get(existing_sexo_col) or "") if existing_sexo_col else ""
                from_records = str(entry.get("sexo") or "") if entry else ""
                str_cols[col].append(_resolve_sexo(manual, from_records, pid))
            else:
                str_cols[col].append(str(entry[col]) if entry else "")

        for col in ANNOTATE_COLS_BOOL:
            bool_cols[col].append(entry[col] if entry else None)
        match_methods.append(method)

    # drop annotation cols if already present (re-run safety)
    for col in ANNOTATE_COLS:
        if col in df.columns:
            df = df.drop(col)

    df = df.with_columns(
        [pl.Series(col, vals, dtype=pl.Utf8) for col, vals in str_cols.items()]
        + [pl.Series(col, vals, dtype=pl.Boolean) for col, vals in bool_cols.items()]
    )

    audit_rows = df.with_columns(pl.Series("match_method", match_methods, dtype=pl.Utf8))
    id_cols = ["patient_unique_id"] if "patient_unique_id" in audit_rows.columns else []
    if id_cols:
        audit_rows = audit_rows.unique(subset=["patient_unique_id"], keep="first")
    audit_rows = audit_rows.select(id_cols + ANNOTATE_COLS + ["match_method"])

    by_method: dict[str, int] = {}
    for m in match_methods:
        by_method[m] = by_method.get(m, 0) + 1
    logger.info(
        "%s: prontuario=%d  name_exact=%d  name_prefix=%d  name_metadata=%d  not_found=%d",
        path.name,
        by_method.get("prontuario", 0),
        by_method.get("name_exact", 0),
        by_method.get("name_prefix", 0),
        by_method.get("name_metadata", 0),
        by_method.get("not_found", 0),
    )

    if not dry_run:
        _write_parquet_inplace(path, df)

    return df, audit_rows


# ---------------------------------------------------------------------------
# main run
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> None:
    base_dir = resolve_base_dir(args.base)
    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    records_path = resolve_input_path(base_dir, args.records_input, must_exist=True)
    mapping_root = resolve_input_path(base_dir, args.mapping_root, must_exist=True)
    reports_dir = resolve_output_dir(base_dir, args.reports_output, create=True)

    logger.info("Medical records source: %s", records_path)
    records_df = _read_parquet_polars(records_path)
    logger.info("Records loaded: %d rows", len(records_df))

    by_prontuario, by_name = _build_lookup(records_df)
    logger.info(
        "Lookup built: %d by-prontuario  %d by-name",
        len(by_prontuario), len(by_name),
    )

    metadata_names: dict[str, str] | None = None
    if getattr(args, "metadata_input", None):
        metadata_path = resolve_input_path(base_dir, args.metadata_input, must_exist=True)
        logger.info("Metadata source (name fallback): %s", metadata_path)
        metadata_df = _read_parquet_polars(metadata_path)
        metadata_names = _build_metadata_name_lookup(metadata_df)
        logger.info("Metadata name lookup built: %d unique patient_unique_ids", len(metadata_names))

    mapping_files = _find_mapping_files(mapping_root)
    if not mapping_files:
        logger.warning("No patients_id_mapping parquet files found under %s", mapping_root)
        return

    logger.info("Mapping files found (%d):", len(mapping_files))
    for mf in mapping_files:
        logger.info("  %s", mf)

    all_audit: list[pl.DataFrame] = []

    for path in mapping_files:
        logger.info("Annotating %s", path)
        _, audit_df = _annotate_file(path, by_prontuario, by_name, args.dry_run, metadata_names)
        all_audit.append(audit_df)

    if all_audit:
        combined_audit = pl.concat(all_audit)
        if "patient_unique_id" in combined_audit.columns:
            combined_audit = combined_audit.unique(subset=["patient_unique_id"], keep="first")

        audit_path = reports_dir / f"annotation_audit_{run_tag}.parquet"
        unmatched = combined_audit.filter(pl.col("match_method") == "not_found")
        unmatched_parquet = reports_dir / f"unmatched_mapping_{run_tag}.parquet"
        unmatched_csv = reports_dir / f"unmatched_mapping_{run_tag}.csv"

        if not args.dry_run:
            combined_audit.write_parquet(str(audit_path))
            logger.info("Annotation audit written: %s (%d unique IDs)", audit_path, len(combined_audit))

            if len(unmatched) > 0:
                unmatched.write_parquet(str(unmatched_parquet))
                unmatched.write_csv(str(unmatched_csv))
                logger.info("Unmatched report: %s (%d rows)", unmatched_parquet, len(unmatched))
            else:
                logger.info("All mapping rows matched — no unmatched report written.")
        else:
            logger.info(
                "[dry-run] Would write audit (%d rows), unmatched (%d rows) to %s",
                len(combined_audit), len(unmatched), reports_dir,
            )

    method_totals: dict[str, int] = {}
    if all_audit:
        for df in all_audit:
            for m in df["match_method"].to_list():
                method_totals[m] = method_totals.get(m, 0) + 1

    logger.info(
        "ANNOTATE complete: prontuario=%d  name_exact=%d  name_prefix=%d  name_metadata=%d  not_found=%d",
        method_totals.get("prontuario", 0),
        method_totals.get("name_exact", 0),
        method_totals.get("name_prefix", 0),
        method_totals.get("name_metadata", 0),
        method_totals.get("not_found", 0),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Annotate patients_id_mapping parquets with clinical data from medical_records_history. "
            "Adds records_nome, neurodivergencia and laudo columns in-place. "
            "Writes annotation_audit and unmatched_mapping reports."
        )
    )
    parser.add_argument("--base", default=".", help="Base directory")
    parser.add_argument(
        "--records-input",
        default="patients-data/medical_records_history.parquet",
        help="Path to medical_records_history parquet",
    )
    parser.add_argument(
        "--mapping-root",
        default="output/patients",
        help="Root directory containing patients_id_mapping parquet files",
    )
    parser.add_argument(
        "--reports-output",
        default="output/reports/annotation",
        help="Directory for annotation audit and unmatched reports",
    )
    parser.add_argument(
        "--metadata-input",
        default=None,
        help="Optional path to consolidated_metadata parquet for name fallback lookup",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be annotated without writing any files",
    )
    return parser
