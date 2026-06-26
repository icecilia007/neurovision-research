"""
Conta pacientes únicos nos CSVs de exam/ pela coluna PatientID.
Cada CSV tem múltiplas linhas por paciente (um por exame).
"""
import csv
import os
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
EXAM_DIR = BASE / "exam"

csv_files = [f for f in os.listdir(EXAM_DIR) if f.lower().endswith(".csv")]

all_ids: set[str] = set()
file_stats: list[tuple[str, int, int]] = []

for fname in sorted(csv_files):
    path = EXAM_DIR / fname
    ids_in_file: set[str] = set()
    row_count = 0
    with open(path, encoding="latin-1", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("PatientID", "").strip()
            if pid:
                ids_in_file.add(pid)
                row_count += 1
    all_ids.update(ids_in_file)
    file_stats.append((fname, row_count, len(ids_in_file)))

print(f"Arquivos CSV em exam/: {len(csv_files)}")
print()
for fname, rows, unique in file_stats:
    print(f"  {fname}: {rows} linhas | {unique} pacientes únicos")
print()
print(f"Total de pacientes únicos (todos os CSVs combinados): {len(all_ids)}")
