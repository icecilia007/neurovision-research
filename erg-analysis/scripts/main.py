"""Intentional stage runner entrypoint.

Examples:
    python scripts/main.py consolidate --base . --patients-input exam --waveforms-input waveform
    python scripts/main.py hash --base . --mapping-input ... --mapping-output ... --apply-inputs ... --output-dir ... --debug-csv ...
    python scripts/main.py parquet --base . --input outputs/hashed --output outputs/hashed
"""

from pipeline.stage_runner import main


if __name__ == "__main__":
    main()
