## Instrumentos de Pesquisa sobre Neurodivergência e Hipersensibilidade Visual

<p style="text-align: justify;">Este repositório reúne os artefatos produzidos ao longo da pesquisa: (1) uma pipeline de processamento e classificação de dados de Eletrorretinograma (ERG) para predição de neurodivergência; (2) um framework de avaliação de 25 traduções do questionário CHYPS-V (Cardiff Hypersensitivity Scale, Visual) para o Português Brasileiro; e (3) o código fonte do sistema NeuroVision, utilizado para criação, distribuição e coleta de respostas do questionário CHYPS-BR.</p>

### Componentes

#### [erg-analysis](https://github.com/icecilia007/neurovision-research/tree/master/erg-analysis)

Pipeline de processamento e classificação de dados de Eletrorretinograma (ERG) para predição de neurodivergência.

- Pipeline completa de consolidação, anonimização e extração de features dos exames RETeval
- Modelos de classificação multi label (Decision Tree, Random Forest) com validação cruzada aninhada
- Notebook final com análise completa e figuras do TCC

**Dataset público:** [`classification_dataset.parquet`](https://github.com/icecilia007/neurovision-research/blob/master/erg-analysis/data/classification_dataset.parquet), dataset pré processado e anonimizado, pronto para reproduzir os resultados de classificação.

Os demais dados da pesquisa (brutos e intermediários) não são disponibilizados publicamente em cumprimento à LGPD. Para solicitar acesso, entre em contato via icsbarbosa@sga.pucminas.br ou izabelaengineer@gmail.com.

#### [cardiff-translation](https://github.com/icecilia007/neurovision-research/tree/master/cardiff-translation)

Framework de avaliação de 25 traduções do questionário CHYPS-V para o Português Brasileiro.

- Avaliação por métricas de legibilidade (ALT) e similaridade semântica (BERTScore, COMET)
- 25 modelos avaliados, sendo 12 proprietários, 9 de pesos abertos, 3 ferramentas de tradução especializada e 1 tradutor humano
- Modelo selecionado: Deepseek v3.2 deepthink (métrica composta de 0,7452)

#### [holhos-project](https://github.com/icecilia007/neurovision-research/tree/master/holhos-project)

Código fonte do [NeuroVision](https://neurovision.me/questionnaire/Mw/respond), sistema web para criação, distribuição e coleta de respostas do questionário CHYPS-BR.

- Frontend em Python com NiceGUI
- Backend em Python com FastAPI
- Banco de dados PostgreSQL 15 via Docker Compose

#### [OutrosInstrumentos](https://github.com/icecilia007/neurovision-research/tree/master/OutrosInstrumentos)

Documentos complementares da pesquisa.

### Autores e Orientadores

| Papel | Nome | E-mail | ORCID |
|:------|:-----|:-------|:------|
| Autora | Izabela Cecilia Silva Barbosa | izabelaengineer@gmail.com | [0009-0007-6514-8515](https://orcid.org/0009-0007-6514-8515) |
| Orientador | Cleiton Silva Tavares | cleitontavares@pucminas.br | [0009-0008-4235-409X](https://orcid.org/0009-0008-4235-409X) |
| Orientador | Hugo Bastos de Paula | hugodepaula@gmail.com | [0000-0002-6193-3205](https://orcid.org/0000-0002-6193-3205) |
| Orientador | Jerome Baron | jerome.baron.ufmg@gmail.com | [0000-0002-3809-7835](https://orcid.org/0000-0002-3809-7835) |
| Orientador | Ricardo Queiroz Guimarães | rg2020@gmail.com | [0000-0001-7600-855X](https://orcid.org/0000-0001-7600-855X) |

#### Instituição

PUC Minas, Engenharia de Software, 2025/2

#### Como citar

Se você usar este repositório em sua pesquisa, utilize a citação disponível no arquivo [`CITATION.cff`](https://github.com/icecilia007/neurovision-research/blob/master/CITATION.cff) ou clique em "Cite this repository" no GitHub.

Licenciado sob [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
