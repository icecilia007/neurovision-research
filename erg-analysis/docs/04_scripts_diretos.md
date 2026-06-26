# Referência de Scripts Diretos

Este documento cobre scripts executaveis diretamente, sem passar por `scripts/main.py`.

## 1) Preparação de pacientes

Script:
- `scripts/pipeline/raw_to_consolidated/patient_preparation.py`

Comando exemplo:

```bash
python scripts/pipeline/raw_to_consolidated/patient_preparation.py --base . --input exam --output output/patients --workers 6 --output-partitions 4
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--input` | str | Sim | - | Caminho relativo para buscar CSVs |
| `--base` | str | Não | `.` | Diretório base |
| `--output` | str | Sim | - | Diretorio de saida |
| `--workers` | int | Não | `None` | Workers paralelos |
| `--output-partitions` | int | Não | `None` | Particoes alvo no parquet |

Saídas principais:
- `patients-YYYYMMDD-HHMMSS.parquet`
- `patients_id_mapping-YYYYMMDD-HHMMSS.parquet`

---

## 2) Consolidação de waveforms

Script:
- `scripts/pipeline/raw_to_consolidated/waveform_consolidation.py`

Comando exemplo:

```bash
python scripts/pipeline/raw_to_consolidated/waveform_consolidation.py --base . --input waveform --output output/waveforms --workers 4 --metadata-partitions 4 --waveform-partitions 16 --max-records-per-file 1000000
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--input` | str | Sim | - | Pasta de CSVs brutos RETeval |
| `--base` | str | Não | `.` | Diretório base |
| `--output` | str | Sim | - | Diretorio de saida |
| `--workers` | int | Não | `None` | Workers paralelos |
| `--metadata-partitions` | int | Não | `None` | Partições do metadata consolidado |
| `--waveform-partitions` | int | Não | `None` | Partições do waveforms consolidado |
| `--max-records-per-file` | int | Não | `None` | Limite por arquivo Spark |
| `--spark-heartbeat-interval` | str | Não | `60s` | Heartbeat Spark |
| `--spark-network-timeout` | str | Não | `600s` | Timeout Spark |

Saídas principais:
- `output/waveforms/consolidated/consolidated_metadata.parquet`
- `output/waveforms/consolidated/consolidated_waveforms.parquet`

---

## 3) Extração de datasets ERG finais

Script:
- `scripts/processing/erg_dataset_extraction.py`

Comando exemplo:

```bash
python scripts/processing/erg_dataset_extraction.py --base . --input output/data/anonymized/staging --output output/data/anonymized/datasets --compact-names --name-date-suffix 20260417_101500 --skip-metadata-output
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--input` | str | Sim | - | Pasta com metadata/waveforms/patients |
| `--output` | str | Sim | - | Pasta de saida |
| `--base` | str | Não | `.` | Diretório base |
| `--workers` | int | Não | `None` | Threads de leitura |
| `--block-size-mb` | int | Não | `64` | Bloco CSV |
| `--name-prefix` | str | Não | `erg` | Prefixo no modo não compacto |
| `--compact-names` | flag | Não | `False` | Nomes curtos |
| `--name-date-suffix` | str | Não | `""` | Sufixo de data/hora |
| `--skip-metadata-output` | flag | Não | `False` | Não escrever metadata final |

---

## 4) Auditoria de IDs

Script:
- `scripts/analysis/audit_unique_patient_ids.py`

Comando exemplo (cross):

```bash
python scripts/analysis/audit_unique_patient_ids.py --base . --mode cross --patients-input output/patients/patients-20260417-092416.parquet --metadata-input output/waveforms/consolidated/consolidated_metadata.parquet --output output/reports/id_audit
```

Comando exemplo (before-after):

```bash
python scripts/analysis/audit_unique_patient_ids.py --base . --mode before-after --patients-before-input <antes_patients> --patients-after-input <depois_patients> --metadata-before-input <antes_metadata> --metadata-after-input <depois_metadata> --output output/reports/id_audit_compare
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--base` | str | Não | `.` | Diretório base |
| `--mode` | str | Não | `cross` | `cross` ou `before-after` |
| `--patients-input` | str | Condicional | - | Necessario em `cross` |
| `--metadata-input` | str | Condicional | - | Necessario em `cross` |
| `--patients-before-input` | str | Condicional | - | Necessario em `before-after` |
| `--patients-after-input` | str | Condicional | - | Necessario em `before-after` |
| `--metadata-before-input` | str | Condicional | - | Necessario em `before-after` |
| `--metadata-after-input` | str | Condicional | - | Necessario em `before-after` |
| `--output` | str | Sim | - | Pasta de saida de relatorios |

