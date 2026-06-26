"""Multi-source record linkage pipeline.

Links Cardiff Questionnaire respondents to:
  - patients_id_mapping + medical_records_history  (ERG patient base)
  - RightEye assessment data

Matching hierarchy:
  Phase 0 — Prontuario exact match  (RightEye.PATIENT_ID == mapping.prontuario)
  Phase 1 — Birth year blocking     (from questionnaire DOB)
  Phase 2 — Gender auxiliary filter (never eliminatory)
  Phase 3 — Name matching           (exact → variation lookup → token scoring)
  Phase 4 — Fuzzy matching          (RapidFuzz cdist, only on pre-filtered pool)

NOTE: TEST_DATE is NEVER compared to questionnaire DOB.
      TEST_DATE is only used to estimate a birth year range when the RightEye
      record provides AGE but no birth date.

Fuzzy metrics: ratio, partial_ratio, token_sort_ratio, token_set_ratio.
All four computed ONCE via cdist per pool; individual values stored in detail
dicts and reused throughout — no recalculation.

Outputs:
  linkage_results_<tag>.parquet/.csv      — all rows (one per submission)
  linkage_confirmed_<tag>.parquet/.csv    — MATCH_UNIQUE (submission → prontuario)
  ambiguous_<tag>.parquet/.csv            — MATCH_MULTIPLE candidates (top-5)
  not_found_<tag>.parquet/.csv            — NO_MATCH with best candidate detail
  linkage_explain_<tag>.csv               — every candidate evaluated (explainability)
  linkage_report_<tag>.txt               — summary counts by phase
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.date_utils import extract_birth_year
from common.id_utils import normalize_name
from common.logging_utils import configure_logging
from common.name_utils import build_name_signatures, norm_sex, tokens_from_raw
from common.path_utils import resolve_base_dir, resolve_input_path, resolve_output_dir
from common.patient_lookup import build_patient_table, build_righteye_table

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# scoring constants
# ---------------------------------------------------------------------------

_SC_PRONTUARIO   = 100
_SC_NAME_EXACT   = 50
_SC_FUZZY_95     = 45
_SC_FUZZY_90     = 35
_SC_FUZZY_85     = 25
_SC_BIRTH_YEAR   = 20
_SC_GENDER       = 10
_SC_FIRST_TOKEN  = 15
_SC_LAST_TOKEN   = 15
_SC_SHARED_TOKEN = 5    # per token, max 3

_THRESHOLD_ACCEPT = 70
_THRESHOLD_REVIEW = 35

_QS_ID   = "ID da Submissão"
_QS_NAME = "QS1: Nome"
_QS_DOB  = "QS2: Data de nascimento: __ / __ / ____"
_QS_SEX  = "QS4: Sexo"


# ---------------------------------------------------------------------------
# RapidFuzz — all four metrics, one cdist call per metric, computed ONCE
# ---------------------------------------------------------------------------

def _compute_all_fuzzy(
    query_norm: str,
    names: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (ratio, partial_ratio, token_sort, token_set, best) arrays.

    All five arrays have shape (n,) where n == len(names).
    Computed in a single pass; callers store and reuse — never recalculate.
    """
    n = len(names)
    zeros = np.zeros(n, dtype=np.int32)
    if not query_norm or not names:
        return zeros, zeros, zeros, zeros, zeros

    try:
        from rapidfuzz.process import cdist as _cdist
        from rapidfuzz import fuzz as _fuzz
    except ImportError:
        logger.warning("rapidfuzz not installed — fuzzy scoring unavailable")
        return zeros, zeros, zeros, zeros, zeros

    r   = _cdist([query_norm], names, scorer=_fuzz.ratio)[0].astype(np.int32)
    pr  = _cdist([query_norm], names, scorer=_fuzz.partial_ratio)[0].astype(np.int32)
    ts  = _cdist([query_norm], names, scorer=_fuzz.token_sort_ratio)[0].astype(np.int32)
    tse = _cdist([query_norm], names, scorer=_fuzz.token_set_ratio)[0].astype(np.int32)
    best = np.maximum.reduce([r, pr, ts, tse])
    return r, pr, ts, tse, best


def _score_from_best(best: int) -> int:
    if best >= 95:
        return _SC_FUZZY_95
    if best >= 90:
        return _SC_FUZZY_90
    if best >= 85:
        return _SC_FUZZY_85
    return 0


# ---------------------------------------------------------------------------
# classification
# ---------------------------------------------------------------------------

