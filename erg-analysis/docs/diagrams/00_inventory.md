# Estrutura do Projeto

scripts/
├── analysis/
│   ├── __init__.py
│   ├── audit_records_coverage.py
│   ├── audit_unique_patient_ids.py
│   ├── dbscan_density.py
│   ├── dbscan_sweep.py
│   ├── records_split.py
│   └── classification/
│       ├── __init__.py
│       ├── data_prep.py
│       ├── evaluation.py
│       ├── feature_importance.py
│       ├── persistence.py
│       └── pipeline.py
├── common/
│   ├── __init__.py
│   ├── date_utils.py
│   ├── df_utils.py
│   ├── id_utils.py
│   ├── logging_utils.py
│   ├── name_utils.py
│   ├── path_utils.py
│   ├── patient_lookup.py
│   ├── patient_utils.py
│   └── value_utils.py
├── pipeline/
│   ├── __init__.py
│   ├── stage_runner.py
│   ├── anonymize/
│   │   ├── __init__.py
│   │   └── anonymize_from_output.py
│   ├── consolidated_to_parquet/
│   │   ├── __init__.py
│   │   └── parquet_generation.py
│   ├── hashing/
│   │   ├── __init__.py
│   │   ├── hash_apply_streaming.py
│   │   ├── hash_mapping.py
│   │   ├── hash_orchestrator.py
│   │   └── normalize_patients.py
│   ├── purge/
│   │   ├── __init__.py
│   │   └── purge_orphan_ids.py
│   └── raw_to_consolidated/
│       ├── __init__.py
│       ├── consolidate_from_raw.py
│       ├── patient_preparation.py
│       └── waveform_consolidation.py
├── processing/
│   ├── __init__.py
│   ├── add_gender_to_patients.py
│   ├── annotate_patient_mapping.py
│   ├── erg_dataset_extraction.py
│   └── erg_spectral_extraction.py
├── questionnaire/
│   ├── __init__.py
│   ├── questionnaire_pipeline.py
│   ├── record_linkage.py
│   ├── step1_parse.py
│   ├── step2_link.py
│   ├── step3_features.py
│   └── step4_anonymize.py
├── visualization/
│   ├── __init__.py
│   ├── parquet_preview.py
│   └── waveform_sample_plot.py
├── main.py
└── pipeline_utils.py

---

## scripts/main.py
- Nome: main.py
- Caminho: scripts/main.py
- Responsabilidade: entrypoint CLI principal (delegacao para pipeline.stage_runner.main).
- Dependencias importadas: pipeline.stage_runner
- Quem o utiliza: usuarios via CLI; docs/03_cli_principal.md
- O que consome: argumentos CLI do stage runner
- O que produz: depende do stage escolhido (ver stage_runner)

## scripts/pipeline_utils.py
- Nome: pipeline_utils.py
- Caminho: scripts/pipeline_utils.py
- Responsabilidade: utilitarios de leitura CSV com PyArrow, normalizacao de ID, hash bcrypt, escrita parquet por chunk, e helpers de mapeamento.
- Dependencias importadas: bcrypt, chardet, polars, pyarrow, dotenv, common.id_utils
- Quem o utiliza: pipeline/hashing/hash_mapping.py, pipeline/hashing/hash_apply_streaming.py, pipeline/hashing/normalize_patients.py, pipeline/anonymize/anonymize_from_output.py
- O que consome: CSVs de entrada; .env (BCRYPT_SALT)
- O que produz: parquet de mapping hash; CSV de missing IDs; parquet staging via ParquetChunkWriter

## scripts/pipeline/stage_runner.py
- Nome: stage_runner.py
- Caminho: scripts/pipeline/stage_runner.py
- Responsabilidade: CLI orquestrador de stages (consolidate, consolidate-and-audit, annotate, hash, parquet, purge, anonymize).
- Dependencias importadas: pipeline.raw_to_consolidated, pipeline.hashing, pipeline.consolidated_to_parquet, pipeline.purge, pipeline.anonymize, processing.annotate_patient_mapping, analysis.audit_records_coverage, common.logging_utils
- Quem o utiliza: scripts/main.py
- O que consome: argumentos CLI
- O que produz: outputs dos stages (parquets, CSVs e relatorios)