---

## 5) Extração espectral

Script:
- `scripts/processing/erg_spectral_extraction.py`

Comando exemplo:

```bash
python scripts/processing/erg_spectral_extraction.py --base . --input output/data/anonymized/datasets --output output/analysis/spectral --batch-size 50000 --num-buckets 64 --min-samples 32 --wavelet db4 --max-wavelet-levels 5 --output-file erg_spectral_features.csv --workers 6
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--input` | str | Sim | - | Pasta com arquivos ERG parquet |
| `--output` | str | Sim | - | Pasta de saida |
| `--base` | str | Não | `.` | Diretório base |
| `--batch-size` | int | Não | `50000` | Linhas por batch |
| `--num-buckets` | int | Não | `64` | Buckets temporarios |
| `--min-samples` | int | Não | `32` | Mínimo de pontos do sinal |
| `--wavelet` | str | Não | `db4` | Wavelet DWT |
| `--max-wavelet-levels` | int | Não | `5` | Níveis máximos de wavelet |
| `--output-file` | str | Não | `erg_spectral_features.csv` | Nome do arquivo final |
| `--workers` | int | Não | `cpu_count-1` | Processos paralelos |
| `--strict-metadata-uniqueness` | flag | Não | `False` | Falhar em ambiguidade de metadata |

---

## 6) Clusterização DBSCAN (densidade)

Script:
- `scripts/analysis/dbscan_density.py`

Comando exemplo:

```bash
python scripts/analysis/dbscan_density.py --base . --input output/analysis/spectral/erg_spectral_features.csv --output output/analysis/clustering --eps 0.5 --min-samples 10 --partition-mode waveform
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--input` | str | Não | `outputs/hashed/erg/erg_spectral_features.csv` | CSV de features |
| `--output` | str | Não | `outputs/hashed/erg/clustering` | Pasta de saida |
| `--base` | str | Não | `.` | Diretório base |
| `--eps` | float | Não | `0.5` | `eps` do DBSCAN |
| `--min-samples` | int | Não | `10` | `min_samples` do DBSCAN |
| `--pca-max-points` | int | Não | `5000` | Pontos maximos no PCA |
| `--random-seed` | int | Não | `42` | Semente de amostragem |
| `--pca-axis-percentile-low` | float | Não | `1.0` | Percentil inferior eixo robusto |
| `--pca-axis-percentile-high` | float | Não | `99.0` | Percentil superior eixo robusto |
| `--disable-pca-robust-axis` | flag | Não | `False` | Desativar viewport robusto |
| `--partition-mode` | str | Não | `waveform` | `waveform` ou `waveform_step` |

> **Atenção — caminhos legados:** Os defaults `--input` (`outputs/hashed/erg/erg_spectral_features.csv`) e `--output` (`outputs/hashed/erg/clustering`) usam uma estrutura de pastas anterior. Sempre passe `--input` e `--output` explicitamente, por exemplo: `--input output/analysis/spectral/erg_spectral_features.csv --output output/analysis/clustering`.
>
> **Pré-requisito:** execute o script 5 (`erg_spectral_extraction.py`) antes deste para gerar o arquivo de features espectrais.

---

## 7) Varredura de hiperparâmetros DBSCAN

Script:
- `scripts/analysis/dbscan_sweep.py`

Comando exemplo:

```bash
python scripts/analysis/dbscan_sweep.py --base . --input output/analysis/spectral/erg_spectral_features.csv --output output/analysis/dbscan_sweep --eps-values 0.2,0.3,0.5,0.8,1.0 --min-samples-values 8,10,12,16,20 --workers 6 --partition-mode waveform
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--input` | str | Não | `outputs/hashed/erg/erg_spectral_features.csv` | CSV de features |
| `--output` | str | Não | `outputs/hashed/erg/dbscan_sweep` | Pasta de saida |
| `--base` | str | Não | `.` | Diretório base |
| `--eps-values` | str csv | Não | `0.2,0.3,0.5,0.8,1.0` | Lista de `eps` |
| `--min-samples-values` | str csv | Não | `8,10,12,16,20` | Lista de `min_samples` |
| `--workers` | int | Não | `cpu_count-1` | Processos paralelos |
| `--partition-mode` | str | Não | `waveform` | `waveform` ou `waveform_step` |

