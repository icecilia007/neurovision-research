# Fluxo de Dados

## Fontes Primárias
- patients CSV: dados de pacientes (prontuario, nome, birth, test date).
- waveforms CSV (RETeval): metadata + series temporais.
- medical_records_history.parquet: historico clinico.
- questionnaire JSON: respostas do questionario.
- RightEye parquet: base externa para linkage.

## Fluxo principal (raw -> consolidated -> datasets)
```mermaid
flowchart LR
    A[patients CSV] --> B[patients-*.parquet]
    A --> C[patients_id_mapping-*.parquet]

    D[RETeval CSV] --> E[consolidated_metadata.parquet]
    D --> F[consolidated_waveforms.parquet]

    B --> G[erg_dataset_extraction]
    E --> G
    F --> G
    G --> H[metadata.parquet]
    G --> I[waveforms.parquet]
    G --> J[patients-features.parquet]
    G --> K[waveform_types.parquet]
```

## Fluxo de hashing
```mermaid
flowchart LR
    A[inputs CSV/Parquet] --> B[normalize_patients]
    B --> C[mapping.parquet]
    C --> D[hash_apply_streaming]
    D --> E[hashed parquets]
    D --> F[missing_ids.csv]
```

## Fluxo de anonimizar output/
```mermaid
flowchart TD
    A[output/patients + output/waveforms] --> B[audit_unique_patient_ids before]
    B --> C[hash pipeline]
    C --> D[id_map enriched]
    C --> E[staging hashed parquets]
    E --> F[erg_dataset_extraction]
    F --> G[datasets anonymized]
    G --> H[audit_unique_patient_ids after]
```

## Fluxo de linkage (questionnaire)
```mermaid
flowchart TD
    A[questionnaire JSON] --> B[record_linkage]
    C[medical_records_history] --> B
    D[patients_id_mapping] --> B
    E[right_eye] --> B
    B --> F[linkage_results]
    B --> G[confirmed/ambiguous/not_found]
```

## Entidades e chaves principais
- patient_unique_id:
  - origem: patient_preparation (CSV patients) e waveform_consolidation (filename/metadata)
  - uso: join entre patients, metadata e waveforms
- test_id:
  - origem: waveform_consolidation (contagem por test_no)
  - uso: distinguir exames no mesmo paciente
- waveform_type:
  - origem: metadata do RETeval
  - uso: derivar waveform_type_id e features
- waveform_type_id:
  - origem: erg_dataset_extraction (mapeamento)
  - uso: features espectrais e agrupamentos

## Transformações principais
1) Normalização de IDs
- ID bruto -> patient_unique_id canonical
- patient_unique_id -> hashed (bcrypt)

2) Consolidação de waveforms
- CSV RETeval -> metadata parquet
- CSV RETeval -> waveforms parquet (time_ms, signal, test_id)

3) Datasets finais
- metadata: limpa colunas sensiveis
- waveforms: agrega waveform_type_id
- features: extrai colunas com prefixo feature_ (patients)
- waveform_types: dicionario de tipos

## Relatórios e auditorias
- unique_ids_both_sources.csv: IDs comuns entre patients e metadata.
- unique_ids_only_one_base_counts.csv: IDs presentes em apenas uma base (para purge).
- annotation_audit_*.parquet: revisao de enrichment clinico.
- records_*.parquet/csv: cobertura de prontuarios.
- processing_errors.txt: CSVs RETeval com erro.