def _classify(
    query_norm: str,
    query_tokens: list[str],
    cand_norm: str,
    ratio: int,
    partial_ratio: int,
    token_sort: int,
    token_set: int,
    birth_year_match: bool,
    gender_match: bool,
    first_name_match: bool,
    last_name_match: bool,
) -> str:
    """Assign a single classification label to a (query, candidate) pair."""
    if not cand_norm:
        return "NO_CANDIDATE"
    if query_norm == cand_norm:
        return "EXACT_NAME"

    cand_tokens = set(tokens_from_raw(cand_norm))
    q_token_set = set(query_tokens)

    # All query tokens present in candidate → abbreviation or partial
    if q_token_set and q_token_set.issubset(cand_tokens):
        return "PARTIAL_NAME"

    # Candidate looks like first_name + initials pattern (e.g. "izabelacsb")
    # detected when partial_ratio is high but ratio is low
    if partial_ratio >= 85 and ratio < 70:
        return "NAME_ABBREVIATION"

    if first_name_match and not last_name_match and len(query_tokens) >= 2:
        return "FIRST_NAME_ONLY"

    if last_name_match and not first_name_match and len(query_tokens) >= 2:
        return "LAST_NAME_ONLY"

    if birth_year_match and gender_match and token_set < 70:
        return "YEAR_AND_GENDER_MATCH"

    # High token_set but names differ meaningfully → possible homonym
    if token_set >= 85 and (birth_year_match or gender_match):
        return "POSSIBLE_HOMONYM"

    # High ratio but below exact → possible typo / encoding issue
    if ratio >= 80:
        return "POSSIBLE_TYPO"

    if token_set >= 70 or partial_ratio >= 75:
        return "PARTIAL_NAME"

    return "LOW_CONFIDENCE"


def _build_reasons(
    detail: dict,
    ratio: int,
    partial_ratio: int,
    token_sort: int,
    token_set: int,
) -> list[str]:
    """Build human-readable reason list from the detail dict and fuzzy metrics."""
    reasons: list[str] = []
    motivos = detail.get("motivos", "")

    if "nome_exato" in motivos:
        reasons.append("nome_exato")
    if "fuzzy=" in motivos:
        reasons.append(f"fuzzy_best={detail.get('fuzzy_best', 0)}")
    if partial_ratio >= 90:
        reasons.append("partial_ratio_alto")
    if token_set >= 85:
        reasons.append("token_set_alto")
    if token_sort >= 85:
        reasons.append("token_sort_alto")
    if detail.get("birth_year_match"):
        reasons.append("ano_nascimento_igual")
    if detail.get("gender_match"):
        reasons.append("sexo_igual")
    if detail.get("first_name_match"):
        reasons.append("primeiro_nome_igual")
    if detail.get("last_name_match"):
        reasons.append("sobrenome_igual")
    if "nome_abreviado" in motivos:
        reasons.append("nome_abreviado")
    if "tokens_compartilhados" in motivos:
        reasons.append("tokens_compartilhados")

    return reasons


# ---------------------------------------------------------------------------
# query container
# ---------------------------------------------------------------------------

class _Query:
    __slots__ = (
        "sub_id", "raw_name", "query_norm", "tokens",
        "signatures", "first_token", "last_token",
        "birth_year", "query_sex",
    )

    def __init__(self, sub_id, raw_name: str, raw_dob: str, raw_sex: str) -> None:
        self.sub_id      = sub_id
        self.raw_name    = raw_name
        self.query_norm  = normalize_name(raw_name)
        self.tokens      = tokens_from_raw(raw_name)
        self.signatures  = build_name_signatures(raw_name)
        self.first_token = self.tokens[0] if self.tokens else ""
        self.last_token  = self.tokens[-1] if len(self.tokens) > 1 else ""
        self.birth_year  = extract_birth_year(raw_dob)
        self.query_sex   = norm_sex(raw_sex)


# ---------------------------------------------------------------------------
# Phase 0: prontuario join
# ---------------------------------------------------------------------------

