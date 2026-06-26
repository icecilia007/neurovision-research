"""
Script para ranquear modelos de tradução baseado em múltiplas métricas.

Calcula rankings de modelos usando diferentes metodologias:
- Método 1: Média simples de todas as métricas (padrão)
- Método 2: Rankings individuais por métrica selecionada
- Método 3: Média simples apenas das métricas selecionadas

Exemplo de uso:
    python scripts/rank_models.py --input results/analysis_results.csv
    python scripts/rank_models.py --input data.csv --method 2 --priority bertscore comet
    python scripts/rank_models.py --input data.csv --all --priority bertscore comet --columns bertscore comet 
    python scripts/rank_models.py --input data.csv --method 1 --filter-column comet --filter-op maior --filter-value 0.75
    uv run python scripts/rank_models.py --input results\questions-only\original\analysis_results_alt.csv --all --priority bertscore comet final_readability_score --columns bertscore comet final_readability_score
    uv run python scripts/rank_models.py --input results\questions-only\original\analysis_results_alt.csv --all --priority bertscore comet --columns bertscore 
    uv run python scripts/rank_models.py --input results\questions-only\original\analysis_results_alt.csv --all --priority bertscore comet --columns bertscore comet --filter-column final_readability_score --filter-op lt --filter-value 9
"""

import argparse
import pandas as pd
from pathlib import Path
import logging
import sys
from pandas.api.types import is_numeric_dtype

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def parse_filter_operator(operator: str) -> str:
    """
    Normaliza operador de filtro para tokens internos.

    Args:
        operator: Operador informado na CLI

    Returns:
        Operador normalizado ('eq', 'gt', 'lt')

    Raises:
        ValueError: Se operador for inválido
    """
    operator_map = {
        'eq': 'eq',
        'igual': 'eq',
        '=': 'eq',
        'gt': 'gt',
        'maior': 'gt',
        '>': 'gt',
        'lt': 'lt',
        'menor': 'lt',
        '<': 'lt'
    }

    normalized = operator_map.get(operator.lower().strip())
    if normalized is None:
        raise ValueError(
            f"Operador inválido: '{operator}'. Use eq/igual/=, gt/maior/> ou lt/menor/<."
        )

    return normalized


def apply_column_filter(df: pd.DataFrame, column: str, operator: str, value: str) -> pd.DataFrame:
    """
    Aplica filtro em uma coluna, mantendo linhas por comparação.

    Args:
        df: DataFrame original
        column: Nome da coluna para filtrar
        operator: Operador de comparação ('eq', 'gt', 'lt' ou sinônimos)
        value: Valor de referência para comparação

    Returns:
        DataFrame filtrado

    Raises:
        ValueError: Se coluna não existir, operador for inválido ou valor incompatível
    """
    if column not in df.columns:
        raise ValueError(f"Coluna de filtro '{column}' não encontrada no CSV")

    normalized_operator = parse_filter_operator(operator)
    series = df[column]

    # Igualdade aceita valores numéricos e texto.
    if normalized_operator == 'eq':
        if is_numeric_dtype(series):
            try:
                numeric_value = float(value)
            except ValueError as e:
                raise ValueError(
                    f"Valor '{value}' inválido para comparação numérica na coluna '{column}'"
                ) from e

            mask = series == numeric_value
        else:
            mask = series.astype(str) == str(value)

    else:
        # Comparações de ordem exigem coluna numérica.
        if not is_numeric_dtype(series):
            raise ValueError(
                f"Operador '{operator}' requer coluna numérica. A coluna '{column}' não é numérica"
            )

        try:
            numeric_value = float(value)
        except ValueError as e:
            raise ValueError(
                f"Valor '{value}' inválido para comparação numérica na coluna '{column}'"
            ) from e

        mask = series > numeric_value if normalized_operator == 'gt' else series < numeric_value

    filtered_df = df[mask].copy()
    logger.info(
        "Filtro aplicado: %s %s %s | Linhas mantidas: %d de %d",
        column,
        normalized_operator,
        value,
        len(filtered_df),
        len(df)
    )

    if filtered_df.empty:
        raise ValueError("Filtro removeu todas as linhas. Ajuste coluna/operador/valor.")

    return filtered_df