> **Atenção — caminhos legados:** Os defaults `--input` (`outputs/hashed/erg/erg_spectral_features.csv`) e `--output` (`outputs/hashed/erg/dbscan_sweep`) usam uma estrutura de pastas anterior. Sempre passe `--input` e `--output` explicitamente.
>
> **Pré-requisito:** execute o script 5 (`erg_spectral_extraction.py`) antes deste para gerar o arquivo de features espectrais.

---

## 8) Preview de parquet

Script:
- `scripts/visualization/parquet_preview.py`

Comando exemplo (head simples):

```bash
python scripts/visualization/parquet_preview.py --base . --input output/data/anonymized/datasets --output output/previews --limit 10
```

Comando exemplo (preview por pacientes):

```bash
python scripts/visualization/parquet_preview.py --base . --input output/data/anonymized/datasets --output output/previews --num-patients 10
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--input` | str | Sim | - | Arquivo parquet ou pasta |
| `--output` | str | Sim | - | Pasta para CSVs de preview |
| `--base` | str | Não | `.` | Diretório base |
| `--limit` | int | Não | `10` | Linhas no modo head |
| `--num-patients` | int | Não | `None` | Ativa modo preview2 por pacientes |

---

## 9) Plot de waveforms por amostra de pacientes

Script:
- `scripts/visualization/waveform_sample_plot.py`

Comando exemplo:

```bash
python scripts/visualization/waveform_sample_plot.py --base . --input output/data/anonymized/datasets/waveforms_20260417_101500.parquet --output output/plots/waveforms --num-patients 10 --chunk-size 200000 --max-rows-per-patient 200000 --max-points-per-curve 3000
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--input` | str | Sim | - | Arquivo/pasta de waveforms |
| `--output` | str | Sim | - | Pasta de imagens |
| `--base` | str | Não | `.` | Diretório base |
| `--num-patients` | int | Não | `10` | Numero de pacientes |
| `--patient-ids` | str csv | Não | `None` | IDs especificos |
| `--chunk-size` | int | Não | `200000` | Chunk de leitura |
| `--max-rows-per-patient` | int | Não | `200000` | Limite de linhas por paciente |
| `--max-points-per-curve` | int | Não | `3000` | Maximo de pontos por curva |

Saidas:
- Arquivos `waveform_<patient_id>.png`
- Arquivo `selected_patients.txt`

---

## 10) Cruzamento de bases por ID com split condicional

Script:
- `scripts/analysis/records_split.py`

Cruza dois arquivos parquet por coluna de ID. Gera outputs separados para IDs não encontrados na base alvo, IDs encontrados com condicao TRUE e IDs encontrados com condicao FALSE. Usa Polars + PyArrow.

Comando exemplo (caso medico_records x data_right_eye):

```bash
python scripts/analysis/records_split.py \
  --base . \
  --reference-input patients-data/medical_records_history.parquet \
  --reference-id-col ID \
  --reference-extra-cols Nome,Neurodivergencia \
  --target-input patients-data/data_right_eye.parquet \
  --target-id-col PATIENT_ID \
  --target-cols PATIENT_ID,FIRST_NAME,LAST_NAME \
  --output output/reports/records_split \
  --conditional-col Neurodivergencia \
  --false-values "Nao tem|Nâo tem" \
  --output-format parquet
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--base` | str | Não | `.` | Diretório base |
| `--reference-input` | str | Sim | - | Parquet de referencia (base com IDs a buscar) |
| `--reference-id-col` | str | Sim | - | Coluna de ID na base de referencia |
| `--reference-extra-cols` | str csv | Não | `""` | Colunas adicionais da referência para incluir nos outputs |
| `--target-input` | str | Sim | - | Parquet alvo (onde buscar os IDs) |
| `--target-id-col` | str | Sim | - | Coluna de ID na base alvo |
| `--target-cols` | str csv | Sim | - | Colunas da base alvo a manter nos outputs |
| `--output` | str | Sim | - | Pasta de saida |
| `--conditional-col` | str | Não | `None` | Coluna da referencia para split TRUE/FALSE |
| `--false-values` | str pipe | Não | `""` | Valores que representam FALSE, separados por `|` |
| `--output-format` | str | Não | `parquet` | `parquet` ou `csv` |

Saidas geradas:

| Arquivo | Conteudo |
|---|---|
| `not_found_in_target.parquet` | IDs da referencia nao encontrados na base alvo |
| `found_conditional_true.parquet` | Matches onde condição é TRUE (inclui coluna condicional) |
| `found_conditional_false.parquet` | Matches onde condição é FALSE (sem coluna condicional) |
| `found_in_target.parquet` | Todos os matches (quando `--conditional-col` não é passado) |

Logs impressos:

- Contagem de linhas em cada base
- IDs únicos em cada base
- IDs encontrados / não encontrados
- IDs encontrados por split condicional TRUE e FALSE
- Aviso de colunas duplicadas por base

---

## 11) Anotação clínica do mapping

Script:
- `scripts/processing/annotate_patient_mapping.py`

Anota `patients_id_mapping-*.parquet` com `records_nome`, `neurodivergencia`, `laudo`, `sexo`, `erg`, `eye_tracking`, `fdt`, `sensibilidade_contraste` e `daltonismo` de `medical_records_history`. Usa Polars + PyArrow. Match por prontuário exato, fallback por prefixo de nome normalizado.

Comando exemplo:

```bash
python scripts/processing/annotate_patient_mapping.py \
  --base . \
  --records-input patients-data/medical_records_history.parquet \
  --mapping-root output/patients \
  --reports-output output/reports/annotation
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--base` | str | Não | `.` | Diretório base |
| `--records-input` | str | Não | `patients-data/medical_records_history.parquet` | medical_records_history parquet |
| `--mapping-root` | str | Não | `output/patients` | Raiz com patients_id_mapping |
| `--reports-output` | str | Não | `output/reports/annotation` | Pasta de relatorios |
| `--metadata-input` | str | Não | `output/waveforms/consolidated/consolidated_metadata.parquet` | consolidated_metadata (fallback de nome por prontuario) |
| `--dry-run` | flag | Não | `False` | Logar sem gravar |

> Nota: `--metadata-root` e `--coverage-reports-output` são argumentos do **stage** `annotate` via `scripts/main.py`, nao deste script direto. Para usar esses parametros, chame `python scripts/main.py annotate`.

---

## 12) Consolidação unificada com relatório de IDs

Script:
- `scripts/pipeline/raw_to_consolidated/consolidate_from_raw.py`

Executa `patient_preparation` + `waveform_consolidation` em sequencia e ao final gera o relatorio `id_audit` cross-report automaticamente. Preferir o stage `consolidate-and-audit` via `scripts/main.py`.

Comando exemplo:

```bash
python scripts/pipeline/raw_to_consolidated/consolidate_from_raw.py \
  --base . \
  --patients-input exam \
  --waveforms-input waveform \
  --patients-output output/patients \
  --waveforms-output output/waveforms \
  --reports-output output/reports/id_audit \
  --workers 6
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--base` | str | Não | `.` | Diretório base |
| `--patients-input` | str | Sim | - | Entrada de pacientes |
| `--waveforms-input` | str | Sim | - | Pasta com CSVs de waveform |
| `--patients-output` | str | Não | `output/patients` | Saida de patients |
| `--waveforms-output` | str | Não | `output/waveforms` | Saida de waveforms |
| `--reports-output` | str | Não | `output/reports/id_audit` | Pasta do relatorio id_audit |
| `--workers` | int | Não | `None` | Workers para os dois scripts |
| `--patients-partitions` | int | Não | `None` | Partições alvo do parquet de patients |
| `--metadata-partitions` | int | Não | `None` | Partições alvo de consolidated metadata |
| `--waveform-partitions` | int | Não | `None` | Partições alvo de consolidated waveforms |
| `--max-records-per-file` | int | Não | `None` | `spark.sql.files.maxRecordsPerFile` |

