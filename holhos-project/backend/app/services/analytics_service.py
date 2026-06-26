import math
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats as scipy_stats

from app.services.chyps_config import (
    CHYPS_V_SCALE_ITEMS,
    CHYPS_V_SUBSCALES,
    DEMOGRAPHIC_FILTERS,
    GLOBAL_SCORE_RANGE,
)


class AnalyticsService:

    # ── Descriptive Statistics ──────────────────────────────────────────

    @staticmethod
    def compute_descriptive_stats(values: List[float]) -> Dict[str, Any]:
        if not values:
            return {"mean": 0, "sd": 0, "mode": 0, "median": 0, "iqr": 0, "min": 0, "max": 0, "n": 0}

        arr = np.array(values, dtype=float)
        q1 = float(np.percentile(arr, 25))
        q3 = float(np.percentile(arr, 75))
        mode_result = scipy_stats.mode(arr, keepdims=True)
        mode_val = float(mode_result.mode[0]) if mode_result.count[0] > 0 else float(arr[0])

        return {
            "mean": round(float(np.mean(arr)), 2),
            "sd": round(float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0, 2),
            "mode": round(mode_val, 2),
            "median": round(float(np.median(arr)), 2),
            "iqr": round(q3 - q1, 2),
            "min": round(float(np.min(arr)), 2),
            "max": round(float(np.max(arr)), 2),
            "n": len(arr),
        }

    # ── CHYPS-V Scoring ────────────────────────────────────────────────

    @staticmethod
    def _re_score_answer(
        selected_options: Optional[List[int]],
        question_options: List[Dict],
    ) -> float:
        if not selected_options:
            return 0.0
        sorted_opts = sorted(question_options, key=lambda o: (o.get("sort_order") or 0, o["id"]))
        position_map = {opt["id"]: i for i, opt in enumerate(sorted_opts)}
        total = 0.0
        for opt_id in selected_options:
            opt = next((o for o in question_options if o["id"] == opt_id), None)
            if opt is None:
                continue
            weight = opt.get("weight") or 0.0
            # Use explicit weight when non-zero; otherwise use ordinal position (Likert).
            total += weight if weight else float(position_map.get(opt_id, 0))
        return total

    def compute_chyps_v_scores(
        self,
        submissions: List[Dict],
        caption_to_options: Dict[str, List[Dict]],
    ) -> Dict[str, Any]:
        respondent_scores = []
        global_scores = []
        subscale_scores_all: Dict[str, List[float]] = {name: [] for name in CHYPS_V_SUBSCALES}

        for sub in submissions:
            answers_by_caption: Dict[str, Dict] = {}
            for ans in sub.get("answers", []):
                cap = ans.get("caption")
                if cap:
                    answers_by_caption[cap] = ans

            item_scores: Dict[str, float] = {}
            for caption in CHYPS_V_SCALE_ITEMS:
                ans = answers_by_caption.get(caption)
                if ans is None:
                    item_scores[caption] = 0.0
                    continue
                opts = caption_to_options.get(caption, [])
                # Re-derive the Likert score from option position/weight whenever
                # option metadata is available; fall back to stored score only when
                # we have no option context at all (e.g. free-text or missing map).
                if opts and ans.get("selected_options"):
                    item_scores[caption] = self._re_score_answer(ans["selected_options"], opts)
                else:
                    item_scores[caption] = float(ans.get("score", 0))

            global_score = sum(item_scores.values())
            global_scores.append(global_score)

            sub_subscales: Dict[str, float] = {}
            for name, config in CHYPS_V_SUBSCALES.items():
                score = sum(item_scores.get(c, 0.0) for c in config["items"])
                sub_subscales[name] = score
                subscale_scores_all[name].append(score)

            respondent_scores.append({
                "submission_id": sub["submission_id"],
                "global_score": round(global_score, 2),
                "subscale_scores": {k: round(v, 2) for k, v in sub_subscales.items()},
                "item_scores": {k: round(v, 2) for k, v in item_scores.items()},
            })

        result: Dict[str, Any] = {
            "respondent_scores": respondent_scores,
            "global_stats": self.compute_descriptive_stats(global_scores),
            "subscale_stats": {},
        }

        for name, scores in subscale_scores_all.items():
            result["subscale_stats"][name] = {
                **self.compute_descriptive_stats(scores),
                "items": CHYPS_V_SUBSCALES[name]["items"],
                "label_en": CHYPS_V_SUBSCALES[name]["label_en"],
            }

        item_matrix = []
        for rs in respondent_scores:
            row = [rs["item_scores"].get(c, 0.0) for c in CHYPS_V_SCALE_ITEMS]
            item_matrix.append(row)

        if item_matrix and len(item_matrix) > 1:
            result["cronbachs_alpha"] = self.compute_cronbachs_alpha(item_matrix)
            try:
                corr_matrix, p_matrix = scipy_stats.spearmanr(
                    np.array(item_matrix, dtype=float), axis=0
                )
                result["spearman_correlation"] = {
                    "matrix": _nan_to_none(np.round(corr_matrix, 4)),
                    "p_values": _nan_to_none(np.round(p_matrix, 4)),
                    "labels": CHYPS_V_SCALE_ITEMS,
                }
            except Exception:
                result["spearman_correlation"] = None
        else:
            result["cronbachs_alpha"] = None

        return result

    # ── Cronbach's Alpha ───────────────────────────────────────────────

    @staticmethod
    def compute_cronbachs_alpha(item_matrix: List[List[float]]) -> float:
        if len(item_matrix) < 2:
            return 0.0
        arr = np.array(item_matrix, dtype=float)
        k = arr.shape[1]
        if k < 2:
            return 0.0
        item_vars = np.var(arr, axis=0, ddof=1)
        total_var = np.var(np.sum(arr, axis=1), ddof=1)
        if total_var == 0:
            return 0.0
        alpha = (k / (k - 1)) * (1 - np.sum(item_vars) / total_var)
        return round(float(alpha), 4)

    # ── Crosstabulation ────────────────────────────────────────────────

    @staticmethod
    def compute_crosstab(
        row_values: List[Any],
        col_values: List[Any],
    ) -> Dict[str, Any]:
        if len(row_values) != len(col_values) or not row_values:
            return {"table": [], "row_labels": [], "col_labels": [], "chi_square": None, "p_value": None}

        row_labels = sorted(set(str(v) for v in row_values if v is not None))
        col_labels = sorted(set(str(v) for v in col_values if v is not None))

        row_idx = {label: i for i, label in enumerate(row_labels)}
        col_idx = {label: i for i, label in enumerate(col_labels)}

        table = [[0] * len(col_labels) for _ in row_labels]
        for rv, cv in zip(row_values, col_values):
            rl, cl = str(rv), str(cv)
            if rl in row_idx and cl in col_idx:
                table[row_idx[rl]][col_idx[cl]] += 1

        result: Dict[str, Any] = {
            "table": table,
            "row_labels": row_labels,
            "col_labels": col_labels,
        }

        try:
            arr = np.array(table, dtype=float)
            if arr.shape[0] >= 2 and arr.shape[1] >= 2:
                chi2, p, dof, expected = scipy_stats.chi2_contingency(arr)
                result["chi_square"] = round(float(chi2), 4)
                result["p_value"] = round(float(p), 6)
                result["degrees_of_freedom"] = int(dof)
            else:
                result["chi_square"] = None
                result["p_value"] = None
        except Exception:
            result["chi_square"] = None
            result["p_value"] = None

        return result

    # ── Filtering ──────────────────────────────────────────────────────

    @staticmethod
    def filter_submissions(
        submissions: List[Dict],
        filters: Dict[str, Any],
    ) -> List[Dict]:
        if not filters:
            return submissions

        filtered = list(submissions)

        for demo_key, config in DEMOGRAPHIC_FILTERS.items():
            filter_val = filters.get(demo_key)
            if not filter_val:
                continue

            pattern = config["pattern"].lower()
            caption = _find_caption_by_pattern(filtered, pattern)
            if not caption:
                continue

            if config["type"] == "year":
                year_min = filter_val.get("min") if isinstance(filter_val, dict) else None
                year_max = filter_val.get("max") if isinstance(filter_val, dict) else None
                filtered = [
                    s for s in filtered
                    if _matches_year(s, caption, year_min, year_max)
                ]
            else:
                if isinstance(filter_val, str):
                    filter_val = [filter_val]
                filtered = [
                    s for s in filtered
                    if _matches_categorical(s, caption, filter_val)
                ]

        if "validity" in filters:
            caption = filters["validity"]["caption"]
            accepted_ids = set(filters["validity"]["accepted_option_ids"])
            filtered = [
                s for s in filtered
                if _passes_validity_check(s, caption, accepted_ids)
            ]

        return filtered

    # ── Question Distributions ─────────────────────────────────────────

    @staticmethod
    def compute_question_distributions(
        question_stats: List[Dict],
    ) -> List[Dict]:
        distributions = []
        for qstat in question_stats:
            qtype = qstat.get("question_type", "")
            option_details = qstat.get("option_details", {})

            if qtype == "free_text":
                distributions.append({
                    "question_id": qstat["question_id"],
                    "question_text": qstat.get("question_text", ""),
                    "question_title": qstat.get("question_title"),
                    "question_body": qstat.get("question_body"),
                    "question_type": qtype,
                    "chart_type": "text_table",
                    "total_answers": qstat.get("total_answers", 0),
                })
                continue

            if not option_details:
                distributions.append({
                    "question_id": qstat["question_id"],
                    "question_text": qstat.get("question_text", ""),
                    "question_title": qstat.get("question_title"),
                    "question_body": qstat.get("question_body"),
                    "question_type": qtype,
                    "chart_type": "none",
                    "total_answers": qstat.get("total_answers", 0),
                })
                continue

            options = list(option_details.values()) if isinstance(option_details, dict) else option_details
            labels = [o["text"] for o in options]
            counts = [o["count"] for o in options]
            total = sum(counts) or 1
            percentages = [round(c / total * 100, 1) for c in counts]

            chart_type = "pie" if len(options) == 2 else "bar"

            distributions.append({
                "question_id": qstat["question_id"],
                "question_text": qstat.get("question_text", ""),
                "question_title": qstat.get("question_title"),
                "question_body": qstat.get("question_body"),
                "question_type": qtype,
                "chart_type": chart_type,
                "labels": labels,
                "counts": counts,
                "percentages": percentages,
                "total_answers": qstat.get("total_answers", 0),
                "stats": AnalyticsService.compute_descriptive_stats(
                    _option_counts_to_scores(options, counts)
                ) if qtype in ("single",) else None,
            })

        return distributions