def _phase0_prontuario(
    patients: pl.DataFrame,
    re_table: pl.DataFrame,
) -> pl.DataFrame:
    """Join patients_mapping ↔ RightEye on prontuario (once at startup)."""
    if re_table.is_empty() or patients.is_empty():
        return pl.DataFrame(schema={
            "prontuario": pl.Utf8, "patient_unique_id": pl.Utf8,
            "participant_id": pl.Utf8, "re_patient_id": pl.Utf8,
        })

    joined = (
        re_table
        .filter(pl.col("re_prontuario").is_not_null())
        .join(
            patients.select(["prontuario", "patient_unique_id"]),
            left_on="re_prontuario", right_on="prontuario", how="inner",
        )
        .select([
            pl.col("re_prontuario").alias("prontuario"),
            "patient_unique_id", "participant_id", "re_patient_id",
        ])
    )
    logger.info("Phase-0 prontuario join: %d RightEye rows linked to mapping", len(joined))
    return joined


# ---------------------------------------------------------------------------
# candidate pool builder
# ---------------------------------------------------------------------------

def _sex_filter_nonelim(pool: pl.DataFrame, sex_col: str, query_sex: str) -> pl.DataFrame:
    if not query_sex or sex_col not in pool.columns:
        return pool
    narrowed = pool.filter(pl.col(sex_col).str.to_lowercase().str.starts_with(query_sex))
    return narrowed if not narrowed.is_empty() else pool


def _build_name_filter_cond(sigs: set[str]) -> pl.Expr:
    cond = pl.col("norm_nome").is_in(list(sigs))
    for v in sigs:
        if len(v) >= 2:
            cond = cond | pl.col("norm_nome").str.starts_with(v)
    return cond


def _build_pool(
    query: _Query,
    patients: pl.DataFrame,
    re_table: pl.DataFrame,
) -> pl.DataFrame:
    if query.birth_year is not None:
        p_pool = patients.filter(pl.col("dob_year") == query.birth_year)
        r_pool = re_table.filter(
            (pl.col("birth_year_min") <= query.birth_year)
            & (pl.col("birth_year_max") >= query.birth_year)
        )
    else:
        p_pool = patients.clear()
        r_pool = re_table.clear()

    if p_pool.is_empty() and not patients.is_empty():
        p_pool = patients.filter(_build_name_filter_cond(query.signatures))
    if r_pool.is_empty() and not re_table.is_empty():
        r_pool = re_table.filter(_build_name_filter_cond(query.signatures))

    p_pool = _sex_filter_nonelim(p_pool, "sexo",      query.query_sex)
    r_pool = _sex_filter_nonelim(r_pool, "re_gender", query.query_sex)

    if not p_pool.is_empty():
        p_pool = p_pool.with_columns(pl.lit("patients_mapping").alias("_source"))
    if not r_pool.is_empty():
        r_pool = r_pool.with_columns(pl.lit("right_eye").alias("_source"))

    return pl.concat([p_pool, r_pool], how="diagonal_relaxed")


# ---------------------------------------------------------------------------
# per-candidate scoring
# ---------------------------------------------------------------------------

