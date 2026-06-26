# 04 — Fluxos de Execução

## Pontos de Entrada

| Ponto | Comando | Porta |
|---|---|---|
| Backend | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | 8000 (interno) |
| Frontend | `python app.py` | 8080 (interno) |
| Proxy | nginx (via docker-compose) | 8080 (externo) |

---

## Fluxo 1: Inicialização do Backend

```mermaid
flowchart TD
    A[uvicorn app.main:app] --> B[Base.metadata.create_all\ncria tabelas se não existirem]
    B --> C[FastAPI app = FastAPI]
    C --> D[Adiciona CORSMiddleware\nallow_origins=asterisco]
    D --> E[include_router api_router prefix=/api/v1]
    E --> F[Servidor pronto em :8000]
    F --> G{Request chegou}
    G --> H[/api/v1/users/*]
    G --> I[/api/v1/questions/*]
    G --> J[/api/v1/questionnaires/*]
    G --> K[/api/v1/responses/*]
    G --> L[/api/v1/reports/*]
    G --> M[/api/v1/analytics/*]
```

---

## Fluxo 2: Inicialização do Frontend

```mermaid
flowchart TD
    A[python app.py] --> B[ui.page / registra handler]
    B --> C[ui.run host=0.0.0.0 port=8080]
    C --> D[Router registra /questionnaire/id/respond]
    D --> E[Servidor NiceGUI pronto]
    E --> F{Request /}
    F --> G{session_manager.is_authenticated?}
    G -->|Sim| H[render_dashboard]
    G -->|Não| I[render_login]
    I --> J[AuthPage.render]
    J --> K[LoginForm ou SignupForm]
    H --> L[DashboardPage.render]
    L --> M[Cards: Questionários e Relatórios]
```

---

## Fluxo 3: Login de Usuário

```mermaid
flowchart TD
    A[Usuário clica Entrar] --> B[LoginForm._on_login]
    B --> C[validators.validate_email]
    C -->|Inválido| D[error_label.text = erro]
    C -->|Válido| E[validators.validate_password]
    E -->|Inválido| D
    E -->|Válido| F[user_service.authenticate_user\nPOST /users/login]
    F --> G[api_client.post /users/login]
    G --> H{Resposta HTTP}
    H -->|Erro 401| I[Exceção: Email ou senha inválidos]
    I --> D
    H -->|200 success=True| J[GET /users/{user_id}]
    J --> K[Retorna dados completos do usuário]
    K --> L[session_manager.login user]
    L --> M[ui.notify Bem-vindo!]
    M --> N[on_success_callback → render_dashboard]
```

---

## Fluxo 4: Criação de Questionário

```mermaid
flowchart TD
    A[Usuário clica Criar Questionário] --> B[questionnaire_create_page\nCria state dict]
    B --> C[Usuário preenche título, descrição, ordem]
    C --> D[Clica Adicionar Pergunta / Instrução / Termo]
    D --> E[Cria QuestionItemEditor]
    E --> F[Usuário edita itens e opções\nDrag-and-drop disponível]
    F --> G[Usuário clica Salvar]
    G --> H[_sync_form_data + _sync_all_editors_data]
    H --> I[_validate: título, textos, opções, is_correct]
    I -->|Inválido| J[ui.notify com erro]
    I -->|Válido| K{Para cada item}
    K -->|instruction| L[POST /questionnaires/instructions]
    K -->|question/term| M[POST /questions/]
    L --> N[Obtém item_id]
    M --> N
    N --> O[Monta built_items com item_id]
    O --> P{Todos itens criados?}
    P -->|Sim| Q[POST /questionnaires/]
    Q --> R[POST /questionnaires/id/generate-link]
    R --> S[ui.notify Link gerado]
    S --> T[on_done → volta para lista]
```

---

## Fluxo 5: Resposta a Questionário (Respondente Público)

