# Como Ranquear Modelos

Script para ranquear modelos de tradução usando 3 métodos objetivos.

---

## Uso Rápido

### Método 1 (padrão): Média de Todas as Métricas
```bash
uv run python scripts/rank_models.py --input seu_arquivo.csv
```

### Método 2: Rankings Individuais por Métrica
```bash
uv run python scripts/rank_models.py --input seu_arquivo.csv --method 2 --priority bertscore comet flesch_reading_ease
```

### Método 3: Média de Métricas Selecionadas
```bash
uv run python scripts/rank_models.py --input seu_arquivo.csv --method 3 --columns bertscore comet
```

### Executar TODOS os métodos de uma vez
```bash
uv run python scripts/rank_models.py --input seu_arquivo.csv --all --priority bertscore comet flesch_reading_ease --columns bertscore comet flesch_reading_ease
```

### Filtrar antes do ranking (igual, maior ou menor)
```bash
# Manter apenas linhas com COMET maior que 0.75
uv run python scripts/rank_models.py --input seu_arquivo.csv --method 1 --filter-column comet --filter-op maior --filter-value 0.75

# Manter apenas linhas com BERTScore igual a 0.718471
uv run python scripts/rank_models.py --input seu_arquivo.csv --method 2 --priority bertscore --filter-column bertscore --filter-op eq --filter-value 0.718471

# Manter apenas linhas com final_readability_score menor que 10
uv run python scripts/rank_models.py --input seu_arquivo.csv --method 3 --columns bertscore comet --filter-column final_readability_score --filter-op lt --filter-value 10
```

---

## Os 3 Métodos

### Método 1: Média Simples (padrão)

**O que faz:** Pega todas as métricas do CSV e calcula uma média simples.

**Exemplo:**
```
Modelo A: BERTScore=0.7, COMET=0.8, Legibilidade=0.6
Média = 0.70

Modelo B: BERTScore=0.6, COMET=0.7, Legibilidade=0.9
Média = 0.73

→ Modelo B vence!
```


---

### Método 2: Rankings Individuais

**O que faz:** Mostra os TOP 5 modelos para CADA métrica que você escolher.

**Exemplo de saída:**
```
TOP 5 por BERTSCORE (maior é melhor)
  1. Human-25-09-30                    0.718471
  2. Grok-4.1-25-12-10                 0.718277
  3. Claude-4.0-Sonnet                 0.718208

TOP 5 por COMET (maior é melhor)
  1. Deepseek-v3.2                     0.776025
  2. DeepL-v2-v3.4.1                   0.773702
  3. DeepSeek-R1                       0.772811
```


---

### Método 3: Média Seletiva

**O que faz:** Igual ao Método 1, mas só usa as métricas que você escolher.

**Exemplo:**
```
Você escolheu: BERTScore e COMET

Modelo A: média de BERTScore + COMET = 0.75
Modelo B: média de BERTScore + COMET = 0.70

→ Modelo A vence!
```

---

## Parâmetros Disponíveis

| Parâmetro | Descrição | Exemplo |
|-----------|-----------|---------|
| `--input` | Arquivo CSV com dados **(obrigatório)** | `--input data.csv` |
| `--method` | Método específico (1, 2 ou 3) | `--method 2` |
| `--all` | Executa todos os métodos | `--all` |
| `--priority` | Métricas para Método 2 | `--priority bertscore comet` |
| `--columns` | Métricas para Método 3 | `--columns bertscore comet` |
| `--top` | Quantos modelos mostrar (padrão: 5) | `--top 10` |
| `--output` | Diretório de saída (padrão: rankings) | `--output results/ranks` |
| `--model-column` | Coluna com nome do modelo | `--model-column model_id` |
| `--filter-column` | Coluna usada para filtrar antes do ranking | `--filter-column comet` |
| `--filter-op` | Operador do filtro (`eq/igual/=`, `gt/maior/>`, `lt/menor/<`) | `--filter-op maior` |
| `--filter-value` | Valor de referência para o filtro | `--filter-value 0.75` |


---

## Como Funciona (Simplificado)

### Normalização Automática
O script detecta automaticamente se "maior é melhor" ou "menor é melhor":

**Maior é melhor:**
- `bertscore`, `comet`
- `accuracy`, `precision`, `recall`
- `flesch_reading_ease`, `gulpease_index`

**Menor é melhor:**
- `final_readability_score`
- `flesch_kincaid_grade_level`
- `error`, `loss`

### Cálculo dos Scores
- **Método 1:** Normaliza métricas para 0-1 e calcula a média (valores comparáveis entre escalas diferentes)
- **Método 2:** Ordena modelos por cada métrica individualmente (sem normalização)
- **Método 3:** Calcula a média dos valores **originais** (sem normalização) das métricas selecionadas — o `final_score` resultante é diretamente comparável à pontuação composta do artigo: `(BERTScore + COMET) / 2`

### Filtro Pré-Ranking (novo)
- O filtro é aplicado antes de executar qualquer método.
- Para ativar, informe os 3 parâmetros juntos: `--filter-column`, `--filter-op`, `--filter-value`.
- Operadores aceitos:
  - Igual: `eq`, `igual`, `=`
  - Maior que: `gt`, `maior`, `>`
  - Menor que: `lt`, `menor`, `<`
- Se o filtro remover todas as linhas, o script retorna erro para evitar ranking vazio.

---