def _score_one(
    query: _Query,
    row: dict,
    ratio: int,
    partial_ratio: int,
    token_sort: int,
    token_set: int,
    fuzzy_best: int,
) -> tuple[int, dict]:
    """Score one candidate. All fuzzy values pre-computed; never recalculated."""
    score = 0
    reasons: list[str] = []

    cand_norm  = str(row.get("norm_nome") or "")
    cand_year  = row.get("dob_year")
    by_min     = row.get("birth_year_min")
    by_max     = row.get("birth_year_max")
    cand_sex   = str(row.get("sexo") or row.get("re_gender") or "")
    prontuario = str(row.get("prontuario") or row.get("re_prontuario") or "")
    source     = str(row.get("_source") or "")

    first_name_match = False
    last_name_match  = False

    if cand_norm:
        if query.query_norm == cand_norm:
            score += _SC_NAME_EXACT
            reasons.append("nome_exato")
            first_name_match = bool(query.first_token and cand_norm.startswith(query.first_token))
            last_name_match  = bool(query.last_token  and cand_norm.endswith(query.last_token))
        else:
            s = _score_from_best(fuzzy_best)
            if s:
                score += s
                reasons.append(f"fuzzy={fuzzy_best}")

            if query.first_token and cand_norm.startswith(query.first_token):
                score += _SC_FIRST_TOKEN
                reasons.append("primeiro_nome")
                first_name_match = True

            if query.last_token and cand_norm.endswith(query.last_token):
                score += _SC_LAST_TOKEN
                reasons.append("ultimo_sobrenome")
                last_name_match = True

            cand_tokens = set(tokens_from_raw(cand_norm))
            shared = {t for t in query.tokens if t in cand_tokens}
            contrib = min(len(shared), 3) * _SC_SHARED_TOKEN
            if contrib:
                score += contrib
                reasons.append(f"tokens_compartilhados={len(shared)}")

    birth_year_match = False
    if cand_year is not None and query.birth_year is not None:
        if int(cand_year) == query.birth_year:
            score += _SC_BIRTH_YEAR
            reasons.append(f"ano_nascimento={cand_year}")
            birth_year_match = True
    elif by_min is not None and by_max is not None and query.birth_year is not None:
        if int(by_min) <= query.birth_year <= int(by_max):
            score += _SC_BIRTH_YEAR
            reasons.append(f"ano_nascimento_range={by_min}-{by_max}")
            birth_year_match = True

    gender_match = False
    if query.query_sex and cand_sex:
        if norm_sex(cand_sex) == query.query_sex:
            score += _SC_GENDER
            reasons.append("sexo")
            gender_match = True

    classification = _classify(
        query.query_norm, query.tokens, cand_norm,
        ratio, partial_ratio, token_sort, token_set,
        birth_year_match, gender_match, first_name_match, last_name_match,
    )

    detail = {
        "prontuario":        prontuario,
        "candidate_source":  source,
        "nome":              str(row.get("records_nome") or row.get("re_full_name") or cand_norm),
        "score":             score,
        "ratio":             ratio,
        "partial_ratio":     partial_ratio,
        "token_sort_ratio":  token_sort,
        "token_set_ratio":   token_set,
        "fuzzy_best":        fuzzy_best,
        "birth_year_match":  birth_year_match,
        "gender_match":      gender_match,
        "first_name_match":  first_name_match,
        "last_name_match":   last_name_match,
        "classification":    classification,
        "motivos":           "|".join(reasons),
    }
    return score, detail


# ---------------------------------------------------------------------------
# real-time review logger
# ---------------------------------------------------------------------------

def _log_review(query: _Query, result: dict) -> None:
    """Print human-readable block to stdout for MATCH_MULTIPLE and NO_MATCH."""
    decision = result["decision"]
    sex_label = query.query_sex.upper() if query.query_sex else "?"

    if decision == "MATCH_MULTIPLE":
        logger.info("")
        logger.info("[REVIEW]")
        logger.info("Questionário: %s", query.raw_name)
        logger.info("Nascimento  : %s", query.birth_year or "?")
        logger.info("Sexo        : %s", sex_label)
        logger.info("")
        for idx, cand in enumerate(result["candidates"], 1):
            logger.info("Candidato #%d", idx)
            logger.info("  Nome............. %s", cand.get("nome", ""))
            logger.info("  Prontuário....... %s", cand.get("prontuario", ""))
            logger.info("  Fonte............ %s", cand.get("candidate_source", ""))
            logger.info("  Score............ %s", cand.get("score", 0))
            logger.info("  partial_ratio.... %s", cand.get("partial_ratio", 0))
            logger.info("  token_set........ %s", cand.get("token_set_ratio", 0))
            logger.info("  token_sort....... %s", cand.get("token_sort_ratio", 0))
            logger.info("  Ano nascimento... %s", "MATCH" if cand.get("birth_year_match") else "---")
            logger.info("  Sexo............. %s", "MATCH" if cand.get("gender_match") else "---")
            logger.info("  Primeiro nome.... %s", "MATCH" if cand.get("first_name_match") else "---")
            logger.info("  Classificação.... %s", cand.get("classification", ""))
            logger.info("")
        logger.info("Decisão: MATCH_MULTIPLE")
        logger.info("---")

    elif decision == "NO_MATCH":
        logger.info("")
        logger.info("[NO_MATCH]")
        logger.info("Questionário: %s", query.raw_name)
        logger.info("Nascimento  : %s", query.birth_year or "?")
        logger.info("Sexo        : %s", sex_label)
        best = result.get("best_candidate")
        if best:
            logger.info("")
            logger.info("Melhor candidato encontrado:")
            logger.info("  Nome............. %s", best.get("nome", ""))
            logger.info("  Prontuário....... %s", best.get("prontuario", ""))
            logger.info("  Score............ %s", best.get("score", 0))
            logger.info("  partial_ratio.... %s", best.get("partial_ratio", 0))
            logger.info("  token_set........ %s", best.get("token_set_ratio", 0))
            logger.info("  token_sort....... %s", best.get("token_sort_ratio", 0))
            logger.info("  Classificação.... %s", best.get("classification", ""))
            logger.info("")
            logger.info("Motivo: Score abaixo do threshold (melhor=%s, mínimo=%s)",
                        best.get("score", 0), _THRESHOLD_REVIEW)
        else:
            logger.info("Motivo: Nenhum candidato encontrado após bloqueio.")
        logger.info("---")


