"""Orchestrates normalize, mapping, and apply stages for hash pipeline."""

import argparse
import logging
from pathlib import Path
from typing import List

from pipeline.hashing.hash_apply_streaming import run as run_apply_streaming
from pipeline.hashing.hash_mapping import run as run_hash_mapping
from pipeline.hashing.normalize_patients import run as run_normalize


logger = logging.getLogger(__name__)


def _parse_list(values: List[str] | None) -> List[str]:
    if not values:
        return []
    parsed: List[str] = []
    for value in values:
        parsed.extend([piece.strip() for piece in value.split(",") if piece.strip()])
    return parsed


def _parse_csv_columns(value: str) -> List[str]:
    return [entry.strip() for entry in value.split(",") if entry.strip()]


def run_hash_orchestrator(args: argparse.Namespace) -> None:
    """Runs selected hash stages according to CLI flags."""
    base = Path(args.base).resolve()

    normalize_inputs = _parse_list(getattr(args, "normalize_inputs", None))
    apply_inputs = _parse_list(getattr(args, "apply_inputs", None))

    drop_columns = _parse_csv_columns(getattr(args, "drop_columns", ""))
    float_columns = _parse_csv_columns(getattr(args, "float_columns", ""))
    int_columns = _parse_csv_columns(getattr(args, "int_columns", ""))

    if not getattr(args, "skip_normalize", False):
        if not normalize_inputs:
            raise ValueError("--normalize-inputs is required when --skip-normalize is not set")
        logger.info("HASH stage 1/3: normalize")
        run_normalize(base=base, inputs=normalize_inputs, column=args.column)

    if not getattr(args, "skip_mapping", False):
        logger.info("HASH stage 2/3: build mapping")
        run_hash_mapping(
            base=base,
            input_csv=args.mapping_input,
            output_parquet=args.mapping_output,
            column=args.column,
            salt=args.salt,
        )

    if not getattr(args, "skip_apply", False):
        if not apply_inputs:
            raise ValueError("--apply-inputs is required when --skip-apply is not set")
        logger.info("HASH stage 3/3: apply streaming")
        run_apply_streaming(
            base=base,
            inputs=apply_inputs,
            mapping_path=args.mapping_output,
            output_dir=args.output_dir,
            debug_csv=args.debug_csv,
            column=args.column,
            drop_columns=drop_columns,
            chunk_size=args.chunk_size,
            float_columns=float_columns,
            int_columns=int_columns,
            metadata_before=getattr(args, "metadata_before", None),
            metadata_after=getattr(args, "metadata_after", None),
            metadata=getattr(args, "metadata", None),
            name_suffix=getattr(args, "name_suffix", ""),
        )
