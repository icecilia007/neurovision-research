"""
Script para criar histogramas de colunas de arquivos CSV.

Gera histogramas individuais para uma ou mais colunas especificadas de um arquivo CSV,
salvando cada gráfico em um arquivo PNG separado.

Exemplo de uso:
    python scripts/plot_histograms.py --input data/results.csv --columns score accuracy --output plots
    python scripts/plot_histograms.py --input consolidated/metrics.csv --columns bleu comet --bins 30 --output analysis/plots
"""

import argparse
import pandas as pd
from pathlib import Path
import logging
import matplotlib.pyplot as plt
import sys
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


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
    
    logger.info(f"CSV carregado: {len(df)} linhas, {len(df.columns)} colunas")
    return df


def validate_columns(df: pd.DataFrame, columns: list) -> list:
    """
    Valida se colunas existem no DataFrame e contêm dados numéricos.
    
    Args:
        df: DataFrame a validar
        columns: Lista de nomes de colunas
        
    Returns:
        Lista de colunas válidas (numéricas)
    """
    available_columns = df.columns.tolist()
    valid_columns = []
    
    for col in columns:
        if col not in available_columns:
            logger.warning(f"Coluna '{col}' não encontrada. Colunas disponíveis: {available_columns}")
            continue
        
        # Verifica se coluna é numérica
        if not pd.api.types.is_numeric_dtype(df[col]):
            logger.warning(f"Coluna '{col}' não é numérica (tipo: {df[col].dtype}). Ignorando.")
            continue
        
        # Verifica se tem dados válidos (não-nulos)
        non_null_count = df[col].notna().sum()
        if non_null_count == 0:
            logger.warning(f"Coluna '{col}' não contém valores válidos. Ignorando.")
            continue
        
        valid_columns.append(col)
        logger.info(f"✓ Coluna '{col}': {non_null_count} valores válidos (tipo: {df[col].dtype})")
    
    return valid_columns


def determine_decimal_places(data: pd.Series) -> int:
    """
    Determina o número apropriado de casas decimais baseado nos dados.
    
    Args:
        data: Serie de dados numéricos
        
    Returns:
        Número de casas decimais a usar (entre 2 e 6)
    """
    # Calcula o range dos dados
    data_range = data.max() - data.min()
    
    # Se o range é muito pequeno, usa mais decimais
    if data_range < 0.01:
        return 6
    elif data_range < 0.1:
        return 5
    elif data_range < 1.0:
        return 4
    elif data_range < 10.0:
        return 3
    else:
        return 2


def create_histogram(df: pd.DataFrame, column: str, output_dir: Path, bins: int = 20):
    """
    Cria e salva histograma para uma coluna específica.
    
    Args:
        df: DataFrame contendo os dados
        column: Nome da coluna para plotar
        output_dir: Diretório onde salvar o gráfico
        bins: Número de bins do histograma (padrão: 20)
    """
    # Prepara dados removendo valores nulos
    data = df[column].dropna()
    
    if len(data) == 0:
        logger.error(f"Nenhum dado válido na coluna '{column}'")
        return
    
    # Determina número de casas decimais apropriado
    decimal_places = determine_decimal_places(data)
    
    # Calcula estatísticas
    mean_val = data.mean()
    median_val = data.median()
    std_val = data.std()
    min_val = data.min()
    max_val = data.max()
    
    # Cria figura
    plt.figure(figsize=(12, 6))
    
    # Plota histograma (usa todos os valores originais, sem arredondamento)
    n, bins_edges, patches = plt.hist(data, bins=bins, edgecolor='black', alpha=0.7, color='steelblue')
    
    # Configurações do gráfico
    plt.xlabel(column, fontsize=12, fontweight='bold')
    plt.ylabel('Frequência', fontsize=12, fontweight='bold')
    plt.title(f'Histograma: {column}', fontsize=14, fontweight='bold', pad=20)
    plt.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Configura eixo X para mostrar todos os limites dos bins
    ax = plt.gca()
    
    # Define os ticks do eixo X para mostrar os limites de cada bin
    ax.set_xticks(bins_edges)
    
    # Formata os labels do eixo X com a precisão adequada
    ax.set_xticklabels([f'{edge:.{decimal_places}f}' for edge in bins_edges], 
                       rotation=45, ha='right', fontsize=8)
    
    # Adiciona caixa de texto com estatísticas (sem duplicar média e mediana)
    stats_text = (
        f'N = {len(data)}\n'
        f'Média = {mean_val:.{decimal_places}f}\n'
        f'Mediana = {median_val:.{decimal_places}f}\n'
        f'Desvio Padrão = {std_val:.{decimal_places}f}\n'
        f'Min = {min_val:.{decimal_places}f}\n'
        f'Max = {max_val:.{decimal_places}f}'
    )
    
    plt.text(
        0.98, 0.98, stats_text,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment='top',
        horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    )
    
    # Salva figura
    output_file = output_dir / f"histogram_{column}.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Histograma salvo: {output_file.name} (precisão: {decimal_places} casas decimais)")


def main():
    """
    Função principal que coordena a geração de histogramas.
    
    Carrega CSV, valida colunas especificadas e gera histogramas
    individuais para cada coluna válida.
    """
    parser = argparse.ArgumentParser(
        description="Gera histogramas para colunas específicas de um arquivo CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s --input data.csv --columns score
  %(prog)s --input results.csv --columns acc loss --bins 30
  %(prog)s --input metrics.csv --columns bleu comet bertscore --output plots
        """
    )
    
    parser.add_argument(
        "--input",
        required=True,
        help="Caminho completo do arquivo CSV de entrada"
    )
    
    parser.add_argument(
        "--columns",
        nargs='+',
        required=True,
        help="Nome(s) da(s) coluna(s) para criar histogramas (separados por espaço)"
    )
    
    parser.add_argument(
        "--output",
        default="plots",
        help="Diretório onde salvar os histogramas (padrão: plots)"
    )
    
    parser.add_argument(
        "--bins",
        type=int,
        default=20,
        help="Número de bins para os histogramas (padrão: 20)"
    )
    
    args = parser.parse_args()
    
    # Valida caminho de entrada
    input_path = Path(args.input).resolve()
    
    try:
        df = validate_csv_file(input_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error(str(e))
        sys.exit(1)
    
    # Valida colunas
    valid_columns = validate_columns(df, args.columns)
    
    if not valid_columns:
        logger.error("Nenhuma coluna válida encontrada para plotar")
        logger.info(f"Colunas disponíveis no CSV: {df.columns.tolist()}")
        sys.exit(1)
    
    # Cria diretório de saída
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Diretório de saída: {output_dir}")
    
    # Gera histogramas
    logger.info(f"\n{'='*60}")
    logger.info(f"Gerando {len(valid_columns)} histograma(s)...")
    logger.info(f"{'='*60}\n")
    
    for column in valid_columns:
        try:
            create_histogram(df, column, output_dir, bins=args.bins)
        except Exception as e:
            logger.error(f"Erro ao criar histograma para '{column}': {e}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Processo concluído: {len(valid_columns)} histograma(s) gerado(s)")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