---

## 13) Remoção de IDs órfãos (purge)

Script:
- `scripts/pipeline/purge/purge_orphan_ids.py`

Lê `unique_ids_only_one_base_counts.csv` e remove linhas com IDs orfaos das bases consolidadas. IDs com `presence == only_patients` são removidos de `output/patients/`; IDs com `presence == only_metadata` são removidos de `output/waveforms/consolidated/`. Usa Spark por padrão para datasets grandes; `--no-spark` usa PyArrow.

Comando exemplo (validação prévia):

```bash
python scripts/pipeline/purge/purge_orphan_ids.py --base . --dry-run
```

Comando exemplo (execução):

```bash
python scripts/pipeline/purge/purge_orphan_ids.py --base . --workers 6
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--base` | str | Não | `.` | Diretório base |
| `--audit-input` | str | Não | `output/reports/id_audit/unique_ids_only_one_base_counts.csv` | CSV de auditoria |
| `--patients-root` | str | Não | `output/patients` | Raiz com parquets de patients |
| `--waveforms-root` | str | Não | `output/waveforms/consolidated` | Raiz com parquets de waveforms |
| `--audit-log-output` | str | Não | `output/reports/id_audit` | Pasta para o CSV de log do purge |
| `--workers` | int | Não | `None` | Workers Spark local |
| `--no-spark` | flag | Não | `False` | Usar PyArrow em vez de Spark |
| `--dry-run` | flag | Não | `False` | Logar sem gravar |

---

## 14) Pipeline de questionário

Scripts:
- `scripts/questionnaire/questionnaire_pipeline.py` — orquestrador principal (executa as fases 1–4 em sequência)
- `scripts/questionnaire/step1_parse.py` — fase 1: parse das respostas JSON
- `scripts/questionnaire/step2_link.py` — fase 2: linkage com bases ERG/RightEye
- `scripts/questionnaire/step3_features.py` — fase 3: extração de features
- `scripts/questionnaire/step4_anonymize.py` — fase 4: anonimização
- `scripts/questionnaire/record_linkage.py` — motor de linkage (usado internamente pelo orquestrador e pelo step2)

Uso recomendado — executar todas as fases via orquestrador:

```bash
python -m scripts.questionnaire.questionnaire_pipeline \
  --questionnaire-input <caminho/questionario.json> \
  --base .
```

Saídas geradas em `output/questionnaire/<questionnaire_id>/`:
- `linkage_confirmed.parquet/.csv` — respostas com match único confirmado
- `linkage_ambiguous.parquet/.csv` — respostas com múltiplos candidatos
- `linkage_not_found.parquet/.csv` — respostas sem match
- `linkage_explain.csv` — detalhes do score por resposta
- `linkage_report.txt` — relatório textual resumido
- `features_*.parquet/.csv` — features extraídas (fase 3)
- `anonymized_*.parquet/.csv` — dataset anonimizado final (fase 4)

Para executar fases individualmente, use `step1_parse.py`–`step4_anonymize.py` diretamente.
Cada step lê a saída do step anterior a partir de `output/questionnaire/<questionnaire_id>/`.

---

## 15) Scripts de suporte (sem CLI própria)

Os arquivos abaixo sao usados como modulos internos e não expõem `argparse` diretamente:

- `scripts/pipeline_utils.py`
- `scripts/pipeline/hashing/hash_orchestrator.py` (funcao chamada via stage `hash`)
- `scripts/pipeline/hashing/hash_mapping.py`
- `scripts/pipeline/hashing/hash_apply_streaming.py`
- `scripts/pipeline/hashing/normalize_patients.py`
- `scripts/pipeline/consolidated_to_parquet/parquet_generation.py`
- `scripts/pipeline/raw_to_consolidated/__init__.py`
- `scripts/pipeline/hashing/__init__.py`
- `scripts/pipeline/consolidated_to_parquet/__init__.py`
- `scripts/common/path_utils.py`
- `scripts/common/logging_utils.py`
- `scripts/common/id_utils.py`

Regra prática:
- Quando houver opção equivalente no `scripts/main.py`, prefira o entrypoint principal.
- Use scripts diretos apenas quando quiser controle avançado ou depuração especifica.
