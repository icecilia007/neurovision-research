# 07 — Diagramas de Sequência

## Sequência 1: Login de Usuário

```mermaid
sequenceDiagram
    actor U as Usuário
    participant LF as LoginForm
    participant SS as SessionManager
    participant USvc as UserService (FE)
    participant API as APIClient
    participant BE as Backend /users/login
    participant DB as PostgreSQL

    U->>LF: Preenche email + senha, clica Entrar
    LF->>LF: validators.validate_email(email)
    LF->>LF: validators.validate_password(senha)
    LF->>USvc: authenticate_user(email, senha)
    USvc->>API: post("/users/login", {email, senha})
    API->>BE: POST /api/v1/users/login
    BE->>DB: SELECT user WHERE email=?
    DB-->>BE: User ORM ou None
    alt Usuário não encontrado
        BE-->>API: 401 "Email ou senha incorretos"
        API-->>USvc: Exception
        USvc-->>LF: Exception
        LF->>U: error_label.text = mensagem
    else Usuário encontrado
        BE->>BE: pwd_context.verify(senha, hash)
        alt Senha inválida
            BE-->>API: 401 "Email ou senha incorretos"
        else Senha válida
            BE-->>API: 200 LoginResponse {success, user_id, nome_completo}
            API->>BE: GET /api/v1/users/{user_id}
            BE->>DB: SELECT user WHERE id=?
            DB-->>BE: User ORM
            BE-->>API: UserResponse
            API-->>USvc: user dict
            USvc-->>LF: user dict
            LF->>SS: session_manager.login(user)
            SS->>SS: app.storage.user["current_user"] = user
            LF->>U: ui.notify("Bem-vindo!")
            LF->>U: render_dashboard()
        end
    end
```

---

## Sequência 2: Criação de Questionário

```mermaid
sequenceDiagram
    actor U as Criador
    participant CP as CreatePage
    participant IEditor as QuestionItemEditor
    participant InstrSvc as InstructionClient
    participant QSvc as QuestionClient
    participant QNSvc as QuestionnaireService (FE)
    participant API as APIClient
    participant BE_QUEST as Backend /questionnaires
    participant BE_Q as Backend /questions
    participant DB as PostgreSQL

    U->>CP: Preenche título, adiciona itens
    CP->>IEditor: Cria editor por item
    U->>IEditor: Edita textos, opções, tipos
    IEditor->>CP: on_change(item_data) callbacks
    U->>CP: Clica Salvar
    CP->>CP: _sync_form_data()
    CP->>CP: _sync_all_editors_data()
    CP->>CP: _validate() — verifica título, textos, opções is_correct
    
    loop Para cada item (instrução)
        CP->>InstrSvc: create_instruction({texto})
        InstrSvc->>API: POST /questionnaires/instructions
        API->>BE_QUEST: POST /api/v1/questionnaires/instructions
        BE_QUEST->>DB: INSERT INTO instructions
        DB-->>BE_QUEST: Instruction {id}
        BE_QUEST-->>API: InstructionResponse
        API-->>CP: {id: ...}
    end
    
    loop Para cada item (pergunta/termo)
        CP->>QSvc: create_question(payload)
        QSvc->>API: POST /questions/
        API->>BE_Q: POST /api/v1/questions/
        BE_Q->>DB: INSERT INTO questions\nINSERT INTO question_options
        DB-->>BE_Q: Question {id}
        BE_Q-->>API: QuestionResponse
        API-->>CP: {id: ...}
    end
    
    CP->>QNSvc: create_questionnaire({título, items, criador_id})
    QNSvc->>API: POST /questionnaires/
    API->>BE_QUEST: POST /api/v1/questionnaires/
    BE_QUEST->>DB: INSERT INTO questionnaires\nINSERT INTO questionnaire_items
    DB-->>BE_QUEST: Questionnaire {id}
    BE_QUEST-->>API: QuestionnaireResponse
    
    CP->>QNSvc: generate_link(questionnaire_id)
    QNSvc->>API: POST /questionnaires/id/generate-link
    API->>BE_QUEST: POST .../generate-link
    BE_QUEST->>BE_QUEST: encrypt_questionnaire_id(id)
    BE_QUEST-->>API: GenerateLinkResponse {link}
    API-->>CP: {link: "https://IP/questionnaire/BASE64/respond"}
    CP->>U: ui.notify("Questionário criado! Link: ...")
    CP->>U: on_done() → volta para lista
```

---

## Sequência 3: Resposta a Questionário

