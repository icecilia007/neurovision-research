# holhos-project — Plataforma de Questionários (NeuroVision)

Código-fonte do **NeuroVision** ([neurovision.me](https://neurovision.me)): sistema web usado na pesquisa para criar, distribuir e coletar as respostas do questionário CHYPS-BR. As respostas exportadas por este sistema são a entrada direta de `erg-analysis/scripts/questionnaire/step1_parse.py`.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | Python + NiceGUI (componentes Vue.js server-side) |
| Backend | Python + FastAPI + Uvicorn |
| Banco de dados | PostgreSQL 15 |
| ORM / Migrações | SQLAlchemy 2.0 + Alembic (14 migrações) |
| Analytics | numpy + scipy |
| Gráficos | Plotly (via NiceGUI) |
| Infraestrutura | Docker Compose (4 containers: nginx, frontend, backend, db) |

---

## Como executar

**Pré-requisito:** Docker e Docker Compose instalados.

```bash
docker compose up --build
```

Na **primeira execução**, aplique as migrações:

```bash
docker compose exec backend alembic upgrade head
```

A aplicação fica disponível em `http://localhost:8080`.

---

## Estrutura principal

```
holhos-project/
  backend/
    app/
      models/              — ORM SQLAlchemy (8 tabelas)
      schemas/             — Validação Pydantic v2
      services/            — Camada de negócio (6 classes de serviço)
        chyps_config.py    — Configuração do instrumento CHYPS-V
      api/v1/endpoints/    — 34 endpoints REST
    alembic/versions/      — Histórico de migrações do schema
  frontend/
    pages/                 — 9 páginas NiceGUI
    components/            — ~18 componentes (auth, questionnaire, dashboard)
    services/              — Clientes HTTP para o backend
  docker-compose.yml
  nginx.conf
  docs/diagrams/           — Documentação técnica detalhada
```

Ver [`docs/diagrams/00_inventory.md`](docs/diagrams/00_inventory.md) para o inventário completo de arquivos com responsabilidades.

---

## Conexão com erg-analysis

O endpoint `GET /api/v1/reports/questionnaires/{id}/export?format=json` gera o arquivo JSON consumido por `erg-analysis/scripts/questionnaire/step1_parse.py`. O campo `caption` de cada resposta (`Q1`–`Q20`) é a chave que o pipeline usa para identificar os itens CHYPS.

Respostas são anônimas desde a migração `0b772bfe0146_remove_respondent_personal_data`, que removeu todos os campos de identificação pessoal dos respondentes antes da exportação.

---

## Instrumento CHYPS-V

Configurado em `backend/app/services/chyps_config.py`:

- **20 itens** (Q1–Q20), escala Likert 0–3, score global 0–60
- **4 subescalas** (5 itens cada): Brilho · Padrão · Estroboscópico · Ambiente Visual Intenso
- Analytics no relatório completo: Alpha de Cronbach + correlação de Spearman item a item
- Filtros demográficos disponíveis: diagnóstico prévio · uso de medicação psiquiátrica · ano de nascimento

---

## Documentação técnica

[`docs/diagrams/`](docs/diagrams/) contém diagramas de componentes, classes, fluxo de execução, entidades e arquitetura. Ponto de entrada: [`docs/diagrams/99_system_summary.md`](docs/diagrams/99_system_summary.md).
