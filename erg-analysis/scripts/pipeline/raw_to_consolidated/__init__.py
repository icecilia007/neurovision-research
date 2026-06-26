"""Fluxo raw para dados consolidados."""

from pipeline.raw_to_consolidated.patient_preparation import run as run_patient_preparation
from pipeline.raw_to_consolidated.waveform_consolidation import run as run_waveform_consolidation
from pipeline.raw_to_consolidated.consolidate_from_raw import run as run_consolidate_from_raw

__all__ = ["run_patient_preparation", "run_waveform_consolidation", "run_consolidate_from_raw"]
