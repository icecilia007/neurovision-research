# Rastreabilidade (funcao -> classe -> modulo -> pipeline -> arquivo)

## Pipeline: consolidate
| Funcao | Classe | Modulo | Stage | Arquivo |
|---|---|---|---|---|
| apply_target_partitions | N/A | patient_preparation | consolidate | scripts/pipeline/raw_to_consolidated/patient_preparation.py |
| find_csv_files | N/A | patient_preparation | consolidate | scripts/pipeline/raw_to_consolidated/patient_preparation.py |
| detect_encoding | N/A | patient_preparation | consolidate | scripts/pipeline/raw_to_consolidated/patient_preparation.py |
| build_spark_session | N/A | patient_preparation | consolidate | scripts/pipeline/raw_to_consolidated/patient_preparation.py |
| try_read_csv_rows_with_header_guesses | N/A | patient_preparation | consolidate | scripts/pipeline/raw_to_consolidated/patient_preparation.py |
| normalize_row_columns | N/A | patient_preparation | consolidate | scripts/pipeline/raw_to_consolidated/patient_preparation.py |
| build_patient_unique_id_from_row | N/A | patient_preparation | consolidate | scripts/pipeline/raw_to_consolidated/patient_preparation.py |
| process_file | N/A | patient_preparation | consolidate | scripts/pipeline/raw_to_consolidated/patient_preparation.py |
| run | N/A | patient_preparation | consolidate | scripts/pipeline/raw_to_consolidated/patient_preparation.py |
| apply_target_partitions | N/A | waveform_consolidation | consolidate | scripts/pipeline/raw_to_consolidated/waveform_consolidation.py |
| build_spark_session | N/A | waveform_consolidation | consolidate | scripts/pipeline/raw_to_consolidated/waveform_consolidation.py |
| process_reteval_csv | N/A | waveform_consolidation | consolidate | scripts/pipeline/raw_to_consolidated/waveform_consolidation.py |
| consolidate_files | N/A | waveform_consolidation | consolidate | scripts/pipeline/raw_to_consolidated/waveform_consolidation.py |
| run | N/A | waveform_consolidation | consolidate | scripts/pipeline/raw_to_consolidated/waveform_consolidation.py |

## Pipeline: consolidate-and-audit
| Funcao | Classe | Modulo | Stage | Arquivo |
|---|---|---|---|---|
| run | N/A | consolidate_from_raw | consolidate-and-audit | scripts/pipeline/raw_to_consolidated/consolidate_from_raw.py |
| run_cross | N/A | audit_unique_patient_ids | consolidate-and-audit | scripts/analysis/audit_unique_patient_ids.py |

## Pipeline: annotate
| Funcao | Classe | Modulo | Stage | Arquivo |
|---|---|---|---|---|
| run | N/A | annotate_patient_mapping | annotate | scripts/processing/annotate_patient_mapping.py |
| run | N/A | audit_records_coverage | annotate | scripts/analysis/audit_records_coverage.py |

## Pipeline: hash
| Funcao | Classe | Modulo | Stage | Arquivo |
|---|---|---|---|---|
| run | N/A | normalize_patients | hash | scripts/pipeline/hashing/normalize_patients.py |
| run | N/A | hash_mapping | hash | scripts/pipeline/hashing/hash_mapping.py |
| run | N/A | hash_apply_streaming | hash | scripts/pipeline/hashing/hash_apply_streaming.py |
| load_hash_mapping | N/A | pipeline_utils | hash | scripts/pipeline_utils.py |
| PatientIDHasher.hash_patient_id | PatientIDHasher | pipeline_utils | hash | scripts/pipeline_utils.py |

## Pipeline: parquet
| Funcao | Classe | Modulo | Stage | Arquivo |
|---|---|---|---|---|
| run | N/A | erg_dataset_extraction | parquet | scripts/processing/erg_dataset_extraction.py |

## Pipeline: purge
| Funcao | Classe | Modulo | Stage | Arquivo |
|---|---|---|---|---|
| run | N/A | purge_orphan_ids | purge | scripts/pipeline/purge/purge_orphan_ids.py |
| _purge_pyarrow | N/A | purge_orphan_ids | purge | scripts/pipeline/purge/purge_orphan_ids.py |
| _purge_spark | N/A | purge_orphan_ids | purge | scripts/pipeline/purge/purge_orphan_ids.py |
| PurgeRecord | PurgeRecord | purge_orphan_ids | purge | scripts/pipeline/purge/purge_orphan_ids.py |

## Pipeline: anonymize
| Funcao | Classe | Modulo | Stage | Arquivo |
|---|---|---|---|---|
| run | N/A | anonymize_from_output | anonymize | scripts/pipeline/anonymize/anonymize_from_output.py |
| _enrich_id_map_with_annotations | N/A | anonymize_from_output | anonymize | scripts/pipeline/anonymize/anonymize_from_output.py |
| run_before_after | N/A | audit_unique_patient_ids | anonymize | scripts/analysis/audit_unique_patient_ids.py |
| run | N/A | erg_dataset_extraction | anonymize | scripts/processing/erg_dataset_extraction.py |

## Fora do stage_runner (processos auxiliares)

### Spectral
| Funcao | Classe | Modulo | Stage | Arquivo |
|---|---|---|---|---|
| main | N/A | erg_spectral_extraction | spectral | scripts/processing/erg_spectral_extraction.py |
| bucketize_waveforms | N/A | erg_spectral_extraction | spectral | scripts/processing/erg_spectral_extraction.py |
| build_group_feature_row | N/A | erg_spectral_extraction | spectral | scripts/processing/erg_spectral_extraction.py |

### Record linkage
| Funcao | Classe | Modulo | Stage | Arquivo |
|---|---|---|---|---|
| run | N/A | record_linkage | linkage | scripts/questionnaire/record_linkage.py |
| match_record | N/A | record_linkage | linkage | scripts/questionnaire/record_linkage.py |
| _Query | _Query | record_linkage | linkage | scripts/questionnaire/record_linkage.py |

### ML (classification)
| Funcao | Classe | Modulo | Stage | Arquivo |
|---|---|---|---|---|
| build_classification_pipeline | N/A | classification.pipeline | ml | scripts/analysis/classification/pipeline.py |
| nested_cv_select_hyperparams | N/A | classification.pipeline | ml | scripts/analysis/classification/pipeline.py |
| evaluate_model | N/A | classification.evaluation | ml | scripts/analysis/classification/evaluation.py |
| run_feature_importance | N/A | classification.feature_importance | ml | scripts/analysis/classification/feature_importance.py |
| save_model | N/A | classification.persistence | ml | scripts/analysis/classification/persistence.py |

### Visualization
| Funcao | Classe | Modulo | Stage | Arquivo |
|---|---|---|---|---|
| main | N/A | parquet_preview | visualization | scripts/visualization/parquet_preview.py |
| main | N/A | waveform_sample_plot | visualization | scripts/visualization/waveform_sample_plot.py |

## Observacao
- Funcoes utilitarias em common/* e pipeline_utils sao consumidas transversalmente e nao pertencem a um stage unico.
