# 00 — Inventário do Projeto

> Nota: O projeto não possui diretório `scripts/`. A documentação cobre toda a base de código existente: `backend/` e `frontend/`.

---

## Estrutura de Diretórios Completa

```
holhos-project/
├── docker-compose.yml          — Orquestração dos 4 containers (nginx, frontend, backend, db)
├── nginx.conf                  — Configuração do proxy reverso
├── clear_db.sh                 — Script shell para limpeza do banco
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py              — Ambiente de migração Alembic
│   │   ├── script.py.mako
│   │   └── versions/           — 12 arquivos de migração (histórico do schema)
│   └── app/
│       ├── main.py             — Entrada FastAPI; configura CORS e routers
│       ├── database.py         — Configuração SQLAlchemy (engine, SessionLocal, Base)
│       ├── config.py           — Settings (DATABASE_URL, FRONTEND_BASE_URL via IP público)
│       ├── dependencies.py     — Injeção de dependência FastAPI (todos os Services)
│       ├── models/             — ORM SQLAlchemy
│       │   ├── user.py         — User + enums GenderEnum, EducationLevelEnum
│       │   ├── questionnaire.py — Questionnaire, QuestionnaireItem + enums
│       │   ├── question.py     — Question, QuestionOption + QuestionTypeEnum
│       │   ├── instruction.py  — Instruction
│       │   ├── response.py     — QuestionnaireSubmission, Answer
│       │   └── __init__.py     — Exporta todos os modelos + Base
│       ├── schemas/            — Pydantic v2 (validação de I/O)
│       │   ├── user.py
│       │   ├── questionnaire.py
│       │   ├── question.py
│       │   ├── instruction.py
│       │   ├── response.py
│       │   └── analytics.py    — FilterParams, CrosstabRequest, CustomExportRequest
│       ├── services/           — Camada de negócio
│       │   ├── user_service.py
│       │   ├── questionnaire_service.py
│       │   ├── question_service.py
│       │   ├── response_service.py
│       │   ├── report_service.py
│       │   ├── analytics_service.py
│       │   └── chyps_config.py — Configuração do instrumento CHYPS-V (escalas, itens, filtros)
│       ├── api/
│       │   └── v1/
│       │       ├── api.py      — Monta o APIRouter principal
│       │       └── endpoints/
│       │           ├── users.py
│       │           ├── questions.py
│       │           ├── questionnaires.py
│       │           ├── responses.py
│       │           ├── reports.py
│       │           └── analytics.py
│       └── utils/
│           └── crypto.py       — Base64 encoding/decoding de IDs de questionários
└── frontend/
    ├── Dockerfile
    ├── requirements.txt
    ├── app.py                  — Entrada NiceGUI; define página raiz e executa server
    ├── config.py               — Config (API_BASE_URL, STORAGE_SECRET)
    ├── router.py               — clear_and_render helper + rota /questionnaire/{id}/respond
    ├── pages/
    │   ├── auth_page.py        — Página de login/cadastro
    │   ├── dashboard.py        — Dashboard pós-login com cards de navegação
    │   ├── questionnaire_list_page.py — Lista de questionários do usuário
    │   ├── questionnaire_create_page.py — Editor de questionários (criar/editar)
    │   ├── questionnaire_answer_page.py — Página pública de resposta
    │   ├── reports_page.py     — Lista de questionários com métricas de relatório
    │   ├── report_detailed.py  — Relatório analítico completo com gráficos
    │   ├── report_analytics.py — Analytics simplificados (distribuição de scores)
    │   └── custom_export_page.py — Exportação personalizada (CSV/XLSX/JSON)
    ├── components/
    │   ├── auth/
    │   │   ├── login_form.py
    │   │   ├── signup_form.py
    │   │   └── auth_modal.py   — Modal de autenticação para respondentes
    │   ├── questionnaire/
    │   │   ├── question_component.py   — Componente UI individual de pergunta (texto, tipo, peso, opções)
    │   │   ├── question_item_editor.py — Editor de perguntas/termos/instruções
    │   │   └── sortable_column.py — Wrapper Vue/Sortable.js para drag-and-drop
    │   ├── dashboard/
    │   │   ├── summary_cards.py     — Cards de estatísticas globais
    │   │   ├── pie_chart_card.py    — Gráfico pizza via Plotly
    │   │   ├── bar_chart_card.py    — Gráfico barra via Plotly
    │   │   ├── subscale_section.py  — Subescalas CHYPS-V com histogramas
    │   │   ├── reliability_card.py  — Alpha de Cronbach com interpretação
    │   │   ├── crosstab_tool.py     — Tabulação cruzada interativa
    │   │   ├── filter_sidebar.py    — Filtros demográficos
    │   │   ├── export_buttons.py    — Botões de exportação CSV/JSON
    │   │   └── text_responses_table.py
    │   └── shared/
    │       └── plotly_config.py — Funções de criação de figuras Plotly
    ├── services/
    │   ├── api_client.py         — Cliente HTTP com requests.Session
    │   ├── user_service.py
    │   ├── questionnaire_service.py
    │   ├── question_service.py
    │   ├── instruction_service.py
    │   ├── response_service.py
    │   ├── report_service.py
    │   ├── analytics_service.py
    │   └── custom_export_service.py — Conversão local para CSV/XLSX/JSON
    └── utils/
        ├── session_manager.py    — Gerencia sessão do usuário no storage NiceGUI
        └── validators.py         — Validações de email, senha, telefone, idade
```

