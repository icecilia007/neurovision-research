# erg-analysis

Pipeline de processamento, anonimização e classificação de dados de ERG (Eletrorretinograma) para pesquisa sobre neurodivergência.

## O que este repositório faz

1. Processa arquivos brutos de exames ERG (formato CSV do dispositivo RETeval)
2. Consolida e anonimiza os dados dos pacientes
3. Treina modelos de classificação para prever neurodivergência a partir das features do ERG

## Estrutura

```
erg-analysis/
  scripts/          — código da pipeline (processamento, anonimização, classificação)
  studies/          — análises e notebooks por tema
    erg_waveform_analysis/     — análise exploratória das formas de onda
    neurodivergencia_classification/  — modelos de classificação de neurodivergência
  data/             — dataset público para reprodução dos resultados
  docs/             — documentação detalhada de cada etapa
  PIPELINE.md       — guia principal de execução
  requirements.txt  — dependências Python
```

## Notebook de análises e resultados finais

O notebook com os resultados finais da pesquisa está em
`studies/neurodivergencia_classification/notebooks/`:

| Notebook | Descrição |
|---|---|
| `neurodivergencia_classification_describre_final.ipynb` | **Notebook final** com análise multi-label completa, resultados consolidados e figuras para o TCC |

As análises exploratórias intermediárias foram consolidadas neste notebook e não estão mais no repositório.

## Como rodar

Consulte [PIPELINE.md](PIPELINE.md) para o fluxo completo de execução.

Para reproduzir apenas os resultados de classificação sem rodar a pipeline completa, basta o `data/classification_dataset.parquet` já disponível neste repositório (ver seção [Dados](#dados)).

## Dependências principais

- Python 3.10+
- PySpark (etapa de consolidação)
- Polars, PyArrow (processamento de dados)
- scikit-learn, imbalanced-learn (classificação)

```bash
pip install -r requirements.txt
```

## Dados

### Dataset público (reprodução dos resultados)

O único dado disponibilizado publicamente é o dataset de classificação já pré-processado e anonimizado, utilizado diretamente pelo notebook de classificação:

| Arquivo | Caminho no repositório | Descrição |
|---------|----------------------|-----------|
| `classification_dataset.parquet` | `data/` | Dataset final com features por paciente, pronto para treinar os modelos |

Este é o único arquivo necessário para reproduzir os resultados de classificação do TCC. O notebook detecta automaticamente a presença desse arquivo e o utiliza quando os dados brutos da pipeline não estão disponíveis.

Os notebooks de análise de formas de onda (`03_raw_waveform_signal_quality.ipynb` e `06_signal_atlas_and_research_summary.ipynb`) não estão neste repositório por ultrapassarem o limite de 100 MB do GitHub (156 MB e 122 MB respectivamente) e por dependerem de dados brutos não compartilháveis — veja a seção abaixo.

### Dados brutos e intermediários — restrição LGPD

Os demais dados da pesquisa (brutos, intermediários e anonimizados) **não são disponibilizados publicamente**, mesmo na forma anonimizada, em cumprimento à [Lei Geral de Proteção de Dados Pessoais (LGPD — Lei nº 13.709/2018)](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm). Os dados envolvem registros clínicos de pacientes e só podem ser compartilhados mediante análise de justificativa e aprovação formal.

Dados não compartilháveis:

- Dados brutos de exames ERG (`exam/`, `waveform/`, `patients-data/`)
- Datasets intermediários gerados pela pipeline (`output/data/anonymized/`)
- Mapeamentos de anonimização (`id_map`, `staging/`)
- Dados de questionários (`questionnaire_*.parquet`)
- Artefatos de modelos treinados (`output/model-training/`)

**Para solicitar acesso** a esses dados mediante justificativa, entre em contato:

- **icsbarbosa@sga.pucminas.br**
- **izabelaengineer@gmail.com**

Descreva o objetivo da pesquisa e como os dados serão utilizados. O acesso está condicionado à análise da solicitação e ao cumprimento das obrigações legais aplicáveis.
