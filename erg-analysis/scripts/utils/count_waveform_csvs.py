"""
Conta arquivos CSV únicos em waveform/ sem abrir nenhum arquivo.
Unicidade por nome de arquivo (sem considerar duplicatas de ID de paciente).
"""
import os
import re
from pathlib import Path
from collections import Counter

BASE = Path(__file__).resolve().parents[2]
WAVEFORM_DIR = BASE / "waveform"

files = [f for f in os.listdir(WAVEFORM_DIR) if f.lower().endswith(".csv")]

# Extrai o ID de paciente da parte inicial do nome (antes do primeiro _YYMMDD_)
def extract_patient_id(filename: str) -> str:
    # Formato: <ID>_<AAAAMMDD>_<timestamp>.csv  ou  <ID>-<NOME>_<AAAAMM>_<timestamp>.csv
    # Pega tudo antes do segundo underline que separa data/hora
    parts = filename.rsplit(".", 1)[0].split("_")
    return parts[0] if parts else filename

patient_ids = [extract_patient_id(f) for f in files]
id_counts = Counter(patient_ids)
duplicates = {pid: n for pid, n in id_counts.items() if n > 1}

print(f"Total de arquivos CSV em waveform/: {len(files)}")
print(f"IDs de paciente únicos (prefixo do nome): {len(id_counts)}")
if duplicates:
    print(f"\nIDs com mais de 1 arquivo ({len(duplicates)}):")
    for pid, n in sorted(duplicates.items(), key=lambda x: -x[1]):
        print(f"  {pid}: {n} arquivos")
else:
    print("Nenhum ID duplicado encontrado.")
