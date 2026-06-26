# Documentação de Componentes

> Diagramas de fluxo por componente. Para descrições textuais de cada arquivo, ver [00_inventory.md](00_inventory.md).
## scripts/main.py

```mermaid
flowchart TD
    A[main.py] --> B[stage_runner.main]
```

## scripts/pipeline/stage_runner.py

```mermaid
flowchart TD
    A[stage_runner] --> B[consolidate]
    A --> C[consolidate-and-audit]
    A --> D[annotate]
    A --> E[hash]
    A --> F[parquet]
    A --> G[purge]
    A --> H[anonymize]
```

## scripts/pipeline_utils.py

```mermaid
flowchart TD
    A[pipeline_utils] --> B[read_csv_arrow]
    A --> C[PatientIDHasher]
    A --> D[ParquetChunkWriter]
    A --> E[MissingIdCsvWriter]
```

## scripts/pipeline/raw_to_consolidated/patient_preparation.py

```mermaid
flowchart TD
    A[patient_preparation] --> B[CSVs patients]
    A --> C[patients-*.parquet]
    A --> D[patients_id_mapping-*.parquet]
```

## scripts/pipeline/raw_to_consolidated/waveform_consolidation.py

```mermaid
flowchart TD
    A[waveform_consolidation] --> B[RETeval CSV]
    A --> C[metadata parquet]
    A --> D[waveforms parquet]
    C --> E[consolidated_metadata.parquet]
    D --> F[consolidated_waveforms.parquet]
```

## scripts/pipeline/raw_to_consolidated/consolidate_from_raw.py

```mermaid
flowchart TD
    A[consolidate_from_raw] --> B[patient_preparation]
    A --> C[waveform_consolidation]
    A --> D[audit_unique_patient_ids]
```

## scripts/pipeline/hashing/normalize_patients.py

```mermaid
flowchart TD
    A[normalize_patients] --> B[CSV inputs]
    A --> C[CSV normalized]
```

## scripts/pipeline/hashing/hash_mapping.py

```mermaid
flowchart TD
    A[hash_mapping] --> B[mapping CSV]
    A --> C[mapping.parquet]
```

## scripts/pipeline/hashing/hash_apply_streaming.py

```mermaid
flowchart TD
    A[hash_apply_streaming] --> B[mapping.parquet]
    A --> C[input CSV/Parquet]
    A --> D[hashed parquet]
    A --> E[missing_ids.csv]
```

## scripts/pipeline/hashing/hash_orchestrator.py

```mermaid
flowchart TD
    A[hash_orchestrator] --> B[normalize]
    A --> C[mapping]
    A --> D[apply]
```

## scripts/pipeline/consolidated_to_parquet/parquet_generation.py

```mermaid
flowchart TD
    A[parquet_generation] --> B[erg_dataset_extraction]
```

## scripts/pipeline/anonymize/anonymize_from_output.py

```mermaid
flowchart TD
    A[anonymize_from_output] --> B[id_audit before]
    A --> C[hash pipeline]
    A --> D[id_map enrichment]
    A --> E[parquet datasets]
    A --> F[id_audit after]
```

## scripts/pipeline/purge/purge_orphan_ids.py

```mermaid
flowchart TD
    A[purge_orphan_ids] --> B[unique_ids_only_one_base_counts.csv]
    A --> C[patients parquet]
    A --> D[waveforms parquet]
    A --> E[purge_log_*.csv]
```

## scripts/processing/erg_dataset_extraction.py

```mermaid
flowchart TD
    A[erg_dataset_extraction] --> B[consolidated_metadata]
    A --> C[consolidated_waveforms]
    A --> D[patients-*]
    A --> E[metadata.parquet]
    A --> F[waveforms.parquet]
    A --> G[patients-features.parquet]
    A --> H[waveform_types.parquet]
```

## scripts/processing/erg_spectral_extraction.py

```mermaid
flowchart TD
    A[erg_spectral_extraction] --> B[waveforms]
    A --> C[metadata dims]
    A --> D[bucket CSVs]
    D --> E[features CSV/Parquet]
```

## scripts/processing/annotate_patient_mapping.py

```mermaid
flowchart TD
    A[annotate_patient_mapping] --> B[patients_id_mapping]
    A --> C[medical_records_history]
    A --> D[annotation_audit]
    A --> E[unmatched_mapping]
```