---

## Inventário de Arquivos por Responsabilidade

### Backend

| Arquivo | Responsabilidade | Consome | Produz |
|---|---|---|---|
| `app/main.py` | Bootstrap FastAPI, CORS, routers | `api.py`, `database.py`, `models/__init__.py` | App ASGI |
| `app/database.py` | Engine SQLAlchemy, SessionLocal, Base | `config.py` | Sessão DB injetável |
| `app/config.py` | Settings via pydantic-settings + detecção de IP público | `.env` | `Settings` singleton |
| `app/dependencies.py` | Instâncias de serviços para injeção FastAPI | Todos os services | `*Dep` Annotated types |
| `app/utils/crypto.py` | Encode/decode Base64 de IDs de questionários | stdlib | `str` encodado ou `int` decodado |
| `app/models/user.py` | Tabela `users` | `database.Base` | ORM `User` |
| `app/models/questionnaire.py` | Tabelas `questionnaires`, `questionnaire_items` | `database.Base` | ORM `Questionnaire`, `QuestionnaireItem` |
| `app/models/question.py` | Tabelas `questions`, `question_options` | `database.Base` | ORM `Question`, `QuestionOption` |
| `app/models/instruction.py` | Tabela `instructions` | `database.Base` | ORM `Instruction` |
| `app/models/response.py` | Tabelas `questionnaire_submissions`, `answers` | `database.Base` | ORM `QuestionnaireSubmission`, `Answer` |
| `app/schemas/user.py` | Validação I/O usuários | `models/user.py` enums | Pydantic schemas |
| `app/schemas/questionnaire.py` | Validação I/O questionários | `models/questionnaire.py` enums | Pydantic schemas |
| `app/schemas/question.py` | Validação I/O perguntas | `models/question.py` enums | Pydantic schemas |
| `app/schemas/instruction.py` | Validação I/O instruções | — | Pydantic schemas |
| `app/schemas/response.py` | Validação I/O submissões | — | Pydantic schemas |
| `app/schemas/analytics.py` | Validação I/O analytics/export | — | `FilterParams`, `CrosstabRequest`, `CustomExportRequest` |
| `app/services/user_service.py` | CRUD de usuários + autenticação bcrypt | `models/user.py`, passlib | `User` ORM |
| `app/services/questionnaire_service.py` | CRUD de questionários + geração de links | Todos models, `crypto.py`, `config.py` | `Questionnaire` ORM, `GenerateLinkResponse` |
| `app/services/question_service.py` | CRUD de perguntas e opções | `models/question.py` | `Question` ORM |
| `app/services/response_service.py` | Validação e persistência de submissões + scoring | `models/*` | `QuestionnaireSubmission` ORM |
| `app/services/report_service.py` | Relatórios completos, sumários, exportação wide-format | Todos models | `Dict` com dados estruturados |
| `app/services/analytics_service.py` | Scores CHYPS-V, alpha de Cronbach, crosstab, filtragem | `chyps_config.py`, numpy, scipy | `Dict` com análises |
| `app/services/chyps_config.py` | Constantes do instrumento CHYPS-V | — | Dicts de configuração |
| `app/api/v1/api.py` | Monta roteador com prefixos | Todos endpoints | `APIRouter` |
| `app/api/v1/endpoints/users.py` | Endpoints REST /users/* | `UserService` | JSON responses |
| `app/api/v1/endpoints/questions.py` | Endpoints REST /questions/* | `QuestionService` | JSON responses |
| `app/api/v1/endpoints/questionnaires.py` | Endpoints REST /questionnaires/* | `QuestionnaireService` | JSON responses |
| `app/api/v1/endpoints/responses.py` | Endpoints REST /responses/* | `ResponseService` | JSON responses |
| `app/api/v1/endpoints/reports.py` | Endpoints REST /reports/* (full, summary, export) | `ReportService` | JSON/CSV/XLSX responses |
| `app/api/v1/endpoints/analytics.py` | Endpoints REST /analytics/* (CHYPS, crosstab, dashboard) | `AnalyticsService`, `ReportService` | JSON responses |

### Frontend

| Arquivo | Responsabilidade | Consome | Produz |
|---|---|---|---|
| `app.py` | Entrada NiceGUI; rota raiz `/`; lógica de auth check | `AuthPage`, `DashboardPage`, `session_manager`, `config` | Servidor web porta 8080 |
| `router.py` | Rota pública `/questionnaire/{id}/respond` + helper `clear_and_render` | `questionnaire_answer_page` | Página de resposta |
| `config.py` | Config API_BASE_URL, STORAGE_SECRET | env vars | `Config` singleton |
| `utils/session_manager.py` | Login/logout no storage NiceGUI | `nicegui.app.storage` | Estado de sessão por usuário |
| `utils/validators.py` | Validações client-side (email, senha, telefone, idade) | stdlib re | Tuples (bool, str) |
| `services/api_client.py` | Cliente HTTP com requests.Session; trata erros HTTP | `config.py`, requests | Dict / None |
| `services/user_service.py` | Chamadas à API de usuários | `api_client` | Dict / None |
| `services/questionnaire_service.py` | Chamadas à API de questionários | `api_client` | Dict / None |
| `services/question_service.py` | Criação de perguntas | `api_client` | Dict / None |
| `services/instruction_service.py` | Criação de instruções | `api_client` | Dict / None |
| `services/response_service.py` | Submissão de respostas | `api_client` | Dict / None |
| `services/report_service.py` | Relatórios e downloads | `api_client`, requests direto | Dict / bytes |
| `services/analytics_service.py` | Dashboard data, CHYPS scores, crosstab, filtros | `api_client` | Dict / None |
| `services/custom_export_service.py` | Conversão local de dados para CSV/XLSX/JSON | csv, json, openpyxl | bytes |
| `pages/auth_page.py` | Renderiza login ou signup | `LoginForm`, `SignupForm` | UI NiceGUI |
| `pages/dashboard.py` | Dashboard com cards Questionários / Relatórios | `QuestionnaireListPage`, `ReportsPage`, `session_manager` | UI NiceGUI |
| `pages/questionnaire_list_page.py` | Lista de questionários do usuário com ações | `questionnaire_service`, `questionnaire_create_page` | UI NiceGUI |
| `pages/questionnaire_create_page.py` | Editor completo de questionários (criar/editar) | `QuestionItemEditor`, `SortableColumn`, múltiplos services | UI NiceGUI |
| `pages/questionnaire_answer_page.py` | Formulário de resposta pública | `questionnaire_service`, `response_service` | UI NiceGUI |
| `pages/reports_page.py` | Lista questionários com métricas | `report_service`, `questionnaire_service` | UI NiceGUI |
| `pages/report_detailed.py` | Relatório analítico completo CHYPS-V | `analytics_service`, todos `components/dashboard/*` | UI NiceGUI |
| `pages/report_analytics.py` | Analytics simplificados | `report_service` | UI NiceGUI |
| `pages/custom_export_page.py` | Exportação personalizada passo-a-passo | `questionnaire_service`, `report_service`, `custom_export_service` | UI NiceGUI + download |
| `components/auth/login_form.py` | Formulário de login com validação | `user_service`, `validators`, `session_manager` | UI NiceGUI |
| `components/auth/signup_form.py` | Formulário de cadastro com datepicker | `user_service`, `validators` | UI NiceGUI |
| `components/auth/auth_modal.py` | Modal de autenticação (para respondentes) | `LoginForm`, `SignupForm`, `session_manager` | ui.dialog |
| `components/questionnaire/question_component.py` | Componente UI de pergunta individual (texto, tipo, peso, opções CRUD) | nicegui | UI NiceGUI + callbacks |
| `components/questionnaire/question_item_editor.py` | Editor de item (pergunta/termo/instrução) com drag | `SortableColumn` | UI NiceGUI + callbacks |
| `components/questionnaire/sortable_column.py` | Componente Vue drag-and-drop | `sortable_column.js` | ui.element customizado |
| `components/dashboard/summary_cards.py` | Cards de estatísticas (N, média, mediana, alpha) | nicegui | UI NiceGUI |
| `components/dashboard/pie_chart_card.py` | Gráfico pizza Plotly | `plotly_config.create_pie_chart` | ui.plotly |
| `components/dashboard/bar_chart_card.py` | Gráfico barra Plotly com stats | `plotly_config.create_bar_chart` | ui.plotly |
| `components/dashboard/subscale_section.py` | Subescalas CHYPS-V com histogramas | `plotly_config.create_histogram` | UI NiceGUI |
| `components/dashboard/reliability_card.py` | Card alpha de Cronbach interpretado | nicegui | UI NiceGUI |
| `components/dashboard/crosstab_tool.py` | Tabulação cruzada com heatmap Plotly | plotly | UI NiceGUI |
| `components/dashboard/filter_sidebar.py` | Sidebar de filtros demográficos | nicegui | UI NiceGUI + callbacks |
| `components/dashboard/export_buttons.py` | Botões exportar CSV/JSON | `report_service` | UI NiceGUI |
| `components/shared/plotly_config.py` | Fábrica de figuras Plotly (pie, bar, histogram, heatmap) | plotly | `go.Figure` |
