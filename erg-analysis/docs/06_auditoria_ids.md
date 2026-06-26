# Auditoria de IDs (Before/After Anonymization)

## Objetivo

Garantir que a anonimização preserve a integridade da base em termos de IDs únicos.

A estratégia atual executa o mesmo relatório completo em dois snapshots:
- `before_anonymization`
- `after_anonymization`

Depois, o fluxo valida contagens entre os dois snapshots.

## Script usado

- `scripts/analysis/audit_unique_patient_ids.py`

Modo principal no fluxo `anonymize`:
- `mode=cross` antes da anonimização
- `mode=cross` depois da anonimização

## Pastas de saída

- `output/data/reports/id_audit/before_anonymization/`
- `output/data/reports/id_audit/after_anonymization/`

## Arquivos gerados no modo `cross`

Cada pasta (`before_anonymization` e `after_anonymization`) gera:

1. `unique_ids_both_sources.csv`
- Tabela de IDs únicos das duas bases (patients e metadata).

2. `unique_id_counts_summary.csv`
- Contagens agregadas:
  - `patients_unique_ids`
  - `metadata_unique_ids`
  - `ids_in_both`
  - `ids_only_patients`
  - `ids_only_metadata`

3. `unique_ids_comparison.csv`
- Comparação linha a linha de presença (`both`, `only_patients`, `only_metadata`).

4. `unique_ids_only_one_base_counts.csv`
- Detalhamento dos IDs exclusivos de apenas uma base, com contagem de linhas por origem.

5. `unique_ids_only_one_base_summary.csv`
- Agregado dos exclusivos por tipo de presença.

## Validação automática no `anonymize`

No final, o fluxo compara os dois `unique_id_counts_summary.csv`:

- Before: `.../before_anonymization/unique_id_counts_summary.csv`
- After: `.../after_anonymization/unique_id_counts_summary.csv`

Regra:
- `patients_unique_ids` deve permanecer igual.
- `metadata_unique_ids` deve permanecer igual.

Se mudar:
- O processo registra warning de mudança de cardinalidade após anonimização.

## Quando usar `mode=before-after`

`mode=before-after` continua útil para comparação direta de dois snapshots específicos. Exemplo:

```bash
python scripts/analysis/audit_unique_patient_ids.py \
  --base . \
  --mode before-after \
  --patients-before-input <p_before> \
  --patients-after-input <p_after> \
  --metadata-before-input <m_before> \
  --metadata-after-input <m_after> \
  --output output/reports/id_audit_compare
```

Arquivos gerados nesse modo:
- `before_after_patients_unique_ids_comparison.csv`
- `before_after_metadata_unique_ids_comparison.csv`
- `before_after_counts_summary.csv`

## Boas práticas

- Sempre guardar before e after da mesma execução de anonymize.
- Publicar dados finais junto com os relatórios de auditoria.
- Investigar qualquer diferença em IDs únicos antes de seguir para análises estatísticas.
