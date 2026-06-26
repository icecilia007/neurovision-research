"""Executa a pipeline em etapas intencionais: consolidate, hash e parquet.

Uso rapido:
    python scripts/main.py consolidate --base . --patients-input exam --waveforms-input waveform
    python scripts/main.py parquet --base . --input outputs/hashed --output outputs/hashed
"""

import argparse
import logging
from pathlib import Path

from common.logging_utils import configure_logging
from pipeline.consolidated_to_parquet import run_consolidated_to_parquet
from pipeline.anonymize import run_anonymize_from_output
from processing.annotate_patient_mapping import run as run_annotate_patient_mapping
from pipeline.raw_to_consolidated import run_patient_preparation, run_waveform_consolidation, run_consolidate_from_raw
from pipeline.hashing import run_hash_orchestrator
from pipeline.purge import run_purge_orphan_ids
from analysis.audit_records_coverage import run as run_audit_records_coverage


logger = logging.getLogger(__name__)


def stage_consolidate(args: argparse.Namespace) -> None:
    base_dir = Path(args.base).resolve()

    prepare_args = argparse.Namespace(
        base=str(base_dir),
        input=args.patients_input,
        output=args.patients_output,
        workers=args.workers,
        output_partitions=args.patients_partitions,
    )

    waveform_args = argparse.Namespace(
        base=str(base_dir),
        input=args.waveforms_input,
        output=args.waveforms_output,
        workers=args.workers,
        metadata_partitions=args.metadata_partitions,
        waveform_partitions=args.waveform_partitions,
        max_records_per_file=args.max_records_per_file,
    )

    logger.info("ETAPA consolidate: preparando patients")
    run_patient_preparation(prepare_args)

    logger.info("ETAPA consolidate: processando waveforms e consolidando Parquet")
    run_waveform_consolidation(waveform_args)

    logger.info("Consolidacao concluida.")
    logger.info("Patients em: %s", (base_dir / args.patients_output).resolve())
    logger.info(
        "Waveforms consolidados em: %s",
        (base_dir / args.waveforms_output / "consolidated").resolve(),
    )


def stage_parquet(args: argparse.Namespace) -> None:
    base_dir = Path(args.base).resolve()

    parquet_args = argparse.Namespace(
        base=str(base_dir),
        input=args.input,
        output=args.output,
        workers=args.workers,
        block_size_mb=args.block_size_mb,
        name_prefix=args.name_prefix,
        compact_names=args.compact_names,
        name_date_suffix=args.name_date_suffix,
        skip_metadata_output=args.skip_metadata_output,
    )

    logger.info("ETAPA parquet: consumindo consolidados e gerando datasets finais")
    run_consolidated_to_parquet(parquet_args)
    logger.info("Conversao para Parquet concluida em: %s", (base_dir / args.output).resolve())


def stage_hash(args: argparse.Namespace) -> None:
    logger.info("ETAPA hash: normalizacao/hash/apply (intencional por comando)")
    run_hash_orchestrator(args)


def stage_consolidate_and_audit(args: argparse.Namespace) -> None:
    logger.info("ETAPA consolidate-and-audit: patients + waveforms + id_audit report")
    run_consolidate_from_raw(args)


def stage_annotate(args: argparse.Namespace) -> None:
    logger.info("ETAPA annotate: anotando patients_id_mapping com dados clinicos")
    run_annotate_patient_mapping(args)

    logger.info("ETAPA annotate: auditoria de cobertura de records")
    coverage_args = argparse.Namespace(
        base=args.base,
        records_input=args.records_input,
        mapping_root=args.mapping_root,
        metadata_root=args.metadata_root,
        reports_output=args.coverage_reports_output,
        dry_run=args.dry_run,
    )
    run_audit_records_coverage(coverage_args)


def stage_purge(args: argparse.Namespace) -> None:
    logger.info("ETAPA purge: removendo IDs orfaos das bases consolidadas")
    run_purge_orphan_ids(args)