# ── Helper functions (module-level) ────────────────────────────────────

def _nan_to_none(arr) -> list:
    """Convert numpy array to nested list, replacing NaN/Inf with None for JSON serialization."""
    if isinstance(arr, np.ndarray):
        arr = arr.tolist()
    if isinstance(arr, list):
        return [_nan_to_none(v) for v in arr]
    if isinstance(arr, float) and (math.isnan(arr) or math.isinf(arr)):
        return None
    return arr


def _find_caption_by_pattern(submissions: List[Dict], pattern: str) -> Optional[str]:
    for sub in submissions:
        for ans in sub.get("answers", []):
            q_text = (ans.get("question_text") or "").lower()
            if pattern in q_text and ans.get("caption"):
                return ans["caption"]
    return None


def _matches_year(submission: Dict, caption: str, year_min: Optional[int], year_max: Optional[int]) -> bool:
    for ans in submission.get("answers", []):
        if ans.get("caption") == caption:
            raw = ans.get("text_response") or ""
            try:
                parts = raw.strip().split("/")
                if len(parts) == 3:
                    year = int(parts[2])
                else:
                    year = int(float(raw))
            except (ValueError, IndexError):
                return True
            if year_min is not None and year < year_min:
                return False
            if year_max is not None and year > year_max:
                return False
            return True
    return True