## scripts/processing/add_gender_to_patients.py

```mermaid
flowchart TD
    A[add_gender_to_patients] --> B[patients_id_mapping]
    A --> C[gender_mapping.csv]
    A --> D[patients_id_mapping + sexo]
```

## scripts/analysis/audit_unique_patient_ids.py

```mermaid
flowchart TD
    A[audit_unique_patient_ids] --> B[patients dataset]
    A --> C[metadata dataset]
    A --> D[unique_ids_both_sources.csv]
    A --> E[unique_ids_only_one_base_counts.csv]
```

## scripts/analysis/audit_records_coverage.py

```mermaid
flowchart TD
    A[audit_records_coverage] --> B[medical_records_history]
    A --> C[patients_id_mapping]
    A --> D[consolidated_metadata]
    A --> E[coverage reports]
```

## scripts/analysis/records_split.py

```mermaid
flowchart TD
    A[records_split] --> B[reference parquet]
    A --> C[target parquet]
    A --> D[outputs split]
```

## scripts/analysis/dbscan_density.py

```mermaid
flowchart TD
    A[dbscan_density] --> B[erg_spectral_features.csv]
    A --> C[cluster outputs]
    A --> D[pca PNG]
```

## scripts/analysis/dbscan_sweep.py

```mermaid
flowchart TD
    A[dbscan_sweep] --> B[erg_spectral_features.csv]
    A --> C[dbscan_sweep_by_waveform.csv]
    A --> D[dbscan_sweep_global.csv]
```

## scripts/analysis/classification/data_prep.py

```mermaid
flowchart TD
    A[data_prep] --> B[features + labels]
    A --> C[train/test split]
```

## scripts/analysis/classification/pipeline.py

```mermaid
flowchart TD
    A[classification pipeline] --> B[preprocess]
    A --> C[model]
    A --> D[nested CV]
```

## scripts/analysis/classification/evaluation.py

```mermaid
flowchart TD
    A[evaluation] --> B[metrics]
    A --> C[confusion matrix]
```

## scripts/analysis/classification/feature_importance.py

```mermaid
flowchart TD
    A[feature_importance] --> B[importances DF]
```

## scripts/analysis/classification/persistence.py

```mermaid
flowchart TD
    A[persistence] --> B[training/test parquet]
    A --> C[model.joblib]
    A --> D[predictions parquet]
```

## scripts/questionnaire/record_linkage.py

```mermaid
flowchart TD
    A[record_linkage] --> B[questionnaire JSON]
    A --> C[patients_id_mapping]
    A --> D[right_eye]
    A --> E[linkage outputs]
```

## scripts/visualization/parquet_preview.py

```mermaid
flowchart TD
    A[parquet_preview] --> B[parquet datasets]
    A --> C[preview CSV]
```

## scripts/visualization/waveform_sample_plot.py

```mermaid
flowchart TD
    A[waveform_sample_plot] --> B[waveforms input]
    A --> C[PNG outputs]
```

## scripts/common/path_utils.py

```mermaid
flowchart TD
    A[path_utils] --> B[resolve_input_path]
    A --> C[resolve_output_dir]
```

## scripts/common/logging_utils.py

```mermaid
flowchart TD
    A[logging_utils] --> B[logs/pipeline_*.log]
```

## scripts/common/id_utils.py

```mermaid
flowchart TD
    A[id_utils] --> B[normalize_name]
    A --> C[build_patient_unique_id]
```

## scripts/common/name_utils.py

```mermaid
flowchart TD
    A[name_utils] --> B[variations]
```

## scripts/common/date_utils.py

```mermaid
flowchart TD
    A[date_utils] --> B[birth_year_range_expr]
```

## scripts/common/patient_lookup.py

```mermaid
flowchart TD
    A[patient_lookup] --> B[patient_table]
    A --> C[righteye_table]
```

## scripts/common/patient_utils.py

```mermaid
flowchart TD
    A[patient_utils] --> B[dob_year expr]
```

## scripts/common/value_utils.py

```mermaid
flowchart TD
    A[value_utils] --> B[bool/None]
```

## scripts/common/df_utils.py

```mermaid
flowchart TD
    A[df_utils] --> B[deduped DF]
```
