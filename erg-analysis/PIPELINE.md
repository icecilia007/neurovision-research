# Pipeline ERG

Guia principal de execução da pipeline de ponta a ponta.

## Pré-requisitos

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

> ⚠️ **Spark no Windows:** os stages `consolidate` e `consolidate-and-audit` usam PySpark. Em WSL/Linux nenhuma configuração adicional é necessária. Em Windows nativo, configure Java + Hadoop e garanta `winutils.exe` e `hadoop.dll` em `HADOOP_HOME\bin`.

## Reprodução rápida dos resultados de classificação

Se você quer apenas reproduzir os resultados de classificação sem rodar a pipeline completa, o `data/classification_dataset.parquet` já está disponível no repositório. Basta instalar as dependências e abrir o notebook:

```bash
pip install -r requirements.txt
```

```
studies/neurodivergencia_classification/notebooks/
  neurodivergencia_classification_describre_final.ipynb
```

O notebook detecta automaticamente a presença de `data/classification_dataset.parquet` e usa esse arquivo quando os dados brutos da pipeline não estão disponíveis.

> **Acesso aos dados brutos:** Os dados brutos e intermediários (waveforms, features por sessão, questionários) não são distribuídos publicamente em cumprimento à LGPD. Para solicitar acesso mediante justificativa, entre em contato via **icsbarbosa@sga.pucminas.br** ou **izabelaengineer@gmail.com**. Consulte o [README](README.md) para mais detalhes.

---

## Fluxo completo recomendado

> Os passos abaixo requerem acesso aos dados brutos de ERG (`exam/`, `waveform/`, `patients-data/`). Veja a seção de dados no [README](README.md).

### 1. Consolidação + auditoria de IDs

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

Gera:
- `output/patients/` — dataset de pacientes consolidado
- `output/waveforms/consolidated/` — metadata e waveforms consolidados
- `output/reports/id_audit/` — relatório de IDs cruzados entre as duas bases

### 2. Anotação clínica (annotate)

```bash
python scripts/main.py annotate \
  --base . \
  --records-input patients-data/medical_records_history.parquet \
  --mapping-root output/patients \
  --reports-output output/reports/annotation
```

Anota `neurodivergencia`, `laudo` e `records_nome` em `patients_id_mapping-*.parquet`.
O stage `anonymize` propaga essas colunas automaticamente para o `id_map` em staging.

### 3. Remoção de IDs órfãos (purge)

Validar primeiro:

```bash
python scripts/main.py purge --base . --dry-run
```

Executar:

```bash
python scripts/main.py purge --base . --workers 6
```

Remove IDs que existem em apenas uma das bases (patients ou waveforms).

### 4. Anonimização

```bash
python scripts/main.py anonymize --base . --input-root output --output-root output/data --workers 8
```

Executa:
1. Auditoria completa before_anonymization
2. Hash + remoção de colunas sensíveis
3. Geração de datasets finais anonimizados
4. Auditoria completa after_anonymization

### 5. Pipeline do questionário (se aplicável)

Se você tem respostas exportadas do NeuroVision, execute os scripts abaixo em ordem a partir da raiz do projeto:

```bash
python scripts/questionnaire/step1_parse.py
python scripts/questionnaire/step2_link.py
python scripts/questionnaire/step3_features.py
python scripts/questionnaire/step4_anonymize.py
```

Os dados anonimizados do questionário ficam em `output/data/anonymized/datasets/questionnaire_*.parquet`.

### 6. Notebook de classificação

Com os dados anonimizados disponíveis em `output/data/anonymized/`, abra o notebook final:

```
studies/neurodivergencia_classification/notebooks/
  neurodivergencia_classification_describre_final.ipynb
```

## Estrutura de saída

```
output/
  patients/
  waveforms/consolidated/
  reports/
    id_audit/
    annotation/
  data/
    anonymized/
      staging/
        metadata_YYYYMMDD_HHMMSS.parquet
        waveforms_YYYYMMDD_HHMMSS.parquet
        patients_YYYYMMDD_HHMMSS.parquet
        id_map_YYYYMMDD_HHMMSS.parquet
      datasets/
        waveforms_YYYYMMDD_HHMMSS.parquet
        patients-features_YYYYMMDD_HHMMSS.parquet
        waveform_types_YYYYMMDD_HHMMSS.parquet
      reports/
        id_audit/
          before_anonymization/
          after_anonymization/
```

## Documentação de aprofundamento

- [Arquitetura da Pipeline](docs/01_arquitetura_pipeline.md)
- [Guia Operacional Passo a Passo](docs/02_guia_operacional.md)
- [Referência CLI scripts/main.py](docs/03_cli_principal.md)
- [Referência de Scripts Diretos](docs/04_scripts_diretos.md)
- [Saídas e Nomenclatura](docs/05_saidas_e_nomenclatura.md)
- [Auditoria de IDs](docs/06_auditoria_ids.md)
- [Pipeline de Classificação ERG](docs/CLASSIFICATION_PIPELINE.md)
- [Diagramas (componentes, fluxo, entidades, dependências)](docs/diagrams/)