```mermaid
sequenceDiagram
    actor R as Respondente
    participant Browser as Browser
    participant NGINX as nginx:8080
    participant FE as Frontend
    participant AP as QuestionnaireAnswerPage
    participant QSvcFE as QuestionnaireService (FE)
    participant RespSvcFE as ResponseService (FE)
    participant API as APIClient
    participant BE_QUEST as Backend /questionnaires
    participant BE_RESP as Backend /responses
    participant BE_RespSvc as ResponseService (BE)
    participant DB as PostgreSQL

    R->>Browser: Acessa https://IP/questionnaire/BASE64/respond
    Browser->>NGINX: GET /questionnaire/BASE64/respond
    NGINX->>FE: Proxy para frontend:8080
    FE->>AP: questionnaire_answer_page(questionnaire_id=BASE64)
    AP->>AP: _render_loading()
    AP->>QSvcFE: get_questionnaire_for_response(BASE64)
    QSvcFE->>API: GET /questionnaires/BASE64/respond
    API->>BE_QUEST: GET /api/v1/questionnaires/BASE64/respond
    BE_QUEST->>BE_QUEST: decrypt_questionnaire_id(BASE64)
    BE_QUEST->>DB: SELECT questionnaire, items, questions, options
    DB-->>BE_QUEST: Dados do questionário
    BE_QUEST->>BE_QUEST: Aplica ordenação (custom/random)
    BE_QUEST-->>API: QuestionnaireForResponse
    API-->>AP: Dict com titulo, items
    AP->>AP: _render_questionnaire() com todos os itens
    AP->>R: Exibe formulário completo

    R->>R: Responde questões (radio/checkbox/textarea)
    R->>AP: Clica Enviar Respostas
    AP->>AP: _validate_answers() — verifica obrigatórias
    AP->>RespSvcFE: submit_response({questionnaire_id, answers})
    RespSvcFE->>API: POST /responses/submit
    API->>BE_RESP: POST /api/v1/responses/submit
    BE_RESP->>BE_RespSvc: validate_submission(submission_data)
    BE_RespSvc->>DB: Verifica questões, opções, obrigatórias
    DB-->>BE_RespSvc: Dados de validação
    
    alt Validação falhou
        BE_RespSvc-->>BE_RESP: SubmissionValidationResponse {is_valid=False}
        BE_RESP-->>API: 400 {errors, missing_questions}
        API-->>AP: Response dict
        AP->>R: ui.notify(primeiro erro)
    else Validação OK
        BE_RESP->>BE_RespSvc: submit_questionnaire_response(submission_data)
        BE_RespSvc->>DB: INSERT questionnaire_submissions
        loop Para cada answer
            BE_RespSvc->>BE_RespSvc: calculate_answer_score()
            BE_RespSvc->>DB: INSERT answers
        end
        BE_RespSvc->>DB: UPDATE submissions.total_score
        DB-->>BE_RespSvc: Submission persistida
        BE_RespSvc-->>BE_RESP: QuestionnaireSubmission
        BE_RESP-->>API: 200 {success=True, id, total_score}
        API-->>AP: Response dict
        AP->>AP: _render_success()
        AP->>R: Ícone check + "Respostas Enviadas com Sucesso!"
    end
```

---

## Sequência 4: Visualização do Dashboard Analítico

```mermaid
sequenceDiagram
    actor U as Usuário/Pesquisador
    participant DR as QuestionnaireDetailedReport
    participant AnalSvc as AnalyticsService (FE)
    participant API as APIClient
    participant BE_ANA as Backend /analytics
    participant BE_RPT as ReportService (BE)
    participant BE_ASVC as AnalyticsService (BE)
    participant DB as PostgreSQL

    U->>DR: Clica Relatório (questionnaire_id)
    DR->>DR: _load_data()
    DR->>AnalSvc: get_dashboard_data(questionnaire_id)
    AnalSvc->>API: GET /analytics/questionnaires/id/dashboard-data
    API->>BE_ANA: GET /api/v1/analytics/.../dashboard-data
    BE_ANA->>BE_RPT: get_full_report(db, questionnaire_id)
    BE_RPT->>DB: SELECT questionnaire + submissions + answers + questions + options
    DB-->>BE_RPT: Dados completos
    BE_RPT-->>BE_ANA: report_data dict

    BE_ANA->>BE_ASVC: compute_chyps_v_scores(submissions, caption_options)
    BE_ASVC->>BE_ASVC: Para Q1-Q20: _re_score_answer()
    BE_ASVC->>BE_ASVC: compute_cronbachs_alpha(matrix_N_20)
    BE_ASVC->>BE_ASVC: scipy.spearmanr(matrix)
    BE_ASVC-->>BE_ANA: {global_stats, subscale_stats, alpha, spearman}

    BE_ANA->>BE_ASVC: compute_question_distributions(question_stats)
    BE_ASVC-->>BE_ANA: distributions list

    BE_ANA-->>API: dashboard_data {questionnaire, general_stats, analytics, distributions, filter_options, crosstab_variables, anonymous_submissions}
    API-->>DR: Dict completo
    
    DR->>DR: _render_dashboard()
    DR->>DR: SummaryCards(n, global_stats, alpha)
    DR->>DR: Para cada distribution: PieChartCard ou BarChartCard
    DR->>DR: CrosstabTool(variables)
    DR->>DR: create_histogram(global_scores)
    DR->>DR: SubscaleSection(subscale_stats, respondent_scores)
    DR->>DR: ReliabilityCard(alpha)
    DR->>DR: create_correlation_heatmap(spearman_matrix)
    DR->>DR: ExportButtons(questionnaire_id)
    DR->>U: Dashboard completo renderizado

    opt Usuário aplica filtro demográfico
        U->>DR: FilterSidebar → _on_filter_apply(filters)
        DR->>AnalSvc: get_filtered_analytics(questionnaire_id, filters)
        AnalSvc->>API: POST /analytics/.../filtered-analytics
        API->>BE_ANA: POST ...
        BE_ANA->>BE_ASVC: filter_submissions(submissions, filters)
        BE_ASVC->>BE_ASVC: _matches_categorical / _matches_year
        BE_ASVC-->>BE_ANA: Submissões filtradas
        BE_ANA->>BE_ASVC: compute_chyps_v_scores(filtered, ...)
        BE_ASVC-->>BE_ANA: Scores filtrados
        BE_ANA-->>API: {global_stats, subscale_stats, alpha, spearman}
        API-->>DR: Analytics filtrados
        DR->>DR: _refresh_dynamic_sections() — re-renderiza seções analíticas
        DR->>U: Dashboard atualizado
    end
```