def _matches_categorical(submission: Dict, caption: str, allowed_values: List[str]) -> bool:
    for ans in submission.get("answers", []):
        if ans.get("caption") == caption:
            texts = ans.get("selected_option_texts", [])
            if not texts and ans.get("text_response"):
                texts = [ans["text_response"]]
            if not texts:
                return True
            return any(t in allowed_values for t in texts)
    return True


def _passes_validity_check(submission: Dict, caption: str, accepted_ids: set) -> bool:
    for ans in submission.get("answers", []):
        if ans.get("caption") == caption:
            selected = set(ans.get("selected_options") or [])
            if not selected:
                # Answered the question but selected no option (incomplete data)
                # → treat as unanswered, let through
                return True
            return bool(selected & accepted_ids)
    return True


def _option_counts_to_scores(options: List[Dict], counts: List[int]) -> List[float]:
    from app.services.chyps_config import LIKERT_TEXT_TO_SCORE
    scores = []
    for opt, count in zip(options, counts):
        weight = opt.get("weight", 0) or 0
        if weight == 0:
            text_lower = (opt.get("text") or "").lower().strip()
            weight = LIKERT_TEXT_TO_SCORE.get(text_lower, 0)
        scores.extend([weight] * count)
    return scores


analytics_service = AnalyticsService()