```mermaid
flowchart TD
    A[Acessa /questionnaire/encoded_id/respond] --> B[questionnaire_answer_page\nquestion_id str Base64]
    B --> C[QuestionnaireAnswerPage.render]
    C --> D[_render_loading]
    D --> E[_load_questionnaire\nGET /questionnaires/encoded_id/respond]
    E --> F[Backend decrypt_questionnaire_id]
    F --> G[Carrega items com ordenação]
    G --> H[QuestionnaireAnswerPage._render_questionnaire]
    H --> I{Para cada item}
    I -->|instruction| J[_render_instruction]
    I -->|term| K[_render_term\nHTML rico + opções]
    I -->|question| L[_render_question\nCaption + texto + tipo]
    L --> M{question_type}
    M -->|single| N[ui.radio]
    M -->|multiple| O[ui.checkbox para cada opção]
    M -->|free_text| P{_is_date_of_birth?}
    P -->|Sim| Q[_render_date_input\nmask ##/##/####]
    P -->|Não| R[ui.textarea max 1000 chars]
    R --> S[Usuário responde e clica Enviar]
    N --> S
    O --> S
    Q --> S
    S --> T[_validate_answers]
    T -->|Inválido| U[ui.notify warning]
    T -->|Válido| V[POST /responses/submit]
    V --> W[Backend valida + calcula scores + persiste]
    W --> X{success?}
    X -->|Sim| Y[_render_success ícone check verde]
    X -->|Não| Z[ui.notify negative com erro]
```

---

## Fluxo 6: Visualização de Relatório Detalhado

```mermaid
flowchart TD
    A[Usuário clica Relatório] --> B[QuestionnaireDetailedReport.render]
    B --> C[_load_data\nGET /analytics/questionnaires/id/dashboard-data]
    C --> D{Dados carregados}
    D -->|Erro| E[Card de erro]
    D -->|OK| F[_render_dashboard]
    F --> G[FilterSidebar.render]
    F --> H[_render_summary_section\nSummaryCards]
    F --> I[_render_questions_section\nPara cada distribuição: pie ou bar ou text_table]
    F --> J[_render_crosstab_section\nCrosstabTool]
    F --> K[_render_score_histogram\ncreate_histogram]
    F --> L[_render_subscale_section\nSubscaleSection + histogramas]
    F --> M[_render_reliability\nReliabilityCard]
    F --> N[_render_spearman_correlation\ncreate_correlation_heatmap]
    F --> O[_render_export_section\nExportButtons]
    P[Usuário aplica filtro] --> Q[_on_filter_apply]
    Q --> R[POST /analytics/filtered-analytics]
    R --> S[_refresh_dynamic_sections\nre-renderiza H K L M N]
```

---

## Fluxo 7: Exportação Personalizada

```mermaid
flowchart TD
    A[Usuário acessa Exportação Personalizada] --> B[CustomExportPage.render]
    B --> C[Passo 1: Escolhe modo\nrespostas ou questionários]
    C -->|respostas| D[Passo 2: Seleciona questionário]
    D --> E[_load_questions\nGET questionnaire/id/respond]
    E --> F[_extract_questions_from_structure]
    F --> G[Grupos: T=sociodemográfico Q=instrumento]
    G --> H[Passo 3: Metadados submission_id/submitted_at/total_score]
    H --> I[Passo 4+: Checkboxes de questões por grupo]
    I --> J[Filtros de data opcionais]
    J --> K[Passo formato: csv/xlsx/json]
    K --> L[Clica Exportar Dados]
    L --> M[POST /reports/questionnaires/id/custom-export]
    M --> N[Backend filtra por data + questões]
    N --> O[Retorna bytes CSV/XLSX/JSON]
    O --> P[ui.download filename]
    C -->|questionários| Q[Passo 2: Seleciona campos]
    Q --> R[Filtro de data local]
    R --> S[custom_export_service.to_csv/xlsx/json]
    S --> T[ui.download]
```