# ---------------------------------------------------------------------------
# main match function
# ---------------------------------------------------------------------------

def match_record(
    query: _Query,
    patients: pl.DataFrame,
    re_table: pl.DataFrame,
    phase0_links: pl.DataFrame,
) -> dict:
    """Match one questionnaire respondent.

    Returns:
      decision       : "MATCH_UNIQUE" | "MATCH_MULTIPLE" | "NO_MATCH"
      prontuario     : str | None
      score          : int
      phase          : str
      candidates     : list[dict]  (top-5, MATCH_MULTIPLE only)
      best_candidate : dict | None (NO_MATCH only — best candidate detail)
      all_scored     : list[dict]  (every candidate evaluated, for explain file)
    """
    raw_stripped = query.raw_name.strip()
    if raw_stripped.isdigit() and not phase0_links.is_empty():
        hit = phase0_links.filter(pl.col("prontuario") == raw_stripped)
        if len(hit) == 1:
            return {
                "decision":       "MATCH_UNIQUE",
                "prontuario":     hit["prontuario"][0],
                "score":          _SC_PRONTUARIO,
                "phase":          "phase0_prontuario",
                "candidates":     [],
                "best_candidate": None,
                "all_scored":     [],
            }

    pool = _build_pool(query, patients, re_table)

    if pool.is_empty():
        return {
            "decision":       "NO_MATCH",
            "prontuario":     None,
            "score":          0,
            "phase":          "phase1_blocking",
            "candidates":     [],
            "best_candidate": None,
            "all_scored":     [],
        }

    # Compute all four metrics ONCE — reused everywhere, never recalculated
    names = pool["norm_nome"].fill_null("").to_list()
    arr_r, arr_pr, arr_ts, arr_tse, arr_best = _compute_all_fuzzy(query.query_norm, names)

    scored: list[tuple[int, dict]] = []
    for i, row in enumerate(pool.to_dicts()):
        s, detail = _score_one(
            query, row,
            int(arr_r[i]), int(arr_pr[i]), int(arr_ts[i]), int(arr_tse[i]), int(arr_best[i]),
        )
        scored.append((s, detail))

    scored.sort(key=lambda x: x[0], reverse=True)
    all_scored = [d for _, d in scored]

    # When the same prontuario appears in both patients_mapping and RightEye,
    # it is the same patient — not a duplicate. Since the prontuario is what
    # we want to confirm, both entries produce the same answer. Keep only the
    # highest-scoring entry per prontuario so the decision logic sees one
    # candidate per real patient, not one per source.
    seen_pront: set[str] = set()
    deduped: list[tuple[int, dict]] = []
    for s, d in scored:
        pront = d.get("prontuario") or ""
        if pront and pront in seen_pront:
            continue
        if pront:
            seen_pront.add(pront)
        deduped.append((s, d))

    above_accept = [(s, d) for s, d in deduped if s >= _THRESHOLD_ACCEPT]
    above_review = [(s, d) for s, d in deduped if s >= _THRESHOLD_REVIEW]

    # MATCH_UNIQUE: all candidates above accept threshold point to the same
    # prontuario (or there is exactly one). The number of source rows does not
    # matter — what matters is whether the prontuario is unambiguous.
    accept_pronts = {d["prontuario"] for _, d in above_accept if d.get("prontuario")}
    if above_accept and len(accept_pronts) == 1:
        best_score, best_detail = above_accept[0]
        return {
            "decision":       "MATCH_UNIQUE",
            "prontuario":     best_detail["prontuario"],
            "score":          best_score,
            "phase":          _decide_phase(best_detail),
            "candidates":     [],
            "best_candidate": None,
            "all_scored":     all_scored,
        }

    review_pool = above_accept if above_accept else above_review
    if review_pool:
        top5 = [d for _, d in review_pool[:5]]
        return {
            "decision":       "MATCH_MULTIPLE",
            "prontuario":     None,
            "score":          review_pool[0][0],
            "phase":          "review",
            "candidates":     top5,
            "best_candidate": None,
            "all_scored":     all_scored,
        }

    best_detail = scored[0][1] if scored else {}
    return {
        "decision":       "NO_MATCH",
        "prontuario":     None,
        "score":          scored[0][0] if scored else 0,
        "phase":          "phase4_fuzzy",
        "candidates":     [],
        "best_candidate": best_detail,
        "all_scored":     all_scored,
    }


