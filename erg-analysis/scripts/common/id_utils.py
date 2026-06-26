"""ID and text normalization helpers used across pipeline stages."""

from __future__ import annotations

import re
import unicodedata
from typing import Optional, Tuple

import pandas as pd


_DATE_YYMMDD_RE = re.compile(r"^\d{6}$")
_DATETIME_YYMMDDHHMMSS_RE = re.compile(r"^\d{12}$")
_PRONTUARIO_RE = re.compile(r"^(\d{3,10})(.*)$")

# Some characters are not always decomposed as expected by NFKD.
_MANUAL_CHAR_MAP = {
    "ß": "ss",
    "ẞ": "ss",
    "ø": "o",
    "Ø": "o",
    "đ": "d",
    "Đ": "d",
    "ł": "l",
    "Ł": "l",
    "æ": "ae",
    "Æ": "ae",
    "œ": "oe",
    "Œ": "oe",
}


def _safe_str(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()

def clean_patient_name(text):
    text = str(text).strip()
    text = re.sub(r'^(c[oó]pia\s+de\s+)', '', text, flags=re.I)
    # Some input files carry replacement char where cedilla should be
    # (e.g., GON�ALVES). Preserve canonical token by mapping to "c".
    text = text.replace("\ufffd", "c")

    return text

def normalize_name(value: object) -> str:
    """Normalizes names to lowercase ASCII alnum while preserving base letters.

    Example: "João da Silva" -> "joaodasilva", "François" -> "francois", "Çelia" -> "celia".
    """
    text = clean_patient_name(_safe_str(value))
    if not text:
        return ""

    for src, dst in _MANUAL_CHAR_MAP.items():
        text = text.replace(src, dst)

    normalized = unicodedata.normalize("NFKD", text)
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^A-Za-z0-9]", "", without_marks).lower()


def normalize_prontuario(value: object) -> str:
    text = _safe_str(value)
    if not text:
        return ""
    match = re.search(r"\d+", text)
    return match.group(0) if match else ""


def format_birth_yyMMdd(value: object) -> str:
    text = _safe_str(value)
    if not text:
        return ""

    if _DATE_YYMMDD_RE.fullmatch(text):
        return text

    dt = pd.to_datetime(text, errors="coerce", utc=False)
    if pd.isna(dt):
        dt = pd.to_datetime(text, errors="coerce", utc=False, dayfirst=True)
    if pd.isna(dt):
        return ""
    return dt.strftime("%y%m%d")


def format_birth_metadata(value: object) -> str:
    birth = format_birth_yyMMdd(value)
    if not birth:
        return ""
    return f"{birth[0:2]}/{birth[2:4]}/{birth[4:6]}"


def format_test_yyMMddHHMMSS(value: object) -> str:
    text = _safe_str(value)
    if not text:
        return ""

    if _DATETIME_YYMMDDHHMMSS_RE.fullmatch(text):
        return text

    dt = pd.to_datetime(text, errors="coerce", utc=False)
    if pd.isna(dt):
        dt = pd.to_datetime(text, errors="coerce", utc=False, dayfirst=True)
    if pd.isna(dt):
        return ""
    return dt.strftime("%y%m%d%H%M%S")


def format_test_metadata(value: object) -> str:
    test = format_test_yyMMddHHMMSS(value)
    if not test:
        return ""
    return f"{test[0:2]}/{test[2:4]}/{test[4:6]} {test[6:8]}:{test[8:10]}:{test[10:12]}"


def extract_prontuario_and_name(patientid_field: object) -> Tuple[Optional[str], Optional[str]]:
    text = _safe_str(patientid_field)
    if not text:
        return None, None

    m = _PRONTUARIO_RE.match(text)
    if m:
        prontuario = m.group(1)
        raw_name = re.sub(r"^[\s,\-_/]+", "", m.group(2) or "")
        return prontuario, raw_name.strip()

    parts = re.split(r"[,\-_/]+", text, maxsplit=1)
    if len(parts) == 2 and parts[0].strip().isdigit():
        return parts[0].strip(), parts[1].strip()

    return None, text


def parse_patient_unique_id(pid: object) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    text = _safe_str(pid)
    if not text:
        return None, None, None, None

    parts = [p for p in text.split("_") if p != ""]
    if not parts:
        return None, None, None, None

    left = parts[0]
    prontuario = None
    name_part = None

    if "-" in left:
        p, n = left.split("-", 1)
        if p.isdigit():
            prontuario = p
            name_part = n
        else:
            prontuario = left
            name_part = None
    elif left.isdigit() and len(parts) >= 2 and not _DATE_YYMMDD_RE.fullmatch(parts[1]):
        prontuario = left
        name_part = parts[1]
        parts = [f"{left}-{parts[1]}", *parts[2:]]
    else:
        prontuario = left

    birth_part = None
    test_part = None

    if "-" in (parts[0] if parts else ""):
        if len(parts) >= 2:
            birth_part = parts[1]
        if len(parts) >= 3:
            test_part = parts[2]
    else:
        if len(parts) >= 2 and _DATE_YYMMDD_RE.fullmatch(parts[1]):
            birth_part = parts[1]
            if len(parts) >= 3:
                test_part = parts[2]
        elif len(parts) >= 3:
            name_part = name_part or parts[1]
            birth_part = parts[2]
            if len(parts) >= 4:
                test_part = parts[3]

    if name_part is not None:
        name_part = normalize_name(name_part)

    return prontuario, name_part, birth_part, test_part


def build_patient_unique_id(prontuario: object, name: object, birth_raw: object, test_raw: object) -> str:
    pront = normalize_prontuario(prontuario)
    name_part = normalize_name(name)
    birth = format_birth_yyMMdd(birth_raw)
    test = format_test_yyMMddHHMMSS(test_raw)

    if pront and name_part:
        left = f"{pront}-{name_part}"
    elif pront:
        left = pront
    elif name_part:
        left = name_part
    else:
        left = "unknown"
    if birth:
        return f"{left}_{birth}_{test}" if test else f"{left}_{birth}"
    return f"{left}_{test}" if test else left


def match_name_prefix(norm_name: str, name_lookup: dict[str, object]) -> tuple[object | None, str]:
    """Finds the best match for a normalized name in a lookup dict keyed by normalized names.

    Returns (value, method) where method is 'name_exact', 'name_prefix', or 'not_found'.
    Prefix match: one name starts-with the other (handles abbreviations like 'izabelacsb' vs 'izabelaceciliasilva').
    """
    if not norm_name:
        return None, "not_found"
    if norm_name in name_lookup:
        return name_lookup[norm_name], "name_exact"
    for key, value in name_lookup.items():
        if norm_name.startswith(key) or key.startswith(norm_name):
            return value, "name_prefix"
    return None, "not_found"


def normalize_patient_id(patient_id: object) -> str:
    """Canonical form for hash lookup: prontuario_name_birth_test (underscore separator).

    This keeps old compatibility while accepting malformed variants with extra '-'/'_'.
    """
    text = _safe_str(patient_id)
    if not text:
        return text

    prontuario, name_part, birth_part, test_part = parse_patient_unique_id(text)
    if not prontuario:
        # Fallback: preserve best-effort normalization only.
        compact = re.sub(r"\s+", "", text)
        return re.sub(r"_+", "_", compact.strip("_"))

    left = prontuario
    if name_part:
        left = f"{prontuario}_{name_part}"

    pieces = [left]
    if birth_part and _DATE_YYMMDD_RE.fullmatch(str(birth_part)):
        pieces.append(str(birth_part))
    if test_part:
        pieces.append(str(test_part))

    return "_".join(pieces)
