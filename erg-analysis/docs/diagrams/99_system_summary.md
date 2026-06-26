# System Summary

## Executive summary
- Pipeline CLI modular com stages para consolidar, auditar, hash, gerar datasets, purgar e anonimizar.
- Consolida dados de patients e waveforms RETeval em parquets padronizados.
- Enriquecimento clinico e linkage com questionario/RightEye suportam analises downstream.
- Extracao espectral e ML sao pipelines paralelos aos datasets principais.

## Ponto de entrada e controle
- main.py -> stage_runner.main controla a execução via subcommands.
- Stages isolam IO pesado e permitem execucao incremental.

## Pontos criticos e gargalos
- Spark em waveform_consolidation e patient_preparation: custos de inicializacao e IO.
- hash_apply_streaming: IO intensivo e dependente de mapping completo em memória.
- erg_spectral_extraction: bucketizacao e FFT/Welch/Wavelet com custo alto por waveform.
- record_linkage: fuzzy matching pode ser O(n^2) dependendo do pool.

## Acoplamento e reutilizacao
- common/* e pipeline_utils sao dependencias centrais (alto acoplamento utilitario).
- stage_runner acopla os stages, mas cada stage tem CLI proprio.
- Anonymize reusa audit, hash e dataset generation (alta reutilizacao).

## Duplicacoes/Similaridades
- Funções _latest_match e _discover_dataset existem em consolidate_from_raw e anonymize_from_output.
- Normalização de IDs aparece em common.id_utils e pipeline_utils como wrapper.

## Riscos e pontos de atencao
- Fallbacks de encoding e heuristicas de header: risco de parse silencioso incorreto.
- Dependencia de colunas esperadas (ex.: patient_unique_id) gera ValueError em vários pontos.
- Ausencia de esquema forte para parquets pode gerar drift entre etapas.

## Melhorias possiveis (sem alterar semantica)
- Centralizar _discover_dataset e _latest_match em common para reduzir duplicação.
- Adicionar validação de schema explícita antes de joins.
- Instrumentar metrics de tempo por etapa (logging estruturado).
- Cache opcional de mapeamentos e dims para reduzir IO.

## Arquivos de referencia
- docs/diagrams/00_inventory.md
- docs/diagrams/01_components.md
- docs/diagrams/02_classes.md
- docs/diagrams/03_functions.md
- docs/diagrams/04_execution_flow.md
- docs/diagrams/05_data_flow.md
- docs/diagrams/06_dependencies.md
- docs/diagrams/07_sequence.md
- docs/diagrams/08_entities.md
- docs/diagrams/09_architecture.md
- docs/diagrams/10_traceability.md