def _decide_phase(detail: dict) -> str:
    motivos = detail.get("motivos", "")
    if "nome_exato" in motivos:
        return "phase3_exact_name"
    if "fuzzy" in motivos:
        return "phase4_fuzzy"
    if "primeiro_nome" in motivos or "tokens_compartilhados" in motivos:
        return "phase3_token_name"
    if "ano_nascimento" in motivos:
        return "phase1_birth_year"
    return "phase3_name"


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _load_questionnaire(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write(df: pl.DataFrame, base: Path) -> None:
    if df.is_empty():
        return
    df.write_parquet(str(base.with_suffix(".parquet")))
    df.write_csv(str(base.with_suffix(".csv")))
    logger.info("Written: %s (.parquet + .csv) — %d rows", base.stem, len(df))


# ---------------------------------------------------------------------------
# main process
# ---------------------------------------------------------------------------

def _process(
    questionnaire_path: Path,
    records_path: Path,
    mapping_root: Path,
    righteye_path: Path,
    output_dir: Path,
    run_tag: str,
    dry_run: bool,
) -> None:
    responses = _load_questionnaire(questionnaire_path)
    logger.info("Questionnaire: %d responses", len(responses))

    patients  = build_patient_table(records_path, mapping_root)
    re_table  = build_righteye_table(righteye_path)
    phase0    = _phase0_prontuario(patients, re_table)
    logger.info("Tables: patients=%d | RightEye=%d | phase0_links=%d",
                len(patients), len(re_table), len(phase0))

    all_rows:       list[dict] = []
    confirmed_rows: list[dict] = []
    ambiguous_rows: list[dict] = []
    not_found_rows: list[dict] = []
    explain_rows:   list[dict] = []   # every candidate, every submission
    phase_counts:   dict[str, int] = {}

    for resp in responses:
        sub_id   = resp.get(_QS_ID)
        raw_name = resp.get(_QS_NAME, "") or ""
        raw_dob  = resp.get(_QS_DOB,  "") or ""
        raw_sex  = resp.get(_QS_SEX,  "") or ""

        query  = _Query(sub_id, raw_name, raw_dob, raw_sex)
        result = match_record(query, patients, re_table, phase0)

        decision = result["decision"]
        phase    = result["phase"]
        phase_counts[f"{decision}:{phase}"] = phase_counts.get(f"{decision}:{phase}", 0) + 1

        all_rows.append({
            "submission_id":      sub_id,
            "questionnaire_name": raw_name,
            "birth_year":         query.birth_year,
            "gender":             query.query_sex,
            "decision":           decision,
            "prontuario":         result["prontuario"],
            "score":              result["score"],
            "phase":              phase,
        })

        # --- explainability: one row per candidate evaluated ---
        for cand in result["all_scored"]:
            reasons = _build_reasons(
                cand,
                cand.get("ratio", 0),
                cand.get("partial_ratio", 0),
                cand.get("token_sort_ratio", 0),
                cand.get("token_set_ratio", 0),
            )
            explain_rows.append({
                "submission_id":            sub_id,
                "questionario_nome":        raw_name,
                "questionario_nascimento":  query.birth_year,
                "questionario_sexo":        query.query_sex,
                "candidate_nome":           cand.get("nome", ""),
                "candidate_prontuario":     cand.get("prontuario", ""),
                "score_final":              cand.get("score", 0),
                "partial_ratio":            cand.get("partial_ratio", 0),
                "token_set_ratio":          cand.get("token_set_ratio", 0),
                "token_sort_ratio":         cand.get("token_sort_ratio", 0),
                "birth_year_match":         cand.get("birth_year_match", False),
                "gender_match":             cand.get("gender_match", False),
                "first_name_match":         cand.get("first_name_match", False),
                "last_name_match":          cand.get("last_name_match", False),
                "classification":           cand.get("classification", ""),
                "decision":                 decision,
                "reasons":                  "|".join(reasons),
            })

        # --- decision-specific accumulators ---
        if decision == "MATCH_UNIQUE":
            confirmed_rows.append({
                "submission_id": sub_id,
                "prontuario":    result["prontuario"],
                "score":         result["score"],
            })

        elif decision == "MATCH_MULTIPLE":
            _log_review(query, result)
            for cand in result["candidates"]:
                reasons = _build_reasons(
                    cand,
                    cand.get("ratio", 0),
                    cand.get("partial_ratio", 0),
                    cand.get("token_sort_ratio", 0),
                    cand.get("token_set_ratio", 0),
                )
                ambiguous_rows.append({
                    "submission_id":            sub_id,
                    "questionnaire_name":       raw_name,
                    "questionnaire_birth_year": query.birth_year,
                    "questionnaire_gender":     query.query_sex,
                    "candidate_prontuario":     cand.get("prontuario", ""),
                    "candidate_name":           cand.get("nome", ""),
                    "candidate_source":         cand.get("candidate_source", ""),
                    "score":                    cand.get("score", 0),
                    "fuzzy_best":               cand.get("fuzzy_best", 0),
                    "partial_ratio":            cand.get("partial_ratio", 0),
                    "token_set_ratio":          cand.get("token_set_ratio", 0),
                    "token_sort_ratio":         cand.get("token_sort_ratio", 0),
                    "birth_year_match":         cand.get("birth_year_match", False),
                    "gender_match":             cand.get("gender_match", False),
                    "first_name_match":         cand.get("first_name_match", False),
                    "last_name_match":          cand.get("last_name_match", False),
                    "classification":           cand.get("classification", ""),
                    "reasons":                  "|".join(reasons),
                })

        else:  # NO_MATCH
            _log_review(query, result)
            best = result.get("best_candidate") or {}
            reasons = _build_reasons(
                best,
                best.get("ratio", 0),
                best.get("partial_ratio", 0),
                best.get("token_sort_ratio", 0),
                best.get("token_set_ratio", 0),
            ) if best else []
            not_found_rows.append({
                "submission_id":            sub_id,
                "questionnaire_name":       raw_name,
                "questionnaire_birth_year": query.birth_year,
                "questionnaire_gender":     query.query_sex,
                "best_score_reached":       result["score"],
                "best_candidate_name":      best.get("nome", ""),
                "best_candidate_prontuario": best.get("prontuario", ""),
                "partial_ratio":            best.get("partial_ratio", 0),
                "token_set_ratio":          best.get("token_set_ratio", 0),
                "token_sort_ratio":         best.get("token_sort_ratio", 0),
                "birth_year_match":         best.get("birth_year_match", False),
                "gender_match":             best.get("gender_match", False),
                "classification":           best.get("classification", "NO_CANDIDATE"),
                "reasons":                  "|".join(reasons),
            })

    # --- summary ---
    n_unique   = sum(1 for r in all_rows if r["decision"] == "MATCH_UNIQUE")
    n_multiple = sum(1 for r in all_rows if r["decision"] == "MATCH_MULTIPLE")
    n_none     = sum(1 for r in all_rows if r["decision"] == "NO_MATCH")

    logger.info("")
    logger.info("=== Linkage Summary ===")
    logger.info("  Total          : %d", len(responses))
    logger.info("  MATCH_UNIQUE   : %d", n_unique)
    logger.info("  MATCH_MULTIPLE : %d  (manual review)", n_multiple)
    logger.info("  NO_MATCH       : %d", n_none)
    logger.info("  By phase:")
    for k, v in sorted(phase_counts.items()):
        logger.info("    %-50s: %d", k, v)

    if dry_run:
        logger.info("[dry-run] outputs suppressed.")
        return

    # confirmed
    if confirmed_rows:
        _write(
            pl.DataFrame(confirmed_rows, schema={
                "submission_id": pl.Int64, "prontuario": pl.Utf8, "score": pl.Int32,
            }),
            output_dir / f"linkage_confirmed_{run_tag}",
        )

    # all results
    _write(
        pl.DataFrame(all_rows, schema={
            "submission_id": pl.Int64, "questionnaire_name": pl.Utf8,
            "birth_year": pl.Int32, "gender": pl.Utf8,
            "decision": pl.Utf8, "prontuario": pl.Utf8,
            "score": pl.Int32, "phase": pl.Utf8,
        }),
        output_dir / f"linkage_results_{run_tag}",
    )

    # ambiguous
    if ambiguous_rows:
        _write(
            pl.DataFrame(ambiguous_rows, schema={
                "submission_id": pl.Int64, "questionnaire_name": pl.Utf8,
                "questionnaire_birth_year": pl.Int32, "questionnaire_gender": pl.Utf8,
                "candidate_prontuario": pl.Utf8, "candidate_name": pl.Utf8,
                "candidate_source": pl.Utf8, "score": pl.Int32,
                "fuzzy_best": pl.Int32, "partial_ratio": pl.Int32,
                "token_set_ratio": pl.Int32, "token_sort_ratio": pl.Int32,
                "birth_year_match": pl.Boolean, "gender_match": pl.Boolean,
                "first_name_match": pl.Boolean, "last_name_match": pl.Boolean,
                "classification": pl.Utf8, "reasons": pl.Utf8,
            }),
            output_dir / f"ambiguous_{run_tag}",
        )

    # not found (enriched)
    if not_found_rows:
        _write(
            pl.DataFrame(not_found_rows, schema={
                "submission_id": pl.Int64, "questionnaire_name": pl.Utf8,
                "questionnaire_birth_year": pl.Int32, "questionnaire_gender": pl.Utf8,
                "best_score_reached": pl.Int32,
                "best_candidate_name": pl.Utf8, "best_candidate_prontuario": pl.Utf8,
                "partial_ratio": pl.Int32, "token_set_ratio": pl.Int32,
                "token_sort_ratio": pl.Int32,
                "birth_year_match": pl.Boolean, "gender_match": pl.Boolean,
                "classification": pl.Utf8, "reasons": pl.Utf8,
            }),
            output_dir / f"not_found_{run_tag}",
        )

    # explainability — CSV only (wide table, not needed as parquet)
    if explain_rows:
        explain_df = pl.DataFrame(explain_rows, schema={
            "submission_id": pl.Int64, "questionario_nome": pl.Utf8,
            "questionario_nascimento": pl.Int32, "questionario_sexo": pl.Utf8,
            "candidate_nome": pl.Utf8, "candidate_prontuario": pl.Utf8,
            "score_final": pl.Int32, "partial_ratio": pl.Int32,
            "token_set_ratio": pl.Int32, "token_sort_ratio": pl.Int32,
            "birth_year_match": pl.Boolean, "gender_match": pl.Boolean,
            "first_name_match": pl.Boolean, "last_name_match": pl.Boolean,
            "classification": pl.Utf8, "decision": pl.Utf8, "reasons": pl.Utf8,
        })
        explain_path = output_dir / f"linkage_explain_{run_tag}.csv"
        explain_df.write_csv(str(explain_path))
        logger.info("Explain CSV: %s (%d rows)", explain_path.name, len(explain_df))

    # text report
    report_path = output_dir / f"linkage_report_{run_tag}.txt"
    lines = [
        f"Record Linkage Report — {run_tag}",
        f"Questionnaire: {questionnaire_path.name}",
        "",
        f"Total responses   : {len(responses)}",
        f"MATCH_UNIQUE      : {n_unique}",
        f"MATCH_MULTIPLE    : {n_multiple}",
        f"NO_MATCH          : {n_none}",
        "",
        "By phase:",
    ]
    for k, v in sorted(phase_counts.items()):
        lines.append(f"  {k:<52}: {v}")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Report written: %s", report_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Multi-source record linkage: Questionnaire × ERG patients × RightEye."
    )
    p.add_argument("--base",               default=".")
    p.add_argument("--questionnaire-input",
        default="cardiff-questionnaire-responses/exportacao_respostas_escala_de_hipersensibilidade_05-30-2026.json")
    p.add_argument("--records-input",      default="patients-data/medical_records_history.parquet")
    p.add_argument("--mapping-root",       default="output/patients")
    p.add_argument("--righteye-input",     default="patients-data/data_right_eye.parquet")
    p.add_argument("--output",             default="output/reports/record_linkage")
    p.add_argument("--dry-run",            action="store_true")
    return p


def run(args: argparse.Namespace) -> None:
    base    = resolve_base_dir(args.base)
    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = resolve_output_dir(base, args.output, create=not args.dry_run)
    _process(
        questionnaire_path = resolve_input_path(base, args.questionnaire_input, must_exist=True),
        records_path       = resolve_input_path(base, args.records_input,       must_exist=True),
        mapping_root       = resolve_input_path(base, args.mapping_root,        must_exist=True),
        righteye_path      = resolve_input_path(base, args.righteye_input,      must_exist=True),
        output_dir         = out_dir,
        run_tag            = run_tag,
        dry_run            = args.dry_run,
    )


if __name__ == "__main__":
    configure_logging()
    run(build_parser().parse_args())