## scripts/pipeline/__init__.py
- Nome: __init__.py
- Caminho: scripts/pipeline/__init__.py
- Responsabilidade: expor wrappers de run_* para uso externo.
- Dependencias importadas: pipeline.raw_to_consolidated, pipeline.consolidated_to_parquet, pipeline.hashing, pipeline.anonymize, pipeline.purge
- Quem o utiliza: scripts/main.py e consumidores externos
- O que consome: N/A
- O que produz: N/A

## scripts/pipeline/raw_to_consolidated/__init__.py
- Nome: __init__.py
- Caminho: scripts/pipeline/raw_to_consolidated/__init__.py
- Responsabilidade: expor runners de consolidacao (patients, waveforms, consolidate_from_raw).
- Dependencias importadas: patient_preparation, waveform_consolidation, consolidate_from_raw
- Quem o utiliza: pipeline.stage_runner, pipeline.__init__
- O que consome: N/A
- O que produz: N/A

## scripts/pipeline/raw_to_consolidated/patient_preparation.py
- Nome: patient_preparation.py
- Caminho: scripts/pipeline/raw_to_consolidated/patient_preparation.py
- Responsabilidade: ler CSVs de patients, gerar patient_unique_id e escrever parquets patients e patients_id_mapping.
- Dependencias importadas: pyspark, chardet, common.id_utils, common.path_utils, common.logging_utils
- Quem o utiliza: pipeline.stage_runner (stage consolidate), pipeline/consolidate_from_raw
- O que consome: CSVs de patients (diretorio/arquivo)
- O que produz: output/patients/patients-*.parquet, patients_id_mapping-*.parquet, temporarios JSONL

## scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
- Nome: waveform_consolidation.py
- Caminho: scripts/pipeline/raw_to_consolidated/waveform_consolidation.py
- Responsabilidade: ler CSVs RETeval, extrair metadata/waveforms, gerar parquets temporarios e consolidar via Spark.
- Dependencias importadas: pyspark, pyarrow, common.id_utils, common.path_utils, common.logging_utils
- Quem o utiliza: pipeline.stage_runner (stage consolidate), pipeline/consolidate_from_raw
- O que consome: CSVs de waveforms (RETeval)
- O que produz: output/waveforms/*_metadata.parquet, *_waveforms.parquet, output/waveforms/consolidated/consolidated_metadata.parquet, consolidated_waveforms.parquet, processing_errors.txt

## scripts/pipeline/raw_to_consolidated/consolidate_from_raw.py
- Nome: consolidate_from_raw.py
- Caminho: scripts/pipeline/raw_to_consolidated/consolidate_from_raw.py
- Responsabilidade: executar patient_preparation + waveform_consolidation e rodar audit_unique_patient_ids (cross).
- Dependencias importadas: analysis.audit_unique_patient_ids, common.path_utils
- Quem o utiliza: pipeline.stage_runner (stage consolidate-and-audit)
- O que consome: CSVs de patients e waveforms
- O que produz: outputs de consolidacao + relatorio id_audit

## scripts/pipeline/hashing/__init__.py
- Nome: __init__.py
- Caminho: scripts/pipeline/hashing/__init__.py
- Responsabilidade: expor run_hash_orchestrator.
- Dependencias importadas: hash_orchestrator
- Quem o utiliza: pipeline.stage_runner, pipeline.anonymize
- O que consome: N/A
- O que produz: N/A

## scripts/pipeline/hashing/normalize_patients.py
- Nome: normalize_patients.py
- Caminho: scripts/pipeline/hashing/normalize_patients.py
- Responsabilidade: normalizar patient_unique_id em CSVs.
- Dependencias importadas: polars, pipeline_utils
- Quem o utiliza: hash_orchestrator
- O que consome: CSVs com coluna patient_unique_id
- O que produz: CSV normalizado (in-place ou em output_dir)

## scripts/pipeline/hashing/hash_mapping.py
- Nome: hash_mapping.py
- Caminho: scripts/pipeline/hashing/hash_mapping.py
- Responsabilidade: gerar parquet de mapping (patient_unique_id -> patient_unique_id_hashed).
- Dependencias importadas: polars, pipeline_utils
- Quem o utiliza: hash_orchestrator
- O que consome: CSV de mapping
- O que produz: parquet de mapping

## scripts/pipeline/hashing/hash_apply_streaming.py
- Nome: hash_apply_streaming.py
- Caminho: scripts/pipeline/hashing/hash_apply_streaming.py
- Responsabilidade: aplicar mapping hash a CSV/Parquet em streaming e escrever parquets hash.
- Dependencias importadas: polars, pyarrow, pipeline_utils
- Quem o utiliza: hash_orchestrator
- O que consome: arquivos CSV/Parquet; mapping parquet; metadata para corrigir IDs
- O que produz: parquets hash (metadata/waveforms/patients), CSV de IDs sem hash

## scripts/pipeline/hashing/hash_orchestrator.py
- Nome: hash_orchestrator.py
- Caminho: scripts/pipeline/hashing/hash_orchestrator.py
- Responsabilidade: orquestrar normalize -> mapping -> apply.
- Dependencias importadas: normalize_patients, hash_mapping, hash_apply_streaming
- Quem o utiliza: pipeline.stage_runner (stage hash), pipeline.anonymize
- O que consome: args CLI (inputs, mapping, output_dir, debug_csv)
- O que produz: outputs dos sub-stages

## scripts/pipeline/consolidated_to_parquet/__init__.py
- Nome: __init__.py
- Caminho: scripts/pipeline/consolidated_to_parquet/__init__.py
- Responsabilidade: expor run_consolidated_to_parquet.
- Dependencias importadas: parquet_generation
- Quem o utiliza: pipeline.stage_runner, pipeline.anonymize
- O que consome: N/A
- O que produz: N/A

## scripts/pipeline/consolidated_to_parquet/parquet_generation.py
- Nome: parquet_generation.py
- Caminho: scripts/pipeline/consolidated_to_parquet/parquet_generation.py
- Responsabilidade: bridge para processing.erg_dataset_extraction.
- Dependencias importadas: processing.erg_dataset_extraction
- Quem o utiliza: pipeline.stage_runner (stage parquet), pipeline.anonymize
- O que consome: args CLI de parquet
- O que produz: datasets finais de ERG

## scripts/pipeline/purge/__init__.py
- Nome: __init__.py
- Caminho: scripts/pipeline/purge/__init__.py
- Responsabilidade: expor run_purge_orphan_ids.
- Dependencias importadas: purge_orphan_ids
- Quem o utiliza: pipeline.stage_runner (stage purge)
- O que consome: N/A
- O que produz: N/A

## scripts/pipeline/purge/purge_orphan_ids.py
- Nome: purge_orphan_ids.py
- Caminho: scripts/pipeline/purge/purge_orphan_ids.py
- Responsabilidade: remover IDs orfaos de patients e consolidated metadata/waveforms.
- Dependencias importadas: pandas, pyarrow, pyspark (opcional), common.path_utils
- Quem o utiliza: pipeline.stage_runner (stage purge)
- O que consome: unique_ids_only_one_base_counts.csv; parquets em output/patients e output/waveforms/consolidated
- O que produz: parquets reescritos; purge_log_*.csv

## scripts/pipeline/anonymize/__init__.py
- Nome: __init__.py
- Caminho: scripts/pipeline/anonymize/__init__.py
- Responsabilidade: expor run_anonymize_from_output.
- Dependencias importadas: anonymize_from_output
- Quem o utiliza: pipeline.stage_runner (stage anonymize)
- O que consome: N/A
- O que produz: N/A

## scripts/pipeline/anonymize/anonymize_from_output.py
- Nome: anonymize_from_output.py
- Caminho: scripts/pipeline/anonymize/anonymize_from_output.py
- Responsabilidade: fluxo end-to-end de anonimização (audit before/after, hash, datasets finais).
- Dependencias importadas: analysis.audit_unique_patient_ids, pipeline.hashing, pipeline.consolidated_to_parquet, processing.annotate_patient_mapping.ANNOTATE_COLS, common.patient_utils
- Quem o utiliza: pipeline.stage_runner (stage anonymize)
- O que consome: datasets em output/ (patients, metadata, waveforms)
- O que produz: output/data/anonymized/staging (parquets hash), output/data/anonymized/datasets (parquets finais), relatorios id_audit before/after, id_map enriquecido

## scripts/processing/erg_dataset_extraction.py
- Nome: erg_dataset_extraction.py
- Caminho: scripts/processing/erg_dataset_extraction.py
- Responsabilidade: limpar metadata sensivel, preparar waveforms, gerar features e waveform_types.
- Dependencias importadas: pandas, pyarrow, common.path_utils, common.logging_utils
- Quem o utiliza: pipeline.consolidated_to_parquet
- O que consome: consolidated_metadata, consolidated_waveforms, patients parquets/CSVs
- O que produz: metadata.parquet (opcional), waveforms.parquet, patients-features.parquet/CSV, waveform_types.parquet/CSV

## scripts/processing/erg_spectral_extraction.py
- Nome: erg_spectral_extraction.py
- Caminho: scripts/processing/erg_spectral_extraction.py
- Responsabilidade: extrair descritores espectrais (FFT, Welch, Wavelet) por waveform.
- Dependencias importadas: numpy, pandas, pyarrow, pywt, scipy.signal.welch
- Quem o utiliza: usuarios via CLI
- O que consome: waveforms parquets/CSVs e metadata dims
- O que produz: erg_spectral_features.csv/parquet; logs tmp/logs

## scripts/processing/annotate_patient_mapping.py
- Nome: annotate_patient_mapping.py
- Caminho: scripts/processing/annotate_patient_mapping.py
- Responsabilidade: enriquecer patients_id_mapping com dados clinicos (records_nome, neurodivergencia, laudo, sexo, flags).
- Dependencias importadas: polars, pyarrow, common.id_utils, common.value_utils, common.path_utils
- Quem o utiliza: pipeline.stage_runner (stage annotate); pipeline.anonymize (usa ANNOTATE_COLS)
- O que consome: medical_records_history.parquet; patients_id_mapping-*.parquet; consolidated_metadata (opcional)
- O que produz: patients_id_mapping atualizado, annotation_audit_*.parquet, unmatched_mapping_*.parquet/CSV

## scripts/processing/add_gender_to_patients.py
- Nome: add_gender_to_patients.py
- Caminho: scripts/processing/add_gender_to_patients.py
- Responsabilidade: join de sexo em patients_id_mapping via nome_completo.
- Dependencias importadas: polars, common.logging_utils
- Quem o utiliza: usuarios via CLI
- O que consome: parquet patients_id_mapping; CSV gender_mapping
- O que produz: parquet enriquecido com sexo

## scripts/analysis/audit_unique_patient_ids.py
- Nome: audit_unique_patient_ids.py
- Caminho: scripts/analysis/audit_unique_patient_ids.py
- Responsabilidade: auditar IDs unicos entre patients e consolidated_metadata; modo cross e before-after.
- Dependencias importadas: pandas, common.id_utils, common.path_utils
- Quem o utiliza: consolidate_from_raw, anonymize_from_output, usuarios via CLI
- O que consome: parquets/CSVs de patients e metadata
- O que produz: unique_ids_both_sources.csv, unique_id_counts_summary.csv, unique_ids_comparison.csv, unique_ids_only_one_base_counts.csv, summarys before/after

## scripts/analysis/audit_records_coverage.py
- Nome: audit_records_coverage.py
- Caminho: scripts/analysis/audit_records_coverage.py
- Responsabilidade: auditar cobertura entre medical_records_history e bases da pipeline.
- Dependencias importadas: polars, common.id_utils, common.value_utils, common.path_utils, common.df_utils
- Quem o utiliza: pipeline.stage_runner (stage annotate)
- O que consome: medical_records_history.parquet, patients_id_mapping parquets, consolidated_metadata parquets
- O que produz: relatorios records_not_in_bases, bases_not_in_records, records_erg_found, records_erg_not_found, records_no_erg_found

## scripts/analysis/records_split.py
- Nome: records_split.py
- Caminho: scripts/analysis/records_split.py
- Responsabilidade: cruzar duas bases parquet por ID e gerar splits opcionais por coluna condicional.
- Dependencias importadas: polars, pyarrow, common.path_utils
- Quem o utiliza: usuarios via CLI
- O que consome: parquets referencia e alvo
- O que produz: not_found_in_target, found_in_target ou found_conditional_true/false (parquet/csv)

## scripts/analysis/dbscan_density.py
- Nome: dbscan_density.py
- Caminho: scripts/analysis/dbscan_density.py
- Responsabilidade: clustering DBSCAN por waveform_type (ou waveform_type + TestStepType), com PCA para visualizacao.
- Dependencias importadas: pandas, numpy, sklearn, matplotlib
- Quem o utiliza: usuarios via CLI
- O que consome: CSV de features espectrais
- O que produz: erg_spectral_clustered.csv, cluster_counts.csv, cluster_noise_summary.csv, cluster_feature_means.csv, cluster_distribution_by_testtype.csv, cluster_distribution_by_teststeptype.csv, pca_clusters_*.png

## scripts/analysis/dbscan_sweep.py
- Nome: dbscan_sweep.py
- Caminho: scripts/analysis/dbscan_sweep.py
- Responsabilidade: varrer grid de eps/min_samples e sumarizar ruido por particao.
- Dependencias importadas: pandas, numpy, sklearn, cluster_erg_density (alias do dbscan_density)
- Quem o utiliza: usuarios via CLI
- O que consome: CSV de features espectrais
- O que produz: dbscan_sweep_by_waveform.csv, dbscan_sweep_global.csv

## scripts/analysis/classification/__init__.py
- Nome: __init__.py
- Caminho: scripts/analysis/classification/__init__.py
- Responsabilidade: re-export de funcoes de preparacao, pipeline, avaliacao e persistencia.
- Dependencias importadas: data_prep, pipeline, evaluation, feature_importance, persistence
- Quem o utiliza: consumidores externos
- O que consome: N/A
- O que produz: N/A

## scripts/analysis/classification/data_prep.py
- Nome: data_prep.py
- Caminho: scripts/analysis/classification/data_prep.py
- Responsabilidade: preparar datasets para ML (binarizacao, multilabel, join de labels, agregacao por paciente, split).
- Dependencias importadas: polars, sklearn.model_selection
- Quem o utiliza: pipelines de classificacao
- O que consome: DataFrames Polars
- O que produz: DataFrames Polars e matrizes pandas/numpy para sklearn

## scripts/analysis/classification/pipeline.py
- Nome: pipeline.py
- Caminho: scripts/analysis/classification/pipeline.py
- Responsabilidade: construir Pipeline sklearn e executar nested CV (binary, multiclass, multilabel).
- Dependencias importadas: sklearn, numpy, polars
- Quem o utiliza: pipelines de classificacao
- O que consome: X, y (numpy) e param_grid
- O que produz: best_params e sumarios de CV

## scripts/analysis/classification/evaluation.py
- Nome: evaluation.py
- Caminho: scripts/analysis/classification/evaluation.py
- Responsabilidade: avaliacao de modelos, balanceamento SMOTE e metrics.
- Dependencias importadas: sklearn.metrics, imblearn (opcional), matplotlib
- Quem o utiliza: pipelines de classificacao
- O que consome: X, y, modelo treinado
- O que produz: metricas e plots de matriz de confusao

## scripts/analysis/classification/feature_importance.py
- Nome: feature_importance.py
- Caminho: scripts/analysis/classification/feature_importance.py
- Responsabilidade: calcular MDI e permutation importance.
- Dependencias importadas: sklearn.inspection, pandas, polars
- Quem o utiliza: pipelines de classificacao
- O que consome: pipeline treinado e X_test/y_test
- O que produz: DataFrame de importancias

## scripts/analysis/classification/persistence.py
- Nome: persistence.py
- Caminho: scripts/analysis/classification/persistence.py
- Responsabilidade: salvar datasets, modelos e predicoes.
- Dependencias importadas: joblib, pandas, polars
- Quem o utiliza: pipelines de classificacao
- O que consome: X/y e pipeline treinado
- O que produz: parquets de train/test, predictions, feature_importance e model.joblib

## scripts/analysis/__init__.py
- Nome: __init__.py
- Caminho: scripts/analysis/__init__.py
- Responsabilidade: marcador de pacote.
- Dependencias importadas: N/A
- Quem o utiliza: importacao de pacote
- O que consome: N/A
- O que produz: N/A

## scripts/common/path_utils.py
- Nome: path_utils.py
- Caminho: scripts/common/path_utils.py
- Responsabilidade: resolver paths base/entrada/saida.
- Dependencias importadas: pathlib
- Quem o utiliza: maioria dos CLIs
- O que consome: strings de path
- O que produz: Path resolvido

## scripts/common/logging_utils.py
- Nome: logging_utils.py
- Caminho: scripts/common/logging_utils.py
- Responsabilidade: configurar logging em arquivo + console.
- Dependencias importadas: logging, datetime, pathlib
- Quem o utiliza: CLIs
- O que consome: nivel/log format
- O que produz: arquivo logs/pipeline_*.log

## scripts/common/id_utils.py
- Nome: id_utils.py
- Caminho: scripts/common/id_utils.py
- Responsabilidade: normalizacao de nomes e IDs, parsing de patient_unique_id.
- Dependencias importadas: pandas, unicodedata, re
- Quem o utiliza: pipeline, annotate, audit, hashing
- O que consome: strings de IDs/nomes
- O que produz: strings normalizadas

## scripts/common/name_utils.py
- Nome: name_utils.py
- Caminho: scripts/common/name_utils.py
- Responsabilidade: gerar variacoes de nomes e comparar sexo.
- Dependencias importadas: itertools, re, common.id_utils
- Quem o utiliza: questionnaire.record_linkage
- O que consome: nomes brutos
- O que produz: tokens/variacoes

## scripts/common/date_utils.py
- Nome: date_utils.py
- Caminho: scripts/common/date_utils.py
- Responsabilidade: parsing de datas e estimativa de ano de nascimento.
- Dependencias importadas: polars, datetime, re
- Quem o utiliza: patient_lookup, record_linkage
- O que consome: datas/idade
- O que produz: anos e expressoes Polars

## scripts/common/patient_lookup.py
- Nome: patient_lookup.py
- Caminho: scripts/common/patient_lookup.py
- Responsabilidade: construir tabelas de pacientes e filtros por fase (dob, nome, sexo, fuzzy).
- Dependencias importadas: polars, common.date_utils, common.id_utils
- Quem o utiliza: questionnaire.record_linkage
- O que consome: medical_records_history.parquet; patients_id_mapping parquets; righteye parquet
- O que produz: DataFrames Polars com chaves normalizadas

## scripts/common/patient_utils.py
- Nome: patient_utils.py
- Caminho: scripts/common/patient_utils.py
- Responsabilidade: derivar ano de nascimento a partir de data YY/MM/DD.
- Dependencias importadas: polars
- Quem o utiliza: anonymize_from_output
- O que consome: data_nascimento
- O que produz: expressao Polars (dob_year)

## scripts/common/value_utils.py
- Nome: value_utils.py
- Caminho: scripts/common/value_utils.py
- Responsabilidade: normalizar campos booleanos e rotulos.
- Dependencias importadas: re
- Quem o utiliza: annotate_patient_mapping, audit_records_coverage, classification/data_prep
- O que consome: texto livre
- O que produz: bool/None

## scripts/common/df_utils.py
- Nome: df_utils.py
- Caminho: scripts/common/df_utils.py
- Responsabilidade: deduplicacao com logging.
- Dependencias importadas: polars, logging
- Quem o utiliza: audit_records_coverage
- O que consome: DataFrame Polars
- O que produz: DataFrame Polars deduplicado

## scripts/common/__init__.py
- Nome: __init__.py
- Caminho: scripts/common/__init__.py
- Responsabilidade: marcador de pacote.
- Dependencias importadas: N/A
- Quem o utiliza: importacao de pacote
- O que consome: N/A
- O que produz: N/A

## scripts/questionnaire/questionnaire_pipeline.py
- Nome: questionnaire_pipeline.py
- Caminho: scripts/questionnaire/questionnaire_pipeline.py
- Responsabilidade: orquestrador do fluxo de questionário — executa step1_parse, step2_link, step3_features e step4_anonymize em sequência.
- Dependencias importadas: step1_parse, step2_link, step3_features, step4_anonymize
- Quem o utiliza: usuários via CLI (`python -m scripts.questionnaire.questionnaire_pipeline`)
- O que consome: `--questionnaire-input <json>`, `--base .`
- O que produz: outputs de todas as fases em `output/questionnaire/<questionnaire_id>/`

## scripts/questionnaire/record_linkage.py
- Nome: record_linkage.py
- Caminho: scripts/questionnaire/record_linkage.py
- Responsabilidade: motor de linkage — vincula respostas do questionário com bases ERG e RightEye via fuzzy matching.
- Dependencias importadas: polars, numpy, common.patient_lookup, common.name_utils, common.date_utils
- Quem o utiliza: questionnaire_pipeline.py, step2_link.py; usuários via CLI direta
- O que consome: JSON de respostas; medical_records_history; patients_id_mapping; data_right_eye
- O que produz: linkage_results, linkage_confirmed, ambiguous, not_found, linkage_explain.csv, linkage_report.txt

## scripts/questionnaire/step1_parse.py
- Nome: step1_parse.py
- Caminho: scripts/questionnaire/step1_parse.py
- Responsabilidade: fase 1 — parse e normalização das respostas brutas do questionário JSON.
- Quem o utiliza: questionnaire_pipeline.py
- O que consome: JSON de respostas do questionário
- O que produz: respostas normalizadas em `output/questionnaire/<questionnaire_id>/`

## scripts/questionnaire/step2_link.py
- Nome: step2_link.py
- Caminho: scripts/questionnaire/step2_link.py
- Responsabilidade: fase 2 — linkage das respostas com bases ERG/RightEye via record_linkage.
- Quem o utiliza: questionnaire_pipeline.py
- O que consome: saída da fase 1; medical_records_history; patients_id_mapping; data_right_eye
- O que produz: linkage_confirmed, ambiguous, not_found, linkage_explain.csv

## scripts/questionnaire/step3_features.py
- Nome: step3_features.py
- Caminho: scripts/questionnaire/step3_features.py
- Responsabilidade: fase 3 — extração de features a partir dos resultados de linkage confirmados.
- Quem o utiliza: questionnaire_pipeline.py
- O que consome: saída da fase 2 (linkage_confirmed)
- O que produz: features_*.parquet/.csv em `output/questionnaire/<questionnaire_id>/`

## scripts/questionnaire/step4_anonymize.py
- Nome: step4_anonymize.py
- Caminho: scripts/questionnaire/step4_anonymize.py
- Responsabilidade: fase 4 — anonimização do dataset de features do questionário.
- Quem o utiliza: questionnaire_pipeline.py
- O que consome: saída da fase 3 (features_*.parquet)
- O que produz: anonymized_*.parquet/.csv em `output/questionnaire/<questionnaire_id>/`

## scripts/questionnaire/__init__.py
- Nome: __init__.py
- Caminho: scripts/questionnaire/__init__.py
- Responsabilidade: marcador de pacote.
- Dependencias importadas: N/A
- Quem o utiliza: importacao de pacote
- O que consome: N/A
- O que produz: N/A

## scripts/visualization/parquet_preview.py
- Nome: parquet_preview.py
- Caminho: scripts/visualization/parquet_preview.py
- Responsabilidade: gerar previews CSV de parquets (head ou preview2 por pacientes).
- Dependencias importadas: pandas, pyarrow
- Quem o utiliza: usuarios via CLI
- O que consome: parquets de datasets ERG
- O que produz: preview_*.csv ou preview2_*.csv

## scripts/visualization/waveform_sample_plot.py
- Nome: waveform_sample_plot.py
- Caminho: scripts/visualization/waveform_sample_plot.py
- Responsabilidade: plotar waveforms por amostra de pacientes.
- Dependencias importadas: pandas, pyarrow, matplotlib
- Quem o utiliza: usuarios via CLI
- O que consome: parquets/CSVs de waveforms
- O que produz: PNGs waveform_*.png e selected_patients.txt

## scripts/visualization/__init__.py
- Nome: __init__.py
- Caminho: scripts/visualization/__init__.py
- Responsabilidade: marcador de pacote.
- Dependencias importadas: N/A
- Quem o utiliza: importacao de pacote
- O que consome: N/A
- O que produz: N/A
