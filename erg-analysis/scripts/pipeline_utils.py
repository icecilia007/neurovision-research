"""Utilitarios compartilhados da pipeline de normalizacao e hash."""

import csv
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import bcrypt
import chardet
import polars as pl
import pyarrow as pa
import pyarrow.csv as pa_csv
import pyarrow.parquet as pq
from dotenv import load_dotenv

from common.id_utils import normalize_patient_id as canonical_normalize_patient_id

logger = logging.getLogger(__name__)


def detect_encoding(path: Path, num_bytes: int = 4096) -> str:
    """Detecta encoding do arquivo com fallback seguro."""
    try:
        with open(path, "rb") as f:
            raw = f.read(num_bytes)
        guess = chardet.detect(raw)
        return guess.get("encoding") or "utf-8"
    except Exception:
        return "utf-8"


def read_csv_arrow(path: Path, block_size_mb: int = 64, use_threads: bool = True) -> pl.DataFrame:
    """Le CSV com PyArrow e retorna DataFrame Polars."""
    encoding = detect_encoding(path)
    read_options = pa_csv.ReadOptions(
        block_size=block_size_mb * 1024 * 1024,
        use_threads=use_threads,
        encoding=encoding,
    )
    parse_options = pa_csv.ParseOptions(delimiter=",")
    convert_options = pa_csv.ConvertOptions(strings_can_be_null=True)
    table = pa_csv.read_csv(path, read_options=read_options, parse_options=parse_options, convert_options=convert_options)
    return pl.from_arrow(table)


def iter_csv_arrow(path: Path, block_size_mb: int = 64, use_threads: bool = True):
    """Itera CSV com PyArrow e retorna chunks em DataFrame Polars."""
    encoding = detect_encoding(path)
    read_options = pa_csv.ReadOptions(
        block_size=block_size_mb * 1024 * 1024,
        use_threads=use_threads,
        encoding=encoding,
    )
    parse_options = pa_csv.ParseOptions(delimiter=",")
    convert_options = pa_csv.ConvertOptions(strings_can_be_null=True)
    reader = pa_csv.open_csv(path, read_options=read_options, parse_options=parse_options, convert_options=convert_options)
    for batch in reader:
        table = pa.Table.from_batches([batch])
        yield pl.from_arrow(table)


def normalize_patient_id(patient_id: str) -> str:
    """Normaliza patient_unique_id para forma canonica tolerante a variacoes."""
    return canonical_normalize_patient_id(patient_id)


class PatientIDHasher:
    """Hasheador bcrypt com salt vindo de argumento ou .env."""

    _ROUNDS = 12
    _BCRYPT_PREFIX = "$2a$"

    def __init__(self, salt: Optional[str] = None) -> None:
        load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
        self.salt = self._resolve_salt(salt)

    def _resolve_salt(self, salt: Optional[str]) -> bytes:
        if salt:
            if salt.startswith(self._BCRYPT_PREFIX):
                return salt.encode("utf-8")
            return bcrypt.gensalt(rounds=self._ROUNDS)

        salt_env = os.getenv("BCRYPT_SALT")
        if salt_env:
            if salt_env.startswith(self._BCRYPT_PREFIX):
                return salt_env.encode("utf-8")
            return bcrypt.gensalt(rounds=self._ROUNDS)

        return bcrypt.gensalt(rounds=self._ROUNDS)

    def hash_patient_id(self, patient_id: str) -> str:
        if patient_id is None:
            return patient_id
        value = str(patient_id)
        if value.strip() == "":
            return patient_id
        hashed = bcrypt.hashpw(value.encode("utf-8"), self.salt)
        return hashed.decode("utf-8")


@dataclass
class ParquetChunkWriter:
    """Escrita incremental de parquet por chunks."""

    output_path: Path
    compression: str = "snappy"
    force_string_schema: bool = False

    def __post_init__(self) -> None:
        self._writer: Optional[pq.ParquetWriter] = None
        self._schema: Optional[pa.Schema] = None

    def write(self, df) -> None:
        if df is None:
            return

        if isinstance(df, pl.DataFrame):
            if df.height == 0:
                return
            table = df.to_arrow()
        elif isinstance(df, pa.Table):
            if df.num_rows == 0:
                return
            table = df
        else:
            if hasattr(df, "empty") and df.empty:
                return
            table = pa.Table.from_pandas(df, preserve_index=False)

        if self._schema is None:
            if self.force_string_schema:
                self._schema = pa.schema([pa.field(col, pa.string()) for col in table.schema.names])
                table = table.cast(self._schema, safe=False)
            else:
                self._schema = table.schema
        else:
            table = table.cast(self._schema, safe=False)

        if self._writer is None:
            self._writer = pq.ParquetWriter(self.output_path, self._schema, compression=self.compression)
        self._writer.write_table(table)

    def close(self) -> None:
        if self._writer is not None:
            self._writer.close()
            self._writer = None


@dataclass
class MissingIdTracker:
    """Acumula IDs sem hash para debug."""

    rows: List[Dict[str, str]]

    @classmethod
    def create(cls) -> "MissingIdTracker":
        return cls(rows=[])

    def add(self, source_file: str, patient_id: str) -> None:
        self.rows.append({"source_file": source_file, "patient_unique_id": patient_id})

    def to_dataframe(self) -> pl.DataFrame:
        return pl.DataFrame(self.rows)


@dataclass
class MissingIdCsvWriter:
    """Escreve IDs sem hash em CSV incremental."""

    output_path: Path
    _header_written: bool = False

    def write_rows(self, rows: List[Dict[str, str]]) -> None:
        if not rows:
            return
        mode = "a" if self._header_written else "w"
        with self.output_path.open(mode, newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=["source_file", "patient_unique_id"])
            if not self._header_written:
                writer.writeheader()
            writer.writerows(rows)
        self._header_written = True


def load_hash_mapping(parquet_path: Path) -> Dict[str, str]:
    """Carrega parquet de mapping hash e retorna dict patient_unique_id -> hashed."""
    df = pl.read_parquet(parquet_path, columns=["patient_unique_id", "patient_unique_id_hashed"])
    df = df.drop_nulls(["patient_unique_id", "patient_unique_id_hashed"])
    return dict(zip(df["patient_unique_id"].cast(pl.Utf8).to_list(), df["patient_unique_id_hashed"].cast(pl.Utf8).to_list()))


def drop_columns_if_present(df: pl.DataFrame, columns: Iterable[str]) -> pl.DataFrame:
    """Remove colunas se existirem, sem falhar."""
    cols_to_drop = [c for c in columns if c in df.columns]
    if cols_to_drop:
        return df.drop(cols_to_drop)
    return df


def dedupe_mapping(df: pl.DataFrame) -> pl.DataFrame:
    """Remove duplicatas mantendo a primeira ocorrencia do patient_unique_id."""
    if "patient_unique_id" not in df.columns:
        return df
    return df.unique(subset=["patient_unique_id"], keep="first")
