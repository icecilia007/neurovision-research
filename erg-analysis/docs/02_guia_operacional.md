# Guia Operacional (Passo a Passo)

## 1. Preparação de ambiente

Execute os comandos abaixo a partir do diretório `erg-analysis/`.

WSL (recomendado):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Spark no Windows (winutils)

- O preprocessamento usa PySpark (`consolidate`, `patient_preparation`, `waveform_consolidation`).
- Em WSL/Linux, não precisa de `winutils`.
- Em Windows nativo, para evitar erro de runtime do Spark/Hadoop, configure:
  - Java instalado e funcional.
  - `HADOOP_HOME` apontando para o diretório Hadoop local.
  - Arquivos `winutils.exe` e `hadoop.dll` em `HADOOP_HOME\\bin`.

## 2. Fluxo recomendado: consolidação + purge + anonimização

### 2.1 Consolidação unificada com relatório de IDs

```bash
python scripts/main.py consolidate-and-audit \
  --base . \
  --patients-input exam \
  --waveforms-input waveform \
  --patients-output output/patients \
  --waveforms-output output/waveforms \
  --reports-output output/reports/id_audit \
  --workers 6
```

Esse comando:
- Processa CSVs de pacientes e gera `output/patients/`.
- Consolida waveforms e gera `output/waveforms/consolidated/`.
- Gera automaticamente o relatório `output/reports/id_audit/unique_ids_only_one_base_counts.csv`.

### 2.2 Anotação clínica do mapping (annotate)

```bash
python scripts/main.py annotate \
  --base . \
  --records-input patients-data/medical_records_history.parquet \
  --mapping-root output/patients \
  --reports-output output/reports/annotation
```

Esse comando:
- Anota `records_nome`, `neurodivergencia` e `laudo` em todos os `patients_id_mapping-*.parquet`.
- Gera `output/reports/annotation/annotation_audit_*.parquet` com match_method por patient_unique_id.
- Gera `output/reports/annotation/unmatched_mapping_*.{parquet,csv}` com linhas sem match.

Quando você rodar `anonymize` depois, o `id_map_*.parquet` gerado em staging já vai conter essas colunas automaticamente.

**Já rodou o consolidate e quer só anotar (sem re-rodar tudo)?**

```bash
python scripts/main.py annotate --base .
```

### 2.3 Remoção de IDs órfãos (purge)

Recomendado: primeiro valide com `--dry-run`:

```bash
python scripts/main.py purge --base . --dry-run
```

Depois execute de fato:

```bash
python scripts/main.py purge --base . --workers 6
```

Esse comando:
- Lê `output/reports/id_audit/unique_ids_only_one_base_counts.csv`.
- Remove linhas de IDs `only_patients` de todos os parquets em `output/patients/`.
- Remove linhas de IDs `only_metadata` de todos os parquets em `output/waveforms/consolidated/`.

### 2.4 Anonimização completa

```bash
python scripts/main.py anonymize --base . --input-root output --output-root output/data --workers 8
```

Esse comando:
- Descobre automaticamente patients, metadata e waveforms em `output/`.
- Gera auditoria completa pré-anonymization.
- Executa hash + remoção de campos sensíveis.
- Gera datasets finais para análise.
- Gera auditoria completa pós-anonymization.

## 3. Fluxo manual por etapas

### 3.1 Consolidação de pacientes + waveforms (sem relatório automático)

```bash
python scripts/main.py consolidate \
  --base . \
  --patients-input exam \
  --waveforms-input waveform \
  --patients-output output/patients \
  --waveforms-output output/waveforms \
  --workers 6
```

### 3.2 Geração de datasets finais a partir de consolidados

```bash
python scripts/main.py parquet \
  --base . \
  --input output/waveforms/consolidated \
  --output output/data/manual \
  --compact-names \
  --name-date-suffix 20260417_101500
```

### 3.3 Auditoria de IDs (cross)

```bash
python scripts/analysis/audit_unique_patient_ids.py \
  --base . \
  --mode cross \
  --patients-input output/patients/patients-20260417-092416.parquet \
  --metadata-input output/waveforms/consolidated/consolidated_metadata.parquet \
  --output output/reports/id_audit_manual
```

## 4. Validações rápidas após rodar

WSL / Linux:
```bash
ls -lah output/data/anonymized/staging
ls -lah output/data/anonymized/datasets
ls -lah output/data/reports/id_audit/before_anonymization
ls -lah output/data/reports/id_audit/after_anonymization
```

Windows PowerShell:
```powershell
Get-ChildItem output\data\anonymized\staging
Get-ChildItem output\data\anonymized\datasets
Get-ChildItem output\data\reports\id_audit\before_anonymization
Get-ChildItem output\data\reports\id_audit\after_anonymization
```

## 5. Dicas práticas

- Em produção, evite rodar scripts isolados sem necessidade.
- Para rastreabilidade, preserve o sufixo `YYYYMMDD_HHMMSS` dos artefatos.
- No Windows nativo, valide setup Spark/Hadoop antes de rodar preprocessamento.
