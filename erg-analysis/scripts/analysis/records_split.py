"""Cross-reference two parquet datasets by ID and optionally split by a conditional column."""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

import polars as pl
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.logging_utils import configure_logging
from common.path_utils import resolve_base_dir, resolve_input_path, resolve_output_dir


logger = logging.getLogger(__name__)


def _read_parquet(path: Path) -> pl.DataFrame:
    return pl.from_arrow(pq.read_table(str(path)))


def _check_duplicate_columns(df: pl.DataFrame, label: str) -> None:
    seen: set = set()
    for col in df.columns:
        if col in seen:
            logger.warning("Coluna duplicada '%s' encontrada na base %s", col, label)
        seen.add(col)


def _write_output(df: pl.DataFrame, path: Path, fmt: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "parquet":
        df.write_parquet(str(path))
    else:
        df.write_csv(str(path))
    logger.info("Escrito: %s (%d linhas)", path, df.height)


def run(
    *,
    base: Path,
    reference_input: str,
    reference_id_col: str,
    reference_extra_cols: List[str],
    target_input: str,
    target_id_col: str,
    target_cols: List[str],
    output_dir: str,
    conditional_col: Optional[str],
    false_values: List[str],
    output_format: str,
) -> None:
    ref_path = resolve_input_path(base, reference_input)
    tgt_path = resolve_input_path(base, target_input)
    out_dir = resolve_output_dir(base, output_dir)

    logger.info("Lendo base de referencia: %s", ref_path)
    ref = _read_parquet(ref_path)
    logger.info("Lendo base alvo: %s", tgt_path)
    tgt = _read_parquet(tgt_path)

    _check_duplicate_columns(ref, f"referencia ({ref_path.name})")
    _check_duplicate_columns(tgt, f"alvo ({tgt_path.name})")

    # --- stats iniciais ---
    ref_total = ref.height
    tgt_total = tgt.height
    ref_unique_ids = ref.select(pl.col(reference_id_col).cast(pl.Utf8)).unique().height
    tgt_unique_ids = tgt.select(pl.col(target_id_col).cast(pl.Utf8)).unique().height

    logger.info("Linhas base referencia   : %d", ref_total)
    logger.info("Linhas base alvo         : %d", tgt_total)
    logger.info("IDs unicos - referencia  : %d", ref_unique_ids)
    logger.info("IDs unicos - alvo        : %d", tgt_unique_ids)

    # normaliza ID para string nos dois lados
    ref = ref.with_columns(pl.col(reference_id_col).cast(pl.Utf8).alias(reference_id_col))
    tgt = tgt.with_columns(pl.col(target_id_col).cast(pl.Utf8).alias(target_id_col))

    ref_ids = set(ref.select(reference_id_col).unique()[reference_id_col].to_list())
    tgt_ids = set(tgt.select(target_id_col).unique()[target_id_col].to_list())

    ids_found = ref_ids & tgt_ids
    ids_not_found = ref_ids - tgt_ids

    logger.info("IDs referencia encontrados na alvo     : %d", len(ids_found))
    logger.info("IDs referencia NAO encontrados na alvo : %d", len(ids_not_found))

    # colunas que vamos carregar da referencia
    ref_select_cols = list({reference_id_col} | set(reference_extra_cols))
    if conditional_col and conditional_col in ref.columns:
        if conditional_col not in ref_select_cols:
            ref_select_cols.append(conditional_col)

    ref_slim = ref.select([c for c in ref_select_cols if c in ref.columns])
    tgt_slim = tgt.select([c for c in target_cols if c in tgt.columns])

    # renomear coluna ID da referencia para fazer o join sem colidir
    ref_id_alias = f"_ref_{reference_id_col}"
    ref_slim = ref_slim.rename({reference_id_col: ref_id_alias})

    joined = tgt_slim.join(
        ref_slim,
        left_on=target_id_col,
        right_on=ref_id_alias,
        how="inner",
    )

    # --- output: IDs não encontrados (linhas da referencia sem match) ---
    not_found_df = ref.filter(
        pl.col(reference_id_col).is_in(list(ids_not_found))
    ).select([c for c in ref_slim.rename({ref_id_alias: reference_id_col}).columns if c in ref.columns])

    ext = f".{output_format}"
    _write_output(
        not_found_df,
        out_dir / f"not_found_in_target{ext}",
        output_format,
    )

    # --- split condicional ---
    if conditional_col and conditional_col in joined.columns:
        false_vals_set = {v.strip() for v in false_values}

        is_false_expr = pl.col(conditional_col).cast(pl.Utf8).str.strip_chars().is_in(list(false_vals_set))

        df_true = joined.filter(~is_false_expr)
        df_false = joined.filter(is_false_expr).drop(conditional_col)

        ids_true = df_true.select(target_id_col).unique().height
        ids_false = df_false.select(target_id_col).unique().height

        logger.info("IDs encontrados condicional TRUE  : %d", ids_true)
        logger.info("IDs encontrados condicional FALSE : %d", ids_false)

        _write_output(df_true, out_dir / f"found_conditional_true{ext}", output_format)
        _write_output(df_false, out_dir / f"found_conditional_false{ext}", output_format)
    else:
        if conditional_col:
            logger.warning("Coluna condicional '%s' nao encontrada apos join — saida unica gerada", conditional_col)
        _write_output(joined, out_dir / f"found_in_target{ext}", output_format)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Cruza duas bases parquet por ID e gera splits opcionais por coluna condicional.",
    )
    p.add_argument("--base", default=".", help="Diretorio base para resolver paths relativos")
    p.add_argument("--reference-input", required=True, help="Parquet de referencia (base com IDs a buscar)")
    p.add_argument("--reference-id-col", required=True, help="Coluna de ID na base de referencia")
    p.add_argument(
        "--reference-extra-cols",
        default="",
        help="Colunas adicionais da referencia para incluir nos outputs (separadas por virgula)",
    )
    p.add_argument("--target-input", required=True, help="Parquet alvo (base onde buscar os IDs)")
    p.add_argument("--target-id-col", required=True, help="Coluna de ID na base alvo")
    p.add_argument(
        "--target-cols",
        required=True,
        help="Colunas da base alvo a manter nos outputs (separadas por virgula)",
    )
    p.add_argument("--output", required=True, help="Pasta de saida")
    p.add_argument(
        "--conditional-col",
        default=None,
        help="Coluna da referencia usada para split (ex: Neurodivergencia)",
    )
    p.add_argument(
        "--false-values",
        default="",
        help="Valores que representam FALSE na coluna condicional (separados por pipe |). Ex: 'Nao tem|Nâo tem'",
    )
    p.add_argument(
        "--output-format",
        choices=["parquet", "csv"],
        default="parquet",
        help="Formato dos arquivos de saida",
    )
    return p


def main() -> None:
    configure_logging()
    parser = _build_parser()
    args = parser.parse_args()

    base = resolve_base_dir(args.base)

    extra_cols = [c.strip() for c in args.reference_extra_cols.split(",") if c.strip()]
    target_cols = [c.strip() for c in args.target_cols.split(",") if c.strip()]
    false_values = [v.strip() for v in args.false_values.split("|") if v.strip()]

    run(
        base=base,
        reference_input=args.reference_input,
        reference_id_col=args.reference_id_col,
        reference_extra_cols=extra_cols,
        target_input=args.target_input,
        target_id_col=args.target_id_col,
        target_cols=target_cols,
        output_dir=args.output,
        conditional_col=args.conditional_col,
        false_values=false_values,
        output_format=args.output_format,
    )


if __name__ == "__main__":
    main()
