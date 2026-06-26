# Referência CLI Principal (`scripts/main.py`)

O entrypoint principal delega para `scripts/pipeline/stage_runner.py`.

Uso geral:

```bash
python scripts/main.py <stage> [opcoes]
```

Stages disponíveis:
- `consolidate`
- `consolidate-and-audit`
- `annotate`
- `hash`
- `parquet`
- `purge`
- `anonymize`

---

## Stage `consolidate`

Objetivo:
- Executar `patient_preparation` e `waveform_consolidation` em sequência.

Comando base:

```bash
python scripts/main.py consolidate --base . --patients-input exam --waveforms-input waveform
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--base` | str | Não | `.` | Diretório base |
| `--patients-input` | str | Sim | - | Entrada de pacientes (arquivo/pasta) |
| `--waveforms-input` | str | Sim | - | Pasta com CSVs de waveform |
| `--patients-output` | str | Não | `outputs/patients` | Saída de pacientes |
| `--waveforms-output` | str | Não | `outputs/waveforms` | Saída de waveforms |
| `--workers` | int | Não | `None` | Workers para os dois scripts |
| `--patients-partitions` | int | Não | `None` | Partições alvo do parquet de patients |
| `--metadata-partitions` | int | Não | `None` | Partições alvo de consolidated metadata |
| `--waveform-partitions` | int | Não | `None` | Partições alvo de consolidated waveforms |
| `--max-records-per-file` | int | Não | `None` | `spark.sql.files.maxRecordsPerFile` |

> **Atenção:** Os defaults `--patients-output` e `--waveforms-output` deste stage são `outputs/patients` e `outputs/waveforms` (com "s"), diferente dos demais stages que usam `output/`. Se você usar este stage com os defaults e depois rodar `purge`, `annotate` ou `anonymize`, os artefatos não serão encontrados.
> 
> **Recomendação:** sempre passe `--patients-output output/patients --waveforms-output output/waveforms` explicitamente, ou prefira `consolidate-and-audit` que já usa `output/` por padrão.

Nota Spark no Windows:
- Esse stage usa PySpark.
- Em WSL/Linux, não precisa de `winutils`.
- Em Windows nativo, configure Java + Hadoop e garanta `winutils.exe` e `hadoop.dll` em `HADOOP_HOME\\bin`.

---

## Stage `consolidate-and-audit`

Objetivo:
- Executar `patient_preparation`, `waveform_consolidation` e `audit_unique_patient_ids` (cross) em sequência.

Comando base:

```bash
python scripts/main.py consolidate-and-audit --base . --patients-input exam --waveforms-input waveform
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--base` | str | Não | `.` | Diretório base |
| `--patients-input` | str | Sim | - | Entrada de pacientes (arquivo/pasta) |
| `--waveforms-input` | str | Sim | - | Pasta com CSVs de waveform |
| `--patients-output` | str | Não | `output/patients` | Saída de pacientes |
| `--waveforms-output` | str | Não | `output/waveforms` | Saída de waveforms |
| `--reports-output` | str | Não | `output/reports/id_audit` | Pasta do relatorio id_audit |
| `--workers` | int | Não | `None` | Workers para os dois scripts |
| `--patients-partitions` | int | Não | `None` | Partições alvo do parquet de patients |
| `--metadata-partitions` | int | Não | `None` | Partições alvo de consolidated metadata |
| `--waveform-partitions` | int | Não | `None` | Partições alvo de consolidated waveforms |
| `--max-records-per-file` | int | Não | `None` | `spark.sql.files.maxRecordsPerFile` |

---

## Stage `annotate`

Objetivo:
- Anotar `patients_id_mapping` com dados clinicos de `medical_records_history`.
- Colunas anotadas: `records_nome`, `neurodivergencia`, `laudo`, `sexo`, `erg`, `eye_tracking`, `fdt`, `sensibilidade_contraste`, `daltonismo`.
- Match por prontuario exato, fallback por prefixo de nome normalizado.
- O `anonymize` propaga automaticamente as colunas anotadas para o `id_map` em staging.

Comando base:

```bash
python scripts/main.py annotate --base .
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--base` | str | Não | `.` | Diretório base |
| `--records-input` | str | Não | `patients-data/medical_records_history.parquet` | Caminho para medical_records_history |
| `--mapping-root` | str | Não | `output/patients` | Raiz com os arquivos patients_id_mapping |
| `--reports-output` | str | Não | `output/reports/annotation` | Pasta para relatórios de auditoria da anotacao |
| `--metadata-input` | str | Não | `output/waveforms/consolidated/consolidated_metadata.parquet` | consolidated_metadata (fallback de nome por prontuario) |
| `--metadata-root` | str | Não | `output/waveforms/consolidated` | Raiz com consolidated_metadata para auditoria de cobertura |
| `--coverage-reports-output` | str | Não | `output/reports/records_coverage` | Pasta para relatórios de cobertura de records |
| `--dry-run` | flag | Não | `False` | Logar sem gravar |

Saidas geradas:

| Arquivo | Conteudo |
|---|---|
| `patients_id_mapping-*.parquet` (in-place) | Colunas `records_nome`, `neurodivergencia`, `laudo` adicionadas |
| `annotation_audit_YYYYMMDD_HHMMSS.parquet` | Uma linha por patient_unique_id com `match_method` (prontuario/name_exact/name_prefix/not_found) |
| `unmatched_mapping_YYYYMMDD_HHMMSS.parquet` | Linhas do mapping sem correspondencia no records |
| `unmatched_mapping_YYYYMMDD_HHMMSS.csv` | Mesmo conteudo em CSV |