def validate_csv_file(csv_path: Path) -> pd.DataFrame:
    """
    Valida e carrega arquivo CSV.

    Args:
        csv_path: Caminho do arquivo CSV

    Returns:
        DataFrame com os dados carregados

    Raises:
        FileNotFoundError: Se arquivo não existe
        ValueError: Se arquivo está vazio ou inválido
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {csv_path}")

    if not csv_path.is_file():
        raise ValueError(f"O caminho não é um arquivo: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        raise ValueError(f"Erro ao ler CSV: {e}")

    if df.empty:
        raise ValueError("Arquivo CSV está vazio")

    logger.info(f"CSV carregado: {len(df)} modelos, {len(df.columns)} colunas")
    return df


def get_metric_direction(column_name: str) -> str:
    """
    Determina se métrica é melhor quando maior ou menor.

    Args:
        column_name: Nome da coluna/métrica

    Returns:
        'higher' se maior é melhor, 'lower' se menor é melhor
    """
    # Métricas onde MAIOR é MELHOR
    better_higher = [
        'flesch_reading_ease', 'gulpease_index', 'bertscore', 'comet',
        'score', 'accuracy', 'precision', 'recall', 'f1'
    ]

    # Métricas onde MENOR é MELHOR (complexidade, erro, etc)
    better_lower = [
        'flesch_kincaid_grade_level', 'gunning_fog_index',
        'automated_readability_index', 'coleman_liau_index',
        'final_readability_score', 'error', 'loss', 'perplexity'
    ]

    column_lower = column_name.lower()

    if any(metric in column_lower for metric in better_higher):
        return 'higher'
    elif any(metric in column_lower for metric in better_lower):
        return 'lower'
    else:
        # Por padrão, assume que maior é melhor
        logger.warning(f"Direção não definida para '{column_name}'. Assumindo 'maior é melhor'.")
        return 'higher'


def normalize_column(df: pd.DataFrame, column: str) -> pd.Series:
    """
    Normaliza coluna para escala 0-1.

    Args:
        df: DataFrame contendo os dados
        column: Nome da coluna a normalizar

    Returns:
        Serie normalizada (0-1)
    """
    direction = get_metric_direction(column)
    min_val = df[column].min()
    max_val = df[column].max()

    if max_val == min_val:
        logger.warning(f"Coluna '{column}' tem valores constantes. Retornando 0.5 para todos.")
        return pd.Series([0.5] * len(df), index=df.index)

    if direction == 'higher':
        # Maior é melhor: normaliza diretamente
        return (df[column] - min_val) / (max_val - min_val)
    else:
        # Menor é melhor: inverte a escala
        return 1 - (df[column] - min_val) / (max_val - min_val)


def method1_simple_average(df: pd.DataFrame, model_column: str = 'model_id') -> pd.DataFrame:
    """
    Método 1: Média simples de todas as métricas numéricas.

    Args:
        df: DataFrame com os dados
        model_column: Nome da coluna que identifica o modelo

    Returns:
        DataFrame ordenado por score
    """
    logger.info("Método 1: Média simples (todas as métricas têm peso igual)")

    # Identificar colunas numéricas (exceto date e model_id)
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()

    # Normalizar todas as colunas
    df_result = df.copy()
    normalized_cols = []

    for col in numeric_cols:
        norm_col = f'{col}_norm'
        df_result[norm_col] = normalize_column(df, col)
        normalized_cols.append(norm_col)

    # Calcular média simples
    df_result['final_score'] = df_result[normalized_cols].mean(axis=1)

    # Ordenar
    df_result = df_result.sort_values('final_score', ascending=False)

    logger.info(f"Utilizadas {len(normalized_cols)} métricas (peso: {100/len(normalized_cols):.2f}% cada)")

    return df_result


def method2_individual_rankings(df: pd.DataFrame, priority_columns: list, 
                                model_column: str = 'model_id', top_n: int = 5) -> dict:
    """
    Método 2: Rankings individuais por métrica.

    Mostra TOP N modelos para CADA métrica individualmente.

    Args:
        df: DataFrame com os dados
        priority_columns: Lista de colunas prioritárias
        model_column: Nome da coluna que identifica o modelo
        top_n: Número de modelos a mostrar por métrica

    Returns:
        Dicionário com rankings por métrica
    """
    logger.info(f"Método 2: Rankings individuais para {len(priority_columns)} métricas")

    rankings = {}

    for col in priority_columns:
        if col not in df.columns:
            logger.warning(f"Coluna '{col}' não encontrada. Ignorando.")
            continue

        direction = get_metric_direction(col)
        ascending = (direction == 'lower')

        # Ordenar por essa métrica
        df_sorted = df.sort_values(col, ascending=ascending)

        # Pegar top N
        top_models = df_sorted.head(top_n)[[model_column, col]].copy()

        rankings[col] = {
            'data': top_models,
            'direction': 'menor é melhor' if ascending else 'maior é melhor'
        }

        logger.info(f"  • {col}: {rankings[col]['direction']}")

    if not rankings:
        raise ValueError("Nenhuma coluna prioritária válida encontrada")

    return rankings


def method3_selected_average(df: pd.DataFrame, selected_columns: list,
                             model_column: str = 'model_id') -> pd.DataFrame:
    """
    Método 3: Média simples apenas das métricas selecionadas.

    Args:
        df: DataFrame com os dados
        selected_columns: Lista de colunas a considerar
        model_column: Nome da coluna que identifica o modelo

    Returns:
        DataFrame ordenado por score
    """
    logger.info(f"Método 3: Média simples de {len(selected_columns)} métricas selecionadas")

    df_result = df.copy()
    normalized_cols = []

    for col in selected_columns:
        if col not in df.columns:
            logger.warning(f"Coluna '{col}' não encontrada. Ignorando.")
            continue

        norm_col = f'{col}_norm'
        df_result[norm_col] = normalize_column(df, col)
        normalized_cols.append(norm_col)

        logger.info(f"  • {col}")

    if not normalized_cols:
        raise ValueError("Nenhuma coluna válida selecionada")

    # Calcular média
    df_result['final_score'] = df_result[selected_columns].mean(axis=1)

    # Ordenar
    df_result = df_result.sort_values('final_score', ascending=False)

    logger.info(f"Peso por métrica: {100/len(selected_columns):.2f}% cada")

    return df_result


def display_ranking(df: pd.DataFrame, method: int, top_n: int = 5, 
                   model_column: str = 'model_id', key_metrics: list = None):
    """
    Exibe ranking dos modelos (para métodos 1 e 3).

    Args:
        df: DataFrame com resultados
        method: Número do método usado
        top_n: Número de modelos a mostrar
        model_column: Nome da coluna de identificação do modelo
        key_metrics: Lista de métricas principais para exibir
    """
    print("\n" + "="*80)
    print(f"TOP {top_n} MODELOS - MÉTODO {method}")
    print("="*80)

    if key_metrics is None:
        key_metrics = ['bertscore', 'comet', 'final_readability_score']

    # Filtrar métricas que existem no DataFrame
    available_metrics = [m for m in key_metrics if m in df.columns]

    top_models = df.head(top_n)

    for idx, row in enumerate(top_models.itertuples(), 1):
        model_name = getattr(row, model_column)
        # Simplificar nome se muito longo
        if len(model_name) > 50:
            model_name = model_name.replace('CHYPS-V-br20-', '').replace('CHYPS-V-', '')

        print(f"\n{idx}. {model_name}")
        print("-" * 80)

        # Mostrar métricas principais
        for metric in available_metrics:
            if hasattr(row, metric):
                value = getattr(row, metric)
                print(f"   {metric:.<30} {value:.6f}")

        # Mostrar score final
        if hasattr(row, 'final_score'):
            print(f"   {'Score Final':.<30} {row.final_score:.6f}")


def display_individual_rankings(rankings: dict, model_column: str = 'model_id'):
    """
    Exibe rankings individuais por métrica (método 2).

    Args:
        rankings: Dicionário com rankings por métrica
        model_column: Nome da coluna de identificação do modelo
    """
    print("\n" + "="*80)
    print(f"RANKINGS INDIVIDUAIS POR MÉTRICA - MÉTODO 2")
    print("="*80)

    for metric_name, metric_data in rankings.items():
        print(f"\nTOP {len(metric_data['data'])} por {metric_name.upper()}")
        print(f"    ({metric_data['direction']})")
        print("-" * 80)

        for idx, row in enumerate(metric_data['data'].itertuples(), 1):
            model_name = getattr(row, model_column)
            # Simplificar nome
            if len(model_name) > 50:
                model_name = model_name.replace('CHYPS-V-br20-', '').replace('CHYPS-V-', '')

            metric_value = getattr(row, metric_name)
            print(f"  {idx}. {model_name:<60} {metric_value:.6f}")


def save_results(df: pd.DataFrame, output_path: Path, method: int):
    """
    Salva resultados do ranking em CSV (métodos 1 e 3).

    Args:
        df: DataFrame com resultados
        output_path: Caminho do arquivo de saída
        method: Número do método usado
    """
    output_file = output_path / f"ranking_method{method}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"Ranking salvo: {output_file}")


def save_individual_rankings(rankings: dict, output_path: Path, model_column: str = 'model_id'):
    """
    Salva rankings individuais em CSV (método 2).

    Args:
        rankings: Dicionário com rankings por métrica
        output_path: Diretório de saída
        model_column: Nome da coluna de identificação do modelo
    """
    for metric_name, metric_data in rankings.items():
        output_file = output_path / f"ranking_method2_{metric_name}.csv"
        metric_data['data'].to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"Ranking por {metric_name} salvo: {output_file.name}")

    # Salvar resumo consolidado
    summary_file = output_path / "ranking_method2_summary.csv"
    with open(summary_file, 'w', encoding='utf-8-sig') as f:
        f.write("metric,rank,model_id,value\n")
        for metric_name, metric_data in rankings.items():
            for idx, row in enumerate(metric_data['data'].itertuples(), 1):
                model_name = getattr(row, model_column)
                value = getattr(row, metric_name)
                f.write(f"{metric_name},{idx},{model_name},{value}\n")

    logger.info(f"Resumo consolidado salvo: {summary_file.name}")


def main():
    """
    Função principal que coordena o ranqueamento de modelos.

    Executa um dos três métodos de ranqueamento baseado nos parâmetros
    fornecidos e gera ranking dos melhores modelos.
    """
    parser = argparse.ArgumentParser(
        description="Ranqueia modelos de tradução baseado em múltiplas métricas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Métodos disponíveis:
  1 - Média simples de TODAS as métricas (padrão)
  2 - Rankings individuais por métrica selecionada
  3 - Média simples apenas das métricas selecionadas

Exemplos:
  %(prog)s --input results.csv
  %(prog)s --input data.csv --method 2 --priority bertscore comet flesch_reading_ease
  %(prog)s --input data.csv --method 3 --columns bertscore comet
  %(prog)s --input data.csv --all --priority bertscore comet --columns bertscore comet flesch_reading_ease
    %(prog)s --input data.csv --method 1 --filter-column comet --filter-op maior --filter-value 0.75
        """
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Caminho do arquivo CSV com dados dos modelos"
    )

    parser.add_argument(
        "--method",
        type=int,
        choices=[1, 2, 3],
        help="Método de ranqueamento específico (padrão: todos se --all, senão 1)"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Executa todos os métodos de uma vez"
    )

    parser.add_argument(
        "--priority",
        nargs='+',
        help="Métricas prioritárias para método 2 (ex: bertscore comet)"
    )

    parser.add_argument(
        "--columns",
        nargs='+',
        help="Métricas selecionadas para método 3 (ex: bertscore comet flesch_reading_ease)"
    )

    parser.add_argument(
        "--model-column",
        default="model_id",
        help="Nome da coluna que identifica o modelo (padrão: model_id)"
    )

    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Número de modelos a exibir no ranking (padrão: 5)"
    )

    parser.add_argument(
        "--output",
        default="results\\rankings",
        help="Diretório para salvar resultados (padrão: rankings)"
    )

    parser.add_argument(
        "--filter-column",
        help="Coluna para filtrar os dados antes do ranking (ex: comet)"
    )

    parser.add_argument(
        "--filter-op",
        help="Operador do filtro: eq/igual/=, gt/maior/>, lt/menor/<"
    )

    parser.add_argument(
        "--filter-value",
        help="Valor de referência para o filtro (ex: 0.75)"
    )

    args = parser.parse_args()

    # Validar entrada
    input_path = Path(args.input).resolve()

    try:
        df = validate_csv_file(input_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error(str(e))
        sys.exit(1)

    # Verificar coluna de modelo
    if args.model_column not in df.columns:
        logger.error(f"Coluna '{args.model_column}' não encontrada no CSV")
        logger.info(f"Colunas disponíveis: {df.columns.tolist()}")
        sys.exit(1)

    # Aplicar filtro opcional antes dos métodos de ranking
    has_filter_args = any([args.filter_column, args.filter_op, args.filter_value])
    has_complete_filter = all([args.filter_column, args.filter_op, args.filter_value])

    if has_filter_args and not has_complete_filter:
        logger.error("Para usar filtro, informe --filter-column, --filter-op e --filter-value juntos")
        sys.exit(1)

    if has_complete_filter:
        try:
            df = apply_column_filter(
                df,
                column=args.filter_column,
                operator=args.filter_op,
                value=args.filter_value
            )
        except ValueError as e:
            logger.error(str(e))
            sys.exit(1)

    # Criar diretório de saída
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determinar quais métodos executar
    if args.all:
        methods_to_run = [1, 2, 3]
        logger.info("\nExecutando TODOS os métodos\n")
    elif args.method:
        methods_to_run = [args.method]
    else:
        methods_to_run = [1]  # Padrão

    # Validar requisitos de cada método
    if 2 in methods_to_run and not args.priority:
        logger.error("Método 2 requer --priority com lista de métricas")
        sys.exit(1)

    if 3 in methods_to_run and not args.columns:
        logger.error("Método 3 requer --columns com lista de métricas")
        sys.exit(1)

    # Executar métodos selecionados
    results = {}

    for method_num in methods_to_run:
        logger.info(f"\n{'='*60}")
        logger.info(f"Iniciando análise com Método {method_num}")
        logger.info(f"{'='*60}\n")

        try:
            if method_num == 1:
                df_result = method1_simple_average(df, args.model_column)
                key_metrics = ['bertscore', 'comet', 'final_readability_score']

                # Armazenar resultado
                results[method_num] = df_result

                # Exibir ranking
                display_ranking(df_result, method_num, args.top, args.model_column, key_metrics)

                # Salvar resultados
                save_results(df_result, output_dir, method_num)

            elif method_num == 2:
                rankings = method2_individual_rankings(df, args.priority, args.model_column, args.top)

                # Armazenar resultado
                results[method_num] = rankings

                # Exibir rankings individuais
                display_individual_rankings(rankings, args.model_column)

                # Salvar resultados
                save_individual_rankings(rankings, output_dir, args.model_column)

            elif method_num == 3:
                df_result = method3_selected_average(df, args.columns, args.model_column)
                key_metrics = args.columns

                # Armazenar resultado
                results[method_num] = df_result

                # Exibir ranking
                display_ranking(df_result, method_num, args.top, args.model_column, key_metrics)

                # Salvar resultados
                save_results(df_result, output_dir, method_num)

        except Exception as e:
            logger.error(f"Erro no Método {method_num}: {e}")
            continue

    # Resumo final
    if results:
        logger.info(f"\n{'='*60}")
        logger.info(f"Análise concluída com sucesso!")
        logger.info(f"{'='*60}")
        logger.info(f"Métodos executados: {len(results)}")
        logger.info(f"Resultados salvos em: {output_dir}")
    else:
        logger.error("Nenhum método foi executado com sucesso")
        sys.exit(1)


if __name__ == "__main__":
    main()