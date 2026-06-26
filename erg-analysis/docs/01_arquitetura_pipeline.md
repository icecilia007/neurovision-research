# Arquitetura da Pipeline

## Visão geral

A pipeline é organizada em estágios intencionais:

1. `consolidate`
- Prepara dataset de pacientes a partir de CSVs de `exam/`.
- Consolida metadados e séries de waveform a partir de CSVs de `waveform/`.

2. `consolidate-and-audit` (fluxo recomendado para consolidação)
- Executa `patient_preparation` + `waveform_consolidation` em sequência.
- Gera automaticamente o relatório `id_audit` cross-report ao final.
- Saídas: `output/patients/`, `output/waveforms/consolidated/`, `output/reports/id_audit/`.

3. `annotate` (opcional, após `consolidate-and-audit`)
- Lê `patients-data/medical_records_history.parquet`.
- Anota `records_nome`, `neurodivergencia` e `laudo` em todos os `patients_id_mapping-*.parquet`.
- Match por prontuário exato, fallback por prefixo de nome normalizado.
- Gera `output/reports/annotation/annotation_audit_*.parquet` (uma linha por patient_unique_id com match_method).
- Gera `output/reports/annotation/unmatched_mapping_*.{parquet,csv}` para linhas sem match.
- O `anonymize` propaga automaticamente essas colunas para o `id_map_*.parquet` em staging.

4. `purge` (opcional, após `consolidate-and-audit`)
- Lê `output/reports/id_audit/unique_ids_only_one_base_counts.csv`.
- Remove linhas de IDs `only_patients` de todos os parquets em `output/patients/`.
- Remove linhas de IDs `only_metadata` de todos os parquets em `output/waveforms/consolidated/`.
- Suporta `--dry-run` para validação prévia sem escrita.

5. `hash`
- Opcional para uso manual avançado.
- Normaliza IDs, gera mapa hash e aplica anonimização em datasets de entrada.

6. `parquet`
- Converte dados consolidados/hash para datasets finais de análise.

7. `anonymize` (fluxo recomendado para anonimização)
- Descobre automaticamente datasets em `output/`.
- Roda auditoria completa de IDs antes da anonimização.
- Roda hash + remoção de colunas sensíveis.
- Gera datasets finais com nomes curtos e sufixo de data/hora.
- Roda auditoria completa de IDs depois da anonimização.

## Entradas e saídas de alto nível

Entradas típicas:
- `exam/` (dados de pacientes)
- `waveform/` (CSV bruto RETeval)

Saídas intermediárias:
- `output/patients/`
- `output/waveforms/consolidated/`

Saídas de anonimização e análise:
- `output/data/anonymized/staging/`
- `output/data/anonymized/datasets/`
- `output/data/reports/id_audit/before_anonymization/`
- `output/data/reports/id_audit/after_anonymization/`

## Chaves de relação entre datasets

- `patient_unique_id`: identificador único do paciente/exame.
- `test_id`: identificador do teste dentro do exame.

Uso prático:
- `patients` traz atributos clínicos e de contexto.
- `waveforms` traz série temporal do sinal.
- `metadata` traz contexto de teste e parâmetros.

## Módulos principais

- `scripts/main.py`
- `scripts/pipeline/stage_runner.py`
- `scripts/pipeline/raw_to_consolidated/patient_preparation.py`
- `scripts/pipeline/raw_to_consolidated/waveform_consolidation.py`
- `scripts/pipeline/raw_to_consolidated/consolidate_from_raw.py` (backend do comando `consolidate-and-audit`)
- `scripts/pipeline/hashing/hash_orchestrator.py`
- `scripts/pipeline/anonymize/anonymize_from_output.py` (backend do comando `anonymize`)
- `scripts/pipeline/purge/purge_orphan_ids.py` (backend do comando `purge`)
- `scripts/processing/annotate_patient_mapping.py` (backend do comando `annotate`)
- `scripts/processing/erg_dataset_extraction.py`
- `scripts/analysis/audit_unique_patient_ids.py`
- `scripts/analysis/audit_records_coverage.py` (backend do segundo passo do stage `annotate`)
- `scripts/analysis/classification/` (pipeline de ML — ver [CLASSIFICATION_PIPELINE.md](CLASSIFICATION_PIPELINE.md))
- `scripts/questionnaire/questionnaire_pipeline.py` (orquestra `step1_parse.py`–`step4_anonymize.py`) e `scripts/questionnaire/record_linkage.py` (motor de linkage)

## Regras operacionais recomendadas

- Usar `consolidate-and-audit` em vez de `consolidate` para já obter o relatório de IDs na mesma execução.
- Rodar `annotate` para enriquecer o mapping com dados clínicos antes do `anonymize`.
- Rodar `purge` (opcionalmente com `--dry-run` primeiro) antes de passar para `anonymize`.
- Priorizar `scripts/main.py anonymize` para execução de produção pós-consolidação.
- Manter `output/` como área de trabalho de dados brutos e consolidados.
- Tratar `output/data/` como área de artefatos anonimizados e datasets finais.
- Sempre consultar os relatórios de `before_anonymization` e `after_anonymization` para validar integridade de IDs.