---

## Stage `hash`

Objetivo:
- Orquestrar normalização, geração de mapa hash e aplicacao streaming.

Comando base:

```bash
python scripts/main.py hash --base . --mapping-input <csv> --mapping-output <parquet> --apply-inputs <arquivos> --output-dir <dir> --debug-csv <csv>
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--base` | str | Não | `.` | Diretório base |
| `--normalize-inputs` | list[str] | Não | `None` | CSV(s) para normalizar inplace |
| `--mapping-input` | str | Sim | - | CSV de mapeamento de IDs |
| `--mapping-output` | str | Sim | - | Parquet do mapa hash |
| `--apply-inputs` | list[str] | Sim | - | Arquivos CSV/Parquet para aplicar hash |
| `--output-dir` | str | Sim | - | Diretorio de saida |
| `--debug-csv` | str | Sim | - | IDs sem hash |
| `--column` | str | Não | `patient_unique_id` | Coluna de ID |
| `--drop-columns` | str csv | Não | `source_file,id_prontuario,nome_paciente,data_nascimento` | Colunas a remover |
| `--float-columns` | str csv | Não | `voltage_uV,pupil_mm,time_ms` | Colunas float |
| `--int-columns` | str csv | Não | `test_id` | Colunas int |
| `--metadata-before` | str | Não | `None` | Metadata antes da correcao |
| `--metadata-after` | str | Não | `None` | Metadata depois da correcao |
| `--metadata` | str | Não | `None` | Metadata corrigido (modo simples) |
| `--chunk-size` | int | Não | `50000` | Tamanho de chunk |
| `--salt` | str | Não | `None` | Salt bcrypt |
| `--skip-normalize` | flag | Não | `False` | Pular normalize |
| `--skip-mapping` | flag | Não | `False` | Pular mapping |
| `--skip-apply` | flag | Não | `False` | Pular apply |

---

## Stage `parquet`

Objetivo:
- Gerar datasets analíticos a partir de metadata/waveforms/patients.

Comando base:

```bash
python scripts/main.py parquet --base . --input <dir> --output <dir>
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--base` | str | Não | `.` | Diretório base |
| `--input` | str | Sim | - | Pasta com metadata/waveforms/patients |
| `--output` | str | Sim | - | Pasta de saida |
| `--workers` | int | Não | `None` | Threads de leitura |
| `--block-size-mb` | int | Não | `64` | Bloco de leitura CSV |
| `--name-prefix` | str | Não | `erg` | Prefixo em modo não compacto |
| `--compact-names` | flag | Não | `False` | Nomes curtos |
| `--name-date-suffix` | str | Não | `""` | Sufixo de data/hora |
| `--skip-metadata-output` | flag | Não | `False` | Não gerar metadata final |

---

## Stage `anonymize`

Objetivo:
- Fluxo único completo de anonimização com auditoria before/after.

Comando base:

```bash
python scripts/main.py anonymize --base . --input-root output --output-root output/data --workers 8
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--base` | str | Não | `.` | Diretório base |
| `--input-root` | str | Não | `output` | Raiz com patients/ e waveforms/ |
| `--output-root` | str | Não | `output/data` | Raiz de saida do anonymize |
| `--reports-output` | str | Não | `None` | Override de pasta de relatórios |
| `--column` | str | Não | `patient_unique_id` | Coluna de ID |
| `--drop-columns` | str csv | Não | lista padrao extensa | Colunas removidas no hash |
| `--float-columns` | str csv | Não | `voltage_uV,pupil_mm,time_ms` | Colunas float |
| `--int-columns` | str csv | Não | `test_id` | Colunas int |
| `--chunk-size` | int | Não | `50000` | Chunk no hash |
| `--salt` | str | Não | `None` | Salt bcrypt |
| `--workers` | int | Não | `None` | Workers da etapa parquet |
| `--block-size-mb` | int | Não | `64` | Bloco da etapa parquet |

---

## Stage `purge`

Objetivo:
- Remover IDs órfãos das bases consolidadas com base no relatorio `unique_ids_only_one_base_counts.csv`.
- IDs `only_patients` são removidos de todos os parquets em `output/patients/`.
- IDs `only_metadata` são removidos de todos os parquets em `output/waveforms/consolidated/`.

Comando base:

```bash
python scripts/main.py purge --base . --dry-run
python scripts/main.py purge --base . --workers 6
```

Parametros:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `--base` | str | Não | `.` | Diretório base |
| `--audit-input` | str | Não | `output/reports/id_audit/unique_ids_only_one_base_counts.csv` | CSV de auditoria de IDs órfãos |
| `--patients-root` | str | Não | `output/patients` | Raiz com parquets de patients |
| `--waveforms-root` | str | Não | `output/waveforms/consolidated` | Raiz com parquets de waveforms |
| `--audit-log-output` | str | Não | `output/reports/id_audit` | Pasta para o CSV de log do purge |
| `--workers` | int | Não | `None` | Workers Spark local |
| `--no-spark` | flag | Não | `False` | Usar PyArrow em vez de Spark |
| `--dry-run` | flag | Não | `False` | Logar sem gravar (validacao previa) |

---

## Observação

Use `consolidate-and-audit` como entrypoint recomendado para consolidacao.
Use `purge` para limpar IDs inconsistentes antes de `anonymize`.
Use `anonymize` como nome oficial do fluxo único de anonimização.
