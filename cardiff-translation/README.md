# Cardiff Translation — CHYPS-V Evaluation Framework

> Código e dados do TCC de Engenharia de Software — PUC Minas (2025).  
> Avalia 25 traduções do questionário CHYPS-V para o Português Brasileiro combinando métricas automáticas de legibilidade (ALT), similaridade semântica (BERTScore, COMET) e ferramentas auxiliares de ranqueamento.

---

## Índice

- [Contexto da Pesquisa](#contexto-da-pesquisa)
- [Os 25 Modelos Avaliados](#os-25-modelos-avaliados)
- [Datasets](#datasets)
- [Estrutura do Repositório](#estrutura-do-repositório)
- [Pré-requisitos e Instalação](#pré-requisitos-e-instalação)
- [Fluxo Completo de Avaliação](#fluxo-completo-de-avaliação)
  - [Etapa 1 — Obter as Traduções](#etapa-1--obter-as-traduções)
  - [Etapa 2 — Legibilidade via ALT (manual)](#etapa-2--legibilidade-via-alt-manual)
  - [Etapa 3 — Similaridade Semântica (programático)](#etapa-3--similaridade-semântica-programático)
  - [Etapa 4 — Combinar os Resultados](#etapa-4--combinar-os-resultados)
  - [Etapa 5 — Ranquear e Selecionar](#etapa-5--ranquear-e-selecionar)
- [Executando o Pipeline Programático](#executando-o-pipeline-programático)
- [Ranqueando os Modelos](#ranqueando-os-modelos)
- [Gerando Histogramas](#gerando-histogramas)
- [Resultados](#resultados)
- [Referência de Métricas](#referência-de-métricas)
- [Referências Bibliográficas](#referências-bibliográficas)

---

## Contexto da Pesquisa

### O que é o CHYPS-V

O **Cardiff Hypersensitivity Scale – Visual (CHYPS-V)** é um questionário psicométrico de 20 itens desenvolvido por Price, Sumner e Powell (2025) para medir subtipos de hipersensibilidade visual em populações neurodivergentes e neurológicas. Os itens cobrem quatro domínios:

| Domínio | Itens | Exemplos |
|---------|-------|---------|
| Brightness (Brilho) | 3, 7, 9, 14, 19 | Sol, telas brilhantes, reflexos |
| Pattern (Padrões) | 1, 5, 12, 15, 20 | Listras, xadrez, grades |
| Strobing (Estroboscopia) | 2, 6, 10, 16, 18 | Câmera instável, cintilação |
| Intense Visual Environments | 4, 8, 11, 13, 17 | Supermercados, trânsito, multidões |

As respostas seguem escala de 4 pontos: Quase Nunca (0) · Ocasionalmente (1) · Frequentemente (2) · Quase Sempre (3). O gabarito de pontuação por subscala está em [docs/CHYPS-V-scoring.md](docs/CHYPS-V-scoring.md).

### Por que traduzir

A adaptação do CHYPS-V para o Português Brasileiro (CHYPS-BR) é necessária para aplicação clínica no Brasil como instrumento de triagem de hipersensibilidade visual. Este repositório documenta a seleção computacional da melhor versão traduzida entre 25 candidatas (24 modelos de IA + 1 tradutor humano profissional) antes da validação psicométrica com pacientes.

O estudo se insere no contexto de **Medidas de Desfecho Relatadas pelo Paciente (PROMs)** — instrumentos clínicos que dependem de tradução precisa e linguagem acessível para não invalidar suas propriedades psicométricas.

### Critério de seleção

A seleção do CHYPS-BR seguiu dois passos sequenciais:

```
[25 modelos]
      │
      ▼ Filtro de legibilidade: final_readability_score ≤ 8
      │  (compreensível por público com ≥ 12 anos de escolaridade)
      │
[12 elegíveis]
      │
      ▼ Ranking semântico: pontuação composta = (BERTScore + COMET) / 2
      │
[1 vencedor: Deepseek-v3.2-deepthink — composta = 0,7452]
```

Dos 25 modelos avaliados, **12 (48%) atenderam ao critério de legibilidade**.  
O modelo selecionado foi **Deepseek-v3.2-deepthink** (BERTScore = 0,7143; COMET = 0,7760; composta = 0,7452).

---

## Os 25 Modelos Avaliados

### Modelos Proprietários (12)

| Modelo | Versão / Data |
|--------|---------------|
| Claude 4.0 Sonnet | 25-07-24 |
| Claude 4.0 Sonnet Thinking | 25-07-24 |
| Claude 4.1 Opus | 24-09-30 |
| Claude 4.5 Sonnet | 25-12-10 |
| Gemini 2.5 Flash | 25-07-24 |
| Gemini 2.5 Pro | 25-06-05 |
| Gemini 3.0 Pro | 25-12-10 |
| Grok 4 | 25-07-25 |
| Grok 4.1 | 25-12-10 |
| OpenAI GPT-4.1 | 25-07-24 |
| OpenAI GPT-5.1 Pro | 25-12-10 |
| OpenAI o3 | 25-04-16 |

### Modelos de Pesos Abertos (9)

| Modelo | Versão / Data |
|--------|---------------|
| DeepSeek R1-1776 | 25-07-24 |
| DeepSeek v3 DeepThink | 25-07-24 |
| **DeepSeek v3.2 DeepThink** ★ | 25-12-10 |
| Maritaca AI Sabiá 3.1 | 25-07-24 |
| Mistral Medium 3 | 25-07-24 |
| MoonshotAI Kimi K2 | 25-07-24 |
| NVIDIA Llama 3.1 Nemotron Ultra 253B v1 | 25-07-24 |
| Qwen 3 235B A22B (no-thinking) | 25-07-24 |
| Qwen 3 Max | 25-07-24 |

### Ferramentas de Tradução Especializada (3)

| Ferramenta | Versão / Data |
|------------|---------------|
| DeepL v2 API v3.4.1 | 25-06-05 |
| DeepL v2 API v3.8.0 | 25-12-10 |
| Google Translate | 25-09-07 |

### Referência Humana (1)

| Tradutor | Data |
|----------|------|
| Profissional bilíngue (PT-BR/EN) | 25-09-30 |

> ★ Modelo selecionado como base do CHYPS-BR.

---

## Datasets

O estudo manteve dois conjuntos de arquivos de tradução, avaliando apenas o Dataset B:

| Dataset | Localização | Conteúdo | Avaliado no artigo |
|---------|-------------|----------|-------------------|
| **Dataset A** — Texto completo | `translations/plain-text/` | Título + instruções + escala de resposta + 20 itens | Não |
| **Dataset B** — Somente questões | `translations/questions-only/` | Apenas os 20 itens numerados | **Sim** |

O **Dataset B** foi escolhido para avaliação porque isola o conteúdo clínico relevante (as 20 sentenças que serão respondidas por pacientes), eliminando ruído introduzido por partes administrativas (título, instruções gerais) que são genericamente simples e não variam a qualidade clínica da tradução.

O texto de referência usado para comparação semântica é o original em inglês: [docs/CHYPS-V-questions-only.txt](docs/CHYPS-V-questions-only.txt).

---

## Estrutura do Repositório

```
cardiff-translation/
│
├── docs/
│   ├── CHYPS-V-plain-text.txt                  # Texto completo original (inglês)
│   ├── CHYPS-V-questions-only.txt              # 20 itens originais (inglês) — referência da avaliação
│   ├── CHYPS-V-original.md                     # Questionário original formatado
│   ├── CHYPS-V-scoring.md                      # Gabarito de pontuação por subscala
│   ├── textual-legibility-analysis-with-ALT.md # Fórmulas e background do ALT
│   ├── semantic-textual-similarity.md          # Background sobre BERTScore/similaridade semântica
│   └── CHYPS-V-br20-*-comments.md              # Notas dos modelos sobre escolhas tradutórias
│
├── translations/
│   ├── questions-only/   # 25 arquivos .txt — Dataset B (usado no artigo)
│   ├── plain-text/       # 25 arquivos .txt — Dataset A (não avaliado)
│   └── markdown/         # 25 arquivos .md — traduções em markdown
│
├── prompts/
│   └── prompts.md        # System prompt e perfil utilizados para solicitar as traduções
│
├── results/                                    ← PASTA PRINCIPAL DOS RESULTADOS
│   ├── questions-only/
│   │   └── original/
│   │       ├── analysis_results_alt.csv        ← ARQUIVO CENTRAL (25 modelos × 11 métricas)
│   │       ├── analysis_results.csv            # Saída do pipeline (BERTScore + COMET, sem ALT)
│   │       └── report.md                       # Relatório gerado pelo pipeline
│   └── rankings/
│       ├── ranking_method3.csv                 # Ranking usado no artigo (média BERTScore + COMET)
│       ├── ranking_method1.csv                 # Ranking por média normalizada de todas as métricas
│       ├── ranking_method2_bertscore.csv        # Top-5 por BERTScore
│       ├── ranking_method2_comet.csv            # Top-5 por COMET
│       └── ranking_method2_summary.csv          # Consolidado top-5 por métrica
│
├── plots/
│   ├── histogram_bertscore.png
│   └── histogram_comet.png
│
├── scripts/
│   ├── rank_models.py         # Script de ranqueamento (3 métodos + filtro pré-ranking)
│   ├── plot_histograms.py     # Geração de histogramas com estatísticas descritivas
│   └── RANKING_METHODS.md     # Documentação completa do script de ranking
│
├── src/
│   ├── main.py                             # Entry point — uv run python src/main.py
│   └── cardiff/
│       ├── config/config.py                    # Config e QuestionsOnlyConfig
│       ├── data/data_loader.py                 # Carregamento das traduções
│       ├── metrics/
│       │   ├── alt_metrics.py                  # Implementações locais das fórmulas ALT
│       │   └── semantic_similarity.py          # BERTScore (NeoBERTugues) + COMET
│       ├── reporting/reporting.py              # Geração do report.md
│       └── analysis/statistical_analysis.py   # Funções de análise estatística auxiliar
│
├── pyproject.toml   # Dependências gerenciadas pelo uv (Python 3.12)
└── uv.lock
```

> **Navegação rápida:** O arquivo que contém todos os resultados usados no artigo é  
> `results/questions-only/original/analysis_results_alt.csv`

---

## Pré-requisitos e Instalação

**Python 3.12** (exatamente — o projeto requer `>=3.12, <3.13`) e **[uv](https://docs.astral.sh/uv/)** como gerenciador de pacotes.

### Instalar o uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Instalar dependências

```bash
cd cardiff-translation
uv sync
```

O `uv sync` lê o `pyproject.toml` e instala todas as dependências em um ambiente virtual isolado. Principais dependências:

| Pacote | Versão | Uso |
|--------|--------|-----|
| `transformers` | ~4.40.1 | Carregar NeoBERTugues para BERTScore |
| `unbabel-comet` | ≥2.2.6 | Modelo COMET (wmt22-comet-da) |
| `bert-score` | ≥0.3.13 | Utilitários BERTScore |
| `torch` | (via transformers) | Inferência dos modelos |
| `pandas` | — | Manipulação dos CSVs |
| `matplotlib` | — | Geração de histogramas |
| `numpy` | <2.0.0 | Operações numéricas |

> Na primeira execução do pipeline, o NeoBERTugues (~1,3 GB) e o wmt22-comet-da (~1,9 GB) são baixados automaticamente do HuggingFace. Certifique-se de ter espaço em disco e conexão estável.

---

## Fluxo Completo de Avaliação

O estudo combina uma etapa manual (legibilidade no site ALT) com uma etapa programática (BERTScore + COMET via pipeline Python). O diagrama abaixo mostra o fluxo completo desde a coleta das traduções até a seleção do modelo:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ENTRADA                                                                    │
│  docs/CHYPS-V-questions-only.txt  (20 itens originais em inglês)           │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ETAPA 1 — Solicitar Traduções (manual, fora do código)                    │
│  Prompt: prompts/prompts.md                                                 │
│  Saída:  translations/questions-only/*.txt  (25 arquivos)                  │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
┌─────────────────────────┐   ┌──────────────────────────────────────────┐
│  ETAPA 2 — ALT (manual) │   │  ETAPA 3 — Pipeline Python               │
│  Site: legibilidade.com  │   │  Comando: uv run python src/main.py      │
│  Para cada tradução:    │   │           --config questions-only        │
│  · cole o texto         │   │  Saída: analysis_results.csv             │
│  · registre 7 métricas  │   │  Métricas: BERTScore + COMET             │
└───────────┬─────────────┘   └──────────────────┬───────────────────────┘
            │                                     │
            └──────────────┬──────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ETAPA 4 — Combinar (manual)                                                │
│  Adicionar as 7 colunas ALT ao analysis_results.csv                         │
│  Salvar como: results/questions-only/original/analysis_results_alt.csv     │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ETAPA 5 — Ranquear e Selecionar                                           │
│  Comando: uv run python scripts/rank_models.py                              │
│           --input results/questions-only/original/analysis_results_alt.csv │
│           --all --priority bertscore comet --columns bertscore comet        │
│           --filter-column final_readability_score --filter-op lt            │
│           --filter-value 9                                                  │
│  Saída: results/rankings/ranking_method3.csv                                │
│  Modelo selecionado: Deepseek-v3.2-deepthink (composta = 0,7452)           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Etapa 1 — Obter as Traduções

As traduções foram solicitadas individualmente a cada modelo via chat/API usando o prompt disponível em [prompts/prompts.md](prompts/prompts.md). O prompt define o papel de neurofisiologista e solicita a tradução completa do CHYPS-V mantendo estrutura e formatação.

Cada arquivo de saída segue a convenção:

```
translations/questions-only/CHYPS-V-br20-<Modelo>-<AAAA-MM-DD>.txt
```

Apenas os 20 itens traduzidos foram salvos nos arquivos de `questions-only/` — as instruções e demais partes do questionário, presentes nas traduções completas, foram descartadas para esse dataset.

---

### Etapa 2 — Legibilidade via ALT (manual)

**ALT** (Análise de Legibilidade Textual) é a ferramenta web em [legibilidade.com](https://legibilidade.com) que calcula índices de legibilidade adaptados para o Português Brasileiro, usando a lista das 5.000 palavras mais frequentes para classificar "palavras complexas". O site foi usado manualmente porque sua definição de "palavra complexa" (fora das 5.000 mais frequentes) não pode ser replicada pela implementação local em `src/cardiff/metrics/alt_metrics.py`, que usa contagem de sílabas como proxy.

#### Procedimento passo a passo

Para **cada arquivo** em `translations/questions-only/`:

1. Abra [legibilidade.com](https://legibilidade.com) no navegador.
2. Cole o conteúdo do arquivo `.txt` no campo de texto.
3. Configure os parâmetros de análise:
   - **"Considerar nova sentença":** marque a opção para linhas terminadas por ponto e vírgula (`;`) ou dois-pontos (`:`) seguidos de quebra de linha — os itens do CHYPS-V são frases declarativas que terminam nesses caracteres antes do próximo item.
   - **"Remover da contagem de palavras":** marque preposições, artigos, pronomes e suas combinações.
4. Clique em **Analisar**.
5. Registre os **7 valores** retornados pelo site (ver tabela abaixo).
6. Repita para os outros 24 arquivos.

#### Métricas extraídas do ALT

| Coluna no CSV | Escala | Interpretação |
|---------------|--------|---------------|
| `flesch_reading_ease` | 0–100 | Maior = mais fácil de ler |
| `gulpease_index` | 0–100 | Maior = mais fácil de ler |
| `flesch_kincaid_grade_level` | 0–20 | Menor = texto mais simples (anos de estudo) |
| `gunning_fog_index` | 0–20 | Menor = menos palavras complexas |
| `automated_readability_index` | 0–20 | Menor = mais simples |
| `coleman_liau_index` | 0–20 | Menor = mais simples |
| `final_readability_score` | 0–20 | **Média dos quatro índices 0–20 — critério de elegibilidade** |

O `final_readability_score` é a **média aritmética** dos quatro índices de escala 0–20 (Flesch-Kincaid, Gunning Fog, ARI e Coleman-Liau). Um valor ≤ 8 indica que o texto é compreensível por pessoas com pelo menos 12 anos de escolaridade — critério de elegibilidade adotado no estudo.

> Fórmulas completas e contexto metodológico: [docs/textual-legibility-analysis-with-ALT.md](docs/textual-legibility-analysis-with-ALT.md).

---

### Etapa 3 — Similaridade Semântica (programático)

O script `src/main.py` percorre os 25 arquivos em `translations/questions-only/`, computa BERTScore e COMET para cada um em relação ao original em inglês e salva `results/questions-only/original/analysis_results.csv`.

#### BERTScore

Implementado em `src/cardiff/metrics/semantic_similarity.py` usando **NeoBERTugues** ([lorenzocc/NeoBERTugues](https://huggingface.co/lorenzocc/NeoBERTugues)), modelo BERT português com suporte a 8.192 tokens.

**Como funciona:**
1. Tokeniza o texto candidato (tradução PT-BR) e o texto de referência (original EN).
2. Gera embeddings contextuais para cada token via NeoBERTugues.
3. Calcula similaridade cosseno entre cada par de tokens (candidato × referência).
4. Computa **Precisão** (melhor match de cada token do candidato na referência) e **Recall** (melhor match de cada token da referência no candidato).
5. Retorna o **F1** = média harmônica entre Precisão e Recall.

O NeoBERTugues foi escolhido por ser treinado especificamente para Português e suportar textos longos (8.192 tokens), evitando truncamento nos questionários completos.

#### COMET

Implementado usando **wmt22-comet-da** ([Unbabel/wmt22-comet-da](https://huggingface.co/Unbabel/wmt22-comet-da)), modelo neural treinado em avaliações humanas de qualidade de tradução (Direct Assessment).

**Entradas para o COMET:**
- `src`: texto-fonte (original em inglês)
- `mt`: tradução candidata (português)
- `ref`: referência (o próprio original em inglês, usado como âncora semântica)

O COMET retorna um score de qualidade de tradução correlacionado com julgamento humano.

---

### Etapa 4 — Combinar os Resultados

Após executar as Etapas 2 e 3, você terá:
- `results/questions-only/original/analysis_results.csv` — BERTScore e COMET para os 25 modelos (gerado pelo pipeline)
- As 7 colunas de legibilidade coletadas manualmente no ALT

**Para criar o arquivo consolidado:**

1. Abra `analysis_results.csv` em uma planilha ou editor de CSV.
2. Adicione as 7 colunas do ALT para cada modelo, respeitando a ordem das linhas.
3. Salve como `results/questions-only/original/analysis_results_alt.csv`.

**Estrutura final do CSV** (11 colunas):

```
model_id, date,
flesch_reading_ease, gulpease_index, flesch_kincaid_grade_level,
gunning_fog_index, automated_readability_index, coleman_liau_index,
final_readability_score,
bertscore, comet
```

> O arquivo já pré-computado está disponível em `results/questions-only/original/analysis_results_alt.csv` (25 linhas × 11 colunas).

---

### Etapa 5 — Ranquear e Selecionar

Com o CSV consolidado, execute o script de ranking aplicando o filtro de legibilidade e ranqueando pelos scores semânticos:

```bash
uv run python scripts/rank_models.py \
  --input results/questions-only/original/analysis_results_alt.csv \
  --all \
  --priority bertscore comet \
  --columns bertscore comet \
  --filter-column final_readability_score \
  --filter-op lt \
  --filter-value 9
```

O `--filter-value 9` com operador `lt` (menor que) mantém apenas modelos com `final_readability_score < 9`, equivalente a ≤ 8 para valores inteiros — os 12 elegíveis. O `--all` executa os três métodos de ranking sobre esse subconjunto.

O ranking decisivo é o **Método 3** (`results/rankings/ranking_method3.csv`): média aritmética de BERTScore e COMET para os modelos filtrados. Esse valor é a **pontuação composta** citada no artigo.

---

## Executando o Pipeline Programático

```bash
# Avaliar o Dataset B — somente questões (configuração usada no artigo)
uv run python src/main.py --config questions-only

# Avaliar o Dataset A — texto completo
uv run python src/main.py --config default
```

O pipeline:
1. Lê as configurações de `src/cardiff/config/config.py` (`QuestionsOnlyConfig` ou `Config`).
2. Carrega as traduções de `translations/<config>/`.
3. Calcula BERTScore e COMET para cada tradução.
4. Salva `results/<config>/original/analysis_results.csv`.
5. Gera `results/<config>/original/report.md` com estatísticas descritivas.

> **Saída:** `analysis_results.csv` (sem sufixo `_alt`). Os valores de legibilidade precisam ser adicionados manualmente conforme a Etapa 2.

**Tempo estimado de execução** (CPU, sem GPU): ~2–5 min por tradução para BERTScore + ~30 s para COMET. Para 25 traduções: ~1–2 horas total. Com GPU CUDA disponível, o BERTScore acelera significativamente.

---

## Ranqueando os Modelos

`scripts/rank_models.py` implementa três métodos de ranqueamento:

| Método | O que faz |
|--------|-----------|
| **1** | Média normalizada (0-1) de **todas** as colunas numéricas do CSV |
| **2** | Top-N por **cada métrica individualmente** (`--priority`) |
| **3** | Média dos valores **originais** de **colunas selecionadas** (`--columns`) — usado no artigo |

O `final_score` do Método 3 é a média aritmética dos valores brutos das colunas escolhidas, diretamente comparável à pontuação composta `(BERTScore + COMET) / 2` descrita no artigo.

Consulte [scripts/RANKING_METHODS.md](scripts/RANKING_METHODS.md) para referência completa de parâmetros e exemplos de filtro.

---

## Gerando Histogramas

```bash
uv run python scripts/plot_histograms.py \
  --input results/questions-only/original/analysis_results_alt.csv \
  --columns bertscore comet \
  --output plots
```

Gera `plots/histogram_bertscore.png` e `plots/histogram_comet.png`. Cada histograma inclui caixa de estatísticas (média, desvio padrão, mínimo, máximo, amplitude).

Parâmetros disponíveis:

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `--input` | — | Arquivo CSV de entrada (obrigatório) |
| `--columns` | — | Colunas a plotar, separadas por espaço (obrigatório) |
| `--output` | diretório atual | Pasta de saída para os PNGs |
| `--bins` | 10 | Número de bins do histograma |

---

## Resultados

### Arquivo principal

**`results/questions-only/original/analysis_results_alt.csv`** — 25 linhas (uma por modelo), 11 colunas. Este é o arquivo central de todos os resultados do artigo.

### Tabela completa (25 modelos)

Modelos em **negrito** atenderam ao critério de elegibilidade (`final_readability_score ≤ 8`). ★ = modelo selecionado.

| Modelo | Data | Final read. | BERTScore | COMET |
|--------|------|-------------|-----------|-------|
| Claude-4.0-Sonnet | 25-07-24 | 9 | 0,7182 | 0,7471 |
| Claude-4.0-Sonnet-Thinking | 25-07-24 | 9 | 0,7108 | 0,7442 |
| **Claude-4.1-Opus** | 24-09-30 | **8** | 0,7121 | 0,7523 |
| Claude-4.5-Sonnet | 25-12-10 | 10 | 0,7162 | 0,7576 |
| **DeepL-v2-api-v3.4.1** | 25-06-05 | **8** | 0,7062 | 0,7737 |
| DeepL-v2-api-v3.8.0 | 25-12-10 | 9 | 0,7137 | 0,7700 |
| DeepSeek-R1-1776 | 25-07-24 | 9 | 0,6958 | 0,7728 |
| **Deepseek-v3-deepthink** | 25-07-24 | **8** | 0,7095 | 0,7513 |
| **Deepseek-v3.2-deepthink ★** | 25-12-10 | **8** | 0,7143 | 0,7760 |
| Gemini-2.5-Flash | 25-07-24 | 9 | 0,7175 | 0,7611 |
| **Gemini-2.5-Pro** | 25-06-05 | **7** | 0,7132 | 0,7636 |
| Gemini-3.0-Pro | 25-12-10 | 9 | 0,7154 | 0,7430 |
| **google-translate** | 25-09-07 | **8** | 0,7108 | 0,7465 |
| **Grok-4** | 25-07-25 | **8** | 0,7170 | 0,7405 |
| **Grok-4.1** | 25-12-10 | **8** | 0,7183 | 0,7363 |
| **Human** | 25-09-30 | **7** | 0,7185 | 0,7332 |
| Maritaca-ai-Sabia-3.1 | 25-07-24 | 9 | 0,7134 | 0,7463 |
| Mistral-Medium-3 | 25-07-24 | 10 | 0,7155 | 0,7500 |
| **MoonshotAI-Kimi-K2** | 25-07-24 | **7** | 0,7027 | 0,7395 |
| Nvidia-Llama-3.1-Nemotron-Ultra-253B-v1 | 25-07-24 | 9 | 0,7152 | 0,7305 |
| **OpenAI-GPT-4.1** | 25-07-24 | **8** | 0,7090 | 0,7490 |
| OpenAI-GPT-5.1-Pro | 25-12-10 | 9 | 0,7100 | 0,7461 |
| OpenAI-o3 | 25-04-16 | 9 | 0,7122 | 0,7486 |
| qwen-3-235b-a22b-no-thinking | 25-07-24 | 10 | 0,7106 | 0,7575 |
| **qwen-3-max** | 25-07-24 | **8** | 0,7007 | 0,7684 |

### Ranking dos 12 modelos elegíveis

Pontuação composta = `(BERTScore + COMET) / 2`.

| # | Modelo | Legibilidade | BERTScore | COMET | Composta |
|---|--------|-------------|-----------|-------|----------|
| 1 | **Deepseek-v3.2-deepthink** | 8 | 0,7143 | 0,7760 | 0,7452 |
| 2 | DeepL-v2-api-v3.4.1 | 8 | 0,7062 | 0,7737 | 0,7399 |
| 3 | Gemini-2.5-Pro | 7 | 0,7132 | 0,7636 | 0,7384 |
| 4 | qwen-3-max | 8 | 0,7007 | 0,7684 | 0,7346 |
| 5 | Claude-4.1-Opus | 8 | 0,7121 | 0,7523 | 0,7322 |
| 6 | Deepseek-v3-deepthink | 8 | 0,7095 | 0,7513 | 0,7304 |
| 7 | OpenAI-GPT-4.1 | 8 | 0,7090 | 0,7490 | 0,7290 |
| 8 | Grok-4 | 8 | 0,7170 | 0,7405 | 0,7288 |
| 9 | google-translate | 8 | 0,7108 | 0,7465 | 0,7286 |
| 10 | Grok-4.1 | 8 | 0,7183 | 0,7363 | 0,7273 |
| 11 | Human | 7 | 0,7185 | 0,7332 | 0,7258 |
| 12 | MoonshotAI-Kimi-K2 | 7 | 0,7027 | 0,7395 | 0,7211 |

### Arquivos de ranking gerados

| Arquivo | Conteúdo |
|---------|----------|
| `results/rankings/ranking_method3.csv` | 12 elegíveis ranqueados por média BERTScore + COMET — **usado no artigo** |
| `results/rankings/ranking_method1.csv` | 12 elegíveis ranqueados por média normalizada de todas as métricas |
| `results/rankings/ranking_method2_bertscore.csv` | Top-5 por BERTScore |
| `results/rankings/ranking_method2_comet.csv` | Top-5 por COMET |
| `results/rankings/ranking_method2_summary.csv` | Consolidado top-5 por métrica |

---

## Referência de Métricas

### Legibilidade — obtida manualmente no site ALT

| Métrica | Escala | Maior é melhor? | Notas |
|---------|--------|-----------------|-------|
| `flesch_reading_ease` | 0–100 | Sim | — |
| `gulpease_index` | 0–100 | Sim | Não precisou ajuste para PT |
| `flesch_kincaid_grade_level` | 0–20 | Não | Anos de estudo para compreensão |
| `gunning_fog_index` | 0–20 | Não | Usa lista das 5.000 palavras mais frequentes em PT |
| `automated_readability_index` | 0–20 | Não | Baseado em letras/palavras e palavras/sentenças |
| `coleman_liau_index` | 0–20 | Não | — |
| `final_readability_score` | 0–20 | Não | Média dos quatro acima; **critério de elegibilidade: ≤ 8** |

### Similaridade semântica — calculada pelo pipeline

| Métrica | Modelo HuggingFace | Maior é melhor? | Escala |
|---------|-------------------|-----------------|--------|
| `bertscore` | `lorenzocc/NeoBERTugues` | Sim | ~0,69–0,73 (neste corpus) |
| `comet` | `Unbabel/wmt22-comet-da` | Sim | ~0,73–0,78 (neste corpus) |

A amplitude observada no corpus foi baixa: BERTScore ≈ 0,023; COMET ≈ 0,046 — indicando alta homogeneidade semântica entre as 25 traduções, o que reforça a importância do critério de legibilidade como desempate primário.

---

## Referências Bibliográficas

- Price, A., Sumner, P., & Powell, G. (2025). Understanding the subtypes of visual hypersensitivity: Four coherent factors and their measurement with the Cardiff Hypersensitivity Scale (CHYPS). *Vision Research*, 233, 108610.
- Price, A., Sumner, P., & Powell, G. (2025). The subtypes of visual hypersensitivity are transdiagnostic across neurodivergence, neurology and mental health. *Vision Research*, 234, 108640.
- Moreno, G. C. L., et al. (2022). ALT: um software para análise de legibilidade de textos em Língua Portuguesa. *arXiv:2203.12135*.
- Zhang, T., et al. (2020). BERTScore: Evaluating Text Generation with BERT. *ICLR 2020*.
- Rei, R., et al. (2020). COMET: A Neural Framework for MT Evaluation. *EMNLP 2020*.
