# Saídas, Nomes de Arquivo e Estrutura de Pastas

## 1) Estrutura alvo após `anonymize`

```text
output/data/
  anonymized/
    staging/
      metadata_YYYYMMDD_HHMMSS.parquet
      waveforms_YYYYMMDD_HHMMSS.parquet
      patients_YYYYMMDD_HHMMSS.parquet
      id_map_YYYYMMDD_HHMMSS.parquet
      missing_ids_YYYYMMDD_HHMMSS.csv
    datasets/
      waveforms_YYYYMMDD_HHMMSS.parquet
      patients-features_YYYYMMDD_HHMMSS.parquet
      waveform_types_YYYYMMDD_HHMMSS.parquet
  reports/
    id_audit/
      before_anonymization/
      after_anonymization/
```

## 2) Convenções de nome

- Sufixo temporal padrão do fluxo `anonymize`:
  - `YYYYMMDD_HHMMSS`
- Nome de features final:
  - `patients-features` (origem: dataset patients)
- Nomes curtos nos datasets finais gerados pelo `anonymize`:
  - `waveforms`
  - `patients-features`
  - `waveform_types`

## 3) Relação entre entradas e saídas

Entrada consolidada típica:
- `consolidated_metadata.parquet`
- `consolidated_waveforms.parquet`
- `patients-*.parquet`

Saída de staging anônimo:
- `metadata_<run_tag>.parquet`
- `waveforms_<run_tag>.parquet`
- `patients_<run_tag>.parquet`

Saída final analítica:
- `waveforms_<run_tag>.parquet`
- `patients-features_<run_tag>.parquet`
- `waveform_types_<run_tag>.parquet`

## 4) Onde cada camada deve ser usada

- `output/`:
  - área de trabalho para dados brutos e consolidados.
- `output/data/anonymized/staging/`:
  - dados anonimizados ainda próximos da estrutura técnica da pipeline.
- `output/data/anonymized/datasets/`:
  - datasets finais para análise e consumo de ciência de dados.
- `output/data/reports/id_audit/`:
  - trilha de auditoria e validação de integridade de IDs.

## 5) Dicas de governança

- Não sobrescreva manualmente artefatos com sufixo de data/hora.
- Mantenha `run_tag` alinhado entre staging e datasets da mesma execução.
- Ao publicar resultado, sempre acompanhe os relatórios de auditoria before/after da mesma execução.