def stage_anonymize(args: argparse.Namespace) -> None:
    logger.info("ETAPA anonymize: auto-descoberta em output/, audit, hash e parquet")
    run_anonymize_from_output(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Separa a pipeline em estagios intencionais: consolidate, hash, parquet e anonymize."
    )
    subparsers = parser.add_subparsers(dest="stage", required=True)

    consolidate = subparsers.add_parser(
        "consolidate",
        help="Etapa 1: processa arquivos brutos e gera consolidados Parquet",
    )
    consolidate.add_argument("--base", default=".", help="Diretorio base")
    consolidate.add_argument(
        "--patients-input",
        required=True,
        help="Diretorio/arquivo com dados de patients (entrada do prepare_patients)",
    )
    consolidate.add_argument(
        "--waveforms-input",
        required=True,
        help="Diretorio com CSVs de waveform (entrada do process_waveform)",
    )
    consolidate.add_argument(
        "--patients-output",
        default="outputs/patients",
        help="Diretorio de saida de patients",
    )
    consolidate.add_argument(
        "--waveforms-output",
        default="outputs/waveforms",
        help="Diretorio de saida de waveforms",
    )
    consolidate.add_argument("--workers", type=int, default=None, help="Workers para ambos scripts")
    consolidate.add_argument(
        "--patients-partitions",
        type=int,
        default=None,
        help="Particoes/arquivos alvo do parquet de patients",
    )
    consolidate.add_argument(
        "--metadata-partitions",
        type=int,
        default=None,
        help="Particoes/arquivos alvo do consolidated_metadata.parquet",
    )
    consolidate.add_argument(
        "--waveform-partitions",
        type=int,
        default=None,
        help="Particoes/arquivos alvo do consolidated_waveforms.parquet",
    )
    consolidate.add_argument(
        "--max-records-per-file",
        type=int,
        default=None,
        help="Define spark.sql.files.maxRecordsPerFile no processamento de waveform",
    )
    consolidate.set_defaults(func=stage_consolidate)

    consolidate_audit = subparsers.add_parser(
        "consolidate-and-audit",
        help="Etapa 1 unificada: patients + waveforms + id_audit report em sequencia",
    )
    consolidate_audit.add_argument("--base", default=".", help="Diretorio base")
    consolidate_audit.add_argument(
        "--patients-input",
        required=True,
        help="Diretorio/arquivo com dados de patients",
    )
    consolidate_audit.add_argument(
        "--waveforms-input",
        required=True,
        help="Diretorio com CSVs de waveform",
    )
    consolidate_audit.add_argument(
        "--patients-output",
        default="output/patients",
        help="Diretorio de saida de patients",
    )
    consolidate_audit.add_argument(
        "--waveforms-output",
        default="output/waveforms",
        help="Diretorio de saida de waveforms",
    )
    consolidate_audit.add_argument(
        "--reports-output",
        default="output/reports/id_audit",
        help="Diretorio de saida do relatorio id_audit",
    )
    consolidate_audit.add_argument("--workers", type=int, default=None, help="Workers para os dois scripts")
    consolidate_audit.add_argument(
        "--patients-partitions",
        type=int,
        default=None,
        help="Particoes alvo do parquet de patients",
    )
    consolidate_audit.add_argument(
        "--metadata-partitions",
        type=int,
        default=None,
        help="Particoes alvo do consolidated_metadata",
    )
    consolidate_audit.add_argument(
        "--waveform-partitions",
        type=int,
        default=None,
        help="Particoes alvo do consolidated_waveforms",
    )
    consolidate_audit.add_argument(
        "--max-records-per-file",
        type=int,
        default=None,
        help="Define spark.sql.files.maxRecordsPerFile",
    )
    consolidate_audit.set_defaults(func=stage_consolidate_and_audit)

    parquet = subparsers.add_parser(
        "parquet",
        help="Etapa 2: transforma consolidados Parquet em datasets Parquet finais",
    )
    parquet.add_argument("--base", default=".", help="Diretorio base")
    parquet.add_argument(
        "--input",
        required=True,
        help="Diretorio com metadata/waveforms e patients (ou nomes consolidated_*)",
    )
    parquet.add_argument("--output", required=True, help="Diretorio de saida")
    parquet.add_argument("--workers", type=int, default=None, help="Numero de threads de leitura")
    parquet.add_argument(
        "--block-size-mb",
        type=int,
        default=64,
        help="Tamanho do bloco de leitura de waveforms em MB",
    )
    parquet.add_argument(
        "--name-prefix",
        default="erg",
        help="Prefixo dos nomes dos arquivos gerados",
    )
    parquet.add_argument(
        "--compact-names",
        action="store_true",
        help="Gera nomes curtos: metadata/waveforms/features/waveform_types",
    )
    parquet.add_argument(
        "--name-date-suffix",
        default="",
        help="Sufixo de data/hora para os nomes (ex.: 20260417_101500)",
    )
    parquet.add_argument(
        "--skip-metadata-output",
        action="store_true",
        help="Nao gera arquivo de metadata final",
    )
    parquet.set_defaults(func=stage_parquet)

    hash_stage = subparsers.add_parser(
        "hash",
        help="Etapa intencional de hash (delegada ao encrypt_patient_ids)",
    )
    hash_stage.add_argument("--base", default=".", help="Diretorio base")
    hash_stage.add_argument("--normalize-inputs", nargs="+", help="CSV(s) para normalizar inplace")
    hash_stage.add_argument("--mapping-input", required=True, help="CSV de mapping de pacientes")
    hash_stage.add_argument("--mapping-output", required=True, help="Parquet de mapping hash")
    hash_stage.add_argument(
        "--apply-inputs",
        nargs="+",
        required=True,
        help="CSV(s) ou Parquet(s) para aplicar hash via streaming",
    )
    hash_stage.add_argument("--output-dir", required=True, help="Diretorio de saida dos parquets finais")
    hash_stage.add_argument("--debug-csv", required=True, help="CSV de IDs sem hash")
    hash_stage.add_argument("--column", default="patient_unique_id", help="Coluna de ID")
    hash_stage.add_argument(
        "--drop-columns",
        default="source_file,id_prontuario,nome_paciente,data_nascimento",
        help="Colunas a remover",
    )
    hash_stage.add_argument("--float-columns", default="voltage_uV,pupil_mm,time_ms", help="Colunas float")
    hash_stage.add_argument("--int-columns", default="test_id", help="Colunas int")
    hash_stage.add_argument("--metadata-before", default=None, help="Metadata original para corrigir IDs")
    hash_stage.add_argument("--metadata-after", default=None, help="Metadata corrigido para corrigir IDs")
    hash_stage.add_argument("--metadata", default=None, help="Metadata corrigido (uso sem before/after)")
    hash_stage.add_argument("--chunk-size", type=int, default=50000, help="Tamanho de chunk")
    hash_stage.add_argument("--salt", default=None, help="Salt bcrypt")
    hash_stage.add_argument("--skip-normalize", action="store_true", help="Pula etapa de normalizacao")
    hash_stage.add_argument("--skip-mapping", action="store_true", help="Pula etapa de hash mapping")
    hash_stage.add_argument("--skip-apply", action="store_true", help="Pula etapa de aplicacao streaming")
    hash_stage.set_defaults(func=stage_hash)

    annotate_stage = subparsers.add_parser(
        "annotate",
        help="Anota patients_id_mapping com records_nome, neurodivergencia e laudo de medical_records_history",
    )
    annotate_stage.add_argument("--base", default=".", help="Diretorio base")
    annotate_stage.add_argument(
        "--records-input",
        default="patients-data/medical_records_history.parquet",
        help="Caminho para medical_records_history parquet",
    )
    annotate_stage.add_argument(
        "--mapping-root",
        default="output/patients",
        help="Diretorio raiz com os arquivos patients_id_mapping",
    )
    annotate_stage.add_argument(
        "--reports-output",
        default="output/reports/annotation",
        help="Diretorio para relatorios de auditoria da anotacao",
    )
    annotate_stage.add_argument(
        "--metadata-input",
        default="output/waveforms/consolidated/consolidated_metadata.parquet",
        help="Caminho para consolidated_metadata parquet (fallback de nome quando prontuario nao encontrado)",
    )
    annotate_stage.add_argument(
        "--metadata-root",
        default="output/waveforms/consolidated",
        help="Diretorio raiz com consolidated_metadata para auditoria de cobertura",
    )
    annotate_stage.add_argument(
        "--coverage-reports-output",
        default="output/reports/records_coverage",
        help="Diretorio para relatorios de cobertura de records",
    )
    annotate_stage.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas loga o que seria anotado, sem gravar arquivos",
    )
    annotate_stage.set_defaults(func=stage_annotate)

    purge_stage = subparsers.add_parser(
        "purge",
        help="Remove IDs orfaos (only_patients / only_metadata) das bases consolidadas",
    )
    purge_stage.add_argument("--base", default=".", help="Diretorio base")
    purge_stage.add_argument(
        "--audit-input",
        default="output/reports/id_audit/unique_ids_only_one_base_counts.csv",
        help="Caminho para unique_ids_only_one_base_counts.csv",
    )
    purge_stage.add_argument(
        "--patients-root",
        default="output/patients",
        help="Diretorio raiz com parquets de patients",
    )
    purge_stage.add_argument(
        "--waveforms-root",
        default="output/waveforms/consolidated",
        help="Diretorio raiz com consolidated_metadata e consolidated_waveforms",
    )
    purge_stage.add_argument(
        "--audit-log-output",
        default=None,
        help="Diretorio para o CSV de log do purge (default: output/reports/id_audit)",
    )
    purge_stage.add_argument("--workers", type=int, default=None, help="Workers Spark local")
    purge_stage.add_argument(
        "--no-spark",
        action="store_true",
        help="Usar PyArrow em vez de Spark (datasets menores)",
    )
    purge_stage.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas loga o que seria removido, sem gravar arquivos",
    )
    purge_stage.set_defaults(func=stage_purge)

    anonymize_stage = subparsers.add_parser(
        "anonymize",
        help="Etapa unica: descobre datasets em output/, audita IDs, hasheia e gera output/data",
    )
    anonymize_stage.add_argument("--base", default=".", help="Diretorio base")
    anonymize_stage.add_argument("--input-root", default="output", help="Raiz com patients/ e waveforms/")
    anonymize_stage.add_argument("--output-root", default="output/data", help="Raiz de saida do anonymize")
    anonymize_stage.add_argument(
        "--reports-output",
        default=None,
        help="Override do diretorio de relatorios (default: <output-root>/reports/id_audit)",
    )
    anonymize_stage.add_argument("--column", default="patient_unique_id", help="Coluna de ID")
    anonymize_stage.add_argument(
        "--drop-columns",
        default="source_file,id_prontuario,nome_paciente,data_nascimento,PatientID,PatientBirthdate,TestingDate,data_realizada_do_teste,data_teste",
        help="Colunas a remover na etapa hash",
    )
    anonymize_stage.add_argument("--float-columns", default="voltage_uV,pupil_mm,time_ms", help="Colunas float")
    anonymize_stage.add_argument("--int-columns", default="test_id", help="Colunas int")
    anonymize_stage.add_argument("--chunk-size", type=int, default=50000, help="Tamanho de chunk")
    anonymize_stage.add_argument("--salt", default=None, help="Salt bcrypt")
    anonymize_stage.add_argument("--workers", type=int, default=None, help="Workers etapa parquet")
    anonymize_stage.add_argument("--block-size-mb", type=int, default=64, help="Bloco em MB da etapa parquet")
    anonymize_stage.set_defaults(func=stage_anonymize)

    return parser


def main() -> None:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
