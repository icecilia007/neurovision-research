# 10 — Matriz de Rastreabilidade

## Função → Classe → Módulo → Pipeline → Arquivo

### Backend

| Função | Classe | Módulo | Pipeline/Fluxo | Arquivo |
|---|---|---|---|---|
| `get_db` | — | database | Toda requisição com DB | `backend/app/database.py` |
| `_get_public_ip` | — | config | Startup do backend | `backend/app/config.py` |
| `encrypt_questionnaire_id` | — | crypto | Gerar link de questionário | `backend/app/utils/crypto.py` |
| `decrypt_questionnaire_id` | — | crypto | Carregar questionário para resposta | `backend/app/utils/crypto.py` |
| `_normalize_encoded_id` | — | crypto | Normalização de ID Base64 recebido de URL | `backend/app/utils/crypto.py` |
| `is_encrypted_id` | — | crypto | Validação de ID | `backend/app/utils/crypto.py` |
| `create_user` | `UserService` | user_service | Cadastro de usuário | `backend/app/services/user_service.py` |
| `login_user` | `UserService` | user_service | Autenticação | `backend/app/services/user_service.py` |
| `get_user_by_id` | `UserService` | user_service | Obter perfil do usuário | `backend/app/services/user_service.py` |
| `update_user` | `UserService` | user_service | Editar perfil | `backend/app/services/user_service.py` |
| `delete_user` | `UserService` | user_service | Remover usuário | `backend/app/services/user_service.py` |
| `list_users` | `UserService` | user_service | Administração | `backend/app/services/user_service.py` |
| `create_questionnaire` | `QuestionnaireService` | questionnaire_service | Criar questionário | `backend/app/services/questionnaire_service.py` |
| `update_questionnaire` | `QuestionnaireService` | questionnaire_service | Editar questionário | `backend/app/services/questionnaire_service.py` |
| `delete_questionnaire` | `QuestionnaireService` | questionnaire_service | Remover questionário | `backend/app/services/questionnaire_service.py` |
| `generate_questionnaire_link` | `QuestionnaireService` | questionnaire_service | Gerar link público | `backend/app/services/questionnaire_service.py` |
| `get_questionnaire_for_response` | `QuestionnaireService` | questionnaire_service | Exibir questionário ao respondente | `backend/app/services/questionnaire_service.py` |
| `list_questionnaires_by_creator` | `QuestionnaireService` | questionnaire_service | Lista de questionários do usuário | `backend/app/services/questionnaire_service.py` |
| `has_responses` | `QuestionnaireService` | questionnaire_service | Verificar elegibilidade para edição | `backend/app/services/questionnaire_service.py` |
| `create_instruction` | `QuestionnaireService` | questionnaire_service | Adicionar instrução | `backend/app/services/questionnaire_service.py` |
| `update_instruction` | `QuestionnaireService` | questionnaire_service | Editar instrução | `backend/app/services/questionnaire_service.py` |
| `create_question` | `QuestionService` | question_service | Criar pergunta | `backend/app/services/question_service.py` |
| `add_option_to_question` | `QuestionService` | question_service | Adicionar opção a pergunta existente | `backend/app/services/question_service.py` |
| `list_questions` | `QuestionService` | question_service | Listar todas as perguntas | `backend/app/services/question_service.py` |
| `update_question` | `QuestionService` | question_service | Editar pergunta | `backend/app/services/question_service.py` |
| `delete_question` | `QuestionService` | question_service | Remover pergunta | `backend/app/services/question_service.py` |
| `get_question_by_caption` | `QuestionService` | question_service | Busca por código | `backend/app/services/question_service.py` |
| `validate_submission` | `ResponseService` | response_service | Validar resposta antes de persistir | `backend/app/services/response_service.py` |
| `calculate_answer_score` | `ResponseService` | response_service | Calcular pontuação | `backend/app/services/response_service.py` |
| `submit_questionnaire_response` | `ResponseService` | response_service | Persistir resposta | `backend/app/services/response_service.py` |
| `get_submission_by_id` | `ResponseService` | response_service | Buscar submissão por ID | `backend/app/services/response_service.py` |
| `delete_submission` | `ResponseService` | response_service | Remover submissão | `backend/app/services/response_service.py` |
| `get_answers_by_question` | `ResponseService` | response_service | Respostas de uma questão num questionário | `backend/app/services/response_service.py` |
| `list_submissions_by_questionnaire` | `ResponseService` | response_service | Listar respostas | `backend/app/services/response_service.py` |
| `get_submission_statistics` | `ResponseService` | response_service | Stats rápidas de submissão | `backend/app/services/response_service.py` |
| `get_full_report` | `ReportService` | report_service | Relatório completo | `backend/app/services/report_service.py` |
| `get_summary_report` | `ReportService` | report_service | Resumo numérico | `backend/app/services/report_service.py` |
| `custom_export` | `ReportService` | report_service | Exportação personalizada | `backend/app/services/report_service.py` |
| `get_question_analysis` | `ReportService` | report_service | Análise por questão | `backend/app/services/report_service.py` |
| `compute_descriptive_stats` | `AnalyticsService` | analytics_service | Base de todos os stats | `backend/app/services/analytics_service.py` |
| `compute_chyps_v_scores` | `AnalyticsService` | analytics_service | Pipeline CHYPS-V | `backend/app/services/analytics_service.py` |
| `compute_cronbachs_alpha` | `AnalyticsService` | analytics_service | Confiabilidade da escala | `backend/app/services/analytics_service.py` |
| `compute_crosstab` | `AnalyticsService` | analytics_service | Tabulação cruzada | `backend/app/services/analytics_service.py` |
| `filter_submissions` | `AnalyticsService` | analytics_service | Filtros demográficos | `backend/app/services/analytics_service.py` |
| `compute_question_distributions` | `AnalyticsService` | analytics_service | Gráficos de distribuição | `backend/app/services/analytics_service.py` |
| `_re_score_answer` | `AnalyticsService` | analytics_service | Re-scoring por pesos | `backend/app/services/analytics_service.py` |
| `_nan_to_none` | — | analytics_service | Serialização JSON segura | `backend/app/services/analytics_service.py` |
| `_find_caption_by_pattern` | — | analytics_service | Matching demográfico | `backend/app/services/analytics_service.py` |
| `_matches_year` | — | analytics_service | Filtro por ano | `backend/app/services/analytics_service.py` |
| `_matches_categorical` | — | analytics_service | Filtro categórico | `backend/app/services/analytics_service.py` |
| `_option_counts_to_scores` | — | analytics_service | Scores para stats Likert | `backend/app/services/analytics_service.py` |
| `slugify` | — | reports endpoint | Nomes de colunas CSV | `backend/app/api/v1/endpoints/reports.py` |
| `_build_caption_option_map` | — | analytics endpoint | Mapa caption→opções para CHYPS | `backend/app/api/v1/endpoints/analytics.py` |
| `_extract_variable_values` | — | analytics endpoint | Extração de variáveis para crosstab | `backend/app/api/v1/endpoints/analytics.py` |
| `_compute_filter_options` | — | analytics endpoint | Opções disponíveis para filtros | `backend/app/api/v1/endpoints/analytics.py` |
| `_get_crosstab_variables` | — | analytics endpoint | Variáveis disponíveis para crosstab | `backend/app/api/v1/endpoints/analytics.py` |

---

### Frontend

| Função | Classe | Módulo | Pipeline/Fluxo | Arquivo |
|---|---|---|---|---|
| `render_login` / `render_signup` / `render_dashboard` | — | app | Navegação raiz | `frontend/app.py` |
| `render_signup` | `SignupForm` | signup_form | Cadastro de novo usuário | `frontend/components/auth/signup_form.py` |
| `clear_and_render` | — | router | Troca de páginas sem reload | `frontend/router.py` |
| `respond_questionnaire_page` | — | router | Rota pública de resposta | `frontend/router.py` |
| `login` / `logout` / `is_authenticated` | `SessionManager` | session_manager | Toda navegação autenticada | `frontend/utils/session_manager.py` |
| `validate_email` / `validate_password` / `validate_age` / `validate_phone` | `Validators` | validators | Forms de auth e cadastro | `frontend/utils/validators.py` |
| `post` / `get` / `put` / `delete` | `APIClient` | api_client | Toda comunicação com backend | `frontend/services/api_client.py` |
| `authenticate_user` | `UserService` | user_service | Login | `frontend/services/user_service.py` |
| `create_user` | `UserService` | user_service | Cadastro | `frontend/services/user_service.py` |
| `create_questionnaire` / `update_questionnaire` / `delete` | `QuestionnaireService` | questionnaire_service | CRUD questionários | `frontend/services/questionnaire_service.py` |
| `generate_link` / `check_eligibility` | `QuestionnaireService` | questionnaire_service | Gestão de links e edição | `frontend/services/questionnaire_service.py` |
| `get_questionnaire_for_response` | `QuestionnaireService` | questionnaire_service | Resposta + Editor + Exportação | `frontend/services/questionnaire_service.py` |
| `list_by_creator` | `QuestionnaireService` | questionnaire_service | Listas de questionários | `frontend/services/questionnaire_service.py` |
| `submit_response` | `ResponseService` | response_service | Submissão de resposta | `frontend/services/response_service.py` |
| `get_full_report` / `get_summary_report` / `get_analytics` | `ReportService` | report_service | Relatórios | `frontend/services/report_service.py` |
| `download_report` | `ReportService` | report_service | Download CSV/JSON | `frontend/services/report_service.py` |
| `download_csv_report` | `ReportService` | report_service | Atalho download CSV | `frontend/services/report_service.py` |
| `download_json_report` | `ReportService` | report_service | Atalho download JSON | `frontend/services/report_service.py` |
| `custom_export` | `ReportService` | report_service | Exportação personalizada | `frontend/services/report_service.py` |
| `get_dashboard_data` | `AnalyticsService` | analytics_service | Dashboard analítico | `frontend/services/analytics_service.py` |
| `get_filtered_analytics` | `AnalyticsService` | analytics_service | Filtros demográficos | `frontend/services/analytics_service.py` |
| `get_crosstab` | `AnalyticsService` | analytics_service | Tabulação cruzada | `frontend/services/analytics_service.py` |
| `to_csv` / `to_json` / `to_xlsx` | `CustomExportService` | custom_export_service | Exportação local de questionários | `frontend/services/custom_export_service.py` |
| `render` | `LoginForm` | login_form | Login | `frontend/components/auth/login_form.py` |
| `render` / `_validate_form` | `SignupForm` | signup_form | Cadastro | `frontend/components/auth/signup_form.py` |
| `show` / `_on_auth_success` | `AuthModal` | auth_modal | Auth modal para respondentes | `frontend/components/auth/auth_modal.py` |
| `render` / `_render_body` / `_render_options` | `QuestionItemEditor` | question_item_editor | Editor de questionários | `frontend/components/questionnaire/question_item_editor.py` |
| `_sync_question_meta` / `_sync_term_meta` / `_sync_instruction` | `QuestionItemEditor` | question_item_editor | Sincronização de dados | `frontend/components/questionnaire/question_item_editor.py` |
| `_handle_drop` / `update_position` | `SortableColumn` | sortable_column | Drag-and-drop | `frontend/components/questionnaire/sortable_column.py` |
| `render` | `SummaryCards` | summary_cards | Summary do relatório | `frontend/components/dashboard/summary_cards.py` |
| `render` | `PieChartCard` | pie_chart_card | Gráficos pie | `frontend/components/dashboard/pie_chart_card.py` |
| `render` | `BarChartCard` | bar_chart_card | Gráficos bar | `frontend/components/dashboard/bar_chart_card.py` |
| `render` / `_render_subscale_histograms` | `SubscaleSection` | subscale_section | Subescalas CHYPS-V | `frontend/components/dashboard/subscale_section.py` |
| `render` | `ReliabilityCard` | reliability_card | Alpha de Cronbach | `frontend/components/dashboard/reliability_card.py` |
| `render` / `render_result` / `_generate` | `CrosstabTool` | crosstab_tool | Tabulação cruzada | `frontend/components/dashboard/crosstab_tool.py` |
| `render` / `_apply` / `_clear` | `FilterSidebar` | filter_sidebar | Filtros demográficos | `frontend/components/dashboard/filter_sidebar.py` |
| `_export_csv` / `_export_excel` | `ExportButtons` | export_buttons | Exportação rápida | `frontend/components/dashboard/export_buttons.py` |
| `create_pie_chart` / `create_bar_chart` / `create_histogram` / `create_correlation_heatmap` | — | plotly_config | Todos os gráficos | `frontend/components/shared/plotly_config.py` |
| `questionnaire_create_page` | — | questionnaire_create_page | Criar/Editar questionário | `frontend/pages/questionnaire_create_page.py` |
| `questionnaire_answer_page` | — | questionnaire_answer_page | Responder questionário | `frontend/pages/questionnaire_answer_page.py` |
| `_render_dashboard` / `_refresh_dynamic_sections` | `QuestionnaireDetailedReport` | report_detailed | Relatório analítico | `frontend/pages/report_detailed.py` |
| `_do_export` / `_export_responses` / `_export_questionnaires` | `CustomExportPage` | custom_export_page | Exportação personalizada | `frontend/pages/custom_export_page.py` |

---

## Rastreabilidade de Endpoints → Serviços → Tabelas

| Endpoint | Service | Tabelas Tocadas |
|---|---|---|
| POST /users/ | UserService.create_user | users |
| POST /users/login | UserService.login_user | users |
| GET /users/{id} | UserService.get_user_by_id | users |
| POST /questions/ | QuestionService.create_question | questions, question_options |
| PUT /questions/{id} | QuestionService.update_question | questions, question_options |
| DELETE /questions/{id} | QuestionService.delete_question | questions |
| POST /questionnaires/instructions | QuestionnaireService.create_instruction | instructions |
| PUT /questionnaires/instructions/{id} | QuestionnaireService.update_instruction | instructions |
| POST /questionnaires/ | QuestionnaireService.create_questionnaire | questionnaires, questionnaire_items |
| PUT /questionnaires/{id} | QuestionnaireService.update_questionnaire | questionnaires, questionnaire_items |
| DELETE /questionnaires/{id} | QuestionnaireService.delete_questionnaire | answers, questionnaire_submissions, question_options, questions, instructions, questionnaire_items, questionnaires |
| GET /questionnaires/{id}/respond | QuestionnaireService.get_questionnaire_for_response | questionnaires, questionnaire_items, questions, question_options, instructions |
| POST /questionnaires/{id}/generate-link | QuestionnaireService.generate_questionnaire_link | questionnaires |
| POST /responses/submit | ResponseService.validate_submission + submit_questionnaire_response | questionnaire_submissions, answers |
| GET /reports/.../full-report | ReportService.get_full_report | questionnaires, questionnaire_submissions, answers, questions, question_options, questionnaire_items |
| GET /reports/.../summary | ReportService.get_summary_report | questionnaire_submissions |
| GET /reports/.../export | ReportService.get_full_report | (mesmas do full-report) |
| GET /reports/.../analytics | `get_analytics` (endpoint handler) + ReportService.get_full_report | questionnaires, questionnaire_submissions, answers, questions, question_options, questionnaire_items |
| GET /questions/ | QuestionService.list_questions | questions |
| POST /questions/{id}/options | QuestionService.add_option_to_question | question_options |
| GET /responses/submissions/{id} | ResponseService.get_submission_by_id | questionnaire_submissions |
| DELETE /responses/submissions/{id} | ResponseService.delete_submission | questionnaire_submissions, answers |
| GET /responses/questionnaires/{id}/submissions | ResponseService.list_submissions_by_questionnaire | questionnaire_submissions |
| GET /responses/questionnaires/{id}/statistics | ResponseService.get_submission_statistics | questionnaire_submissions |
| GET /users/ | UserService.list_users | users |
| PUT /users/{id} | UserService.update_user | users |
| DELETE /users/{id} | UserService.delete_user | users |
| GET /questionnaires/ | QuestionnaireService.list_questionnaires / list_questionnaires_by_creator | questionnaires |
| GET /questionnaires/{id} | QuestionnaireService.get_questionnaire_by_id | questionnaires |
| GET /questions/{id} | QuestionService.get_question_by_id | questions, question_options |
| GET /questions/by-caption/{caption} | QuestionService.get_question_by_caption | questions, question_options |
| POST /reports/.../custom-export | ReportService.custom_export | questionnaire_submissions, answers, questions, question_options, questionnaire_items |
| GET /analytics/.../dashboard-data | ReportService.get_full_report + AnalyticsService.* | (mesmas do full-report) |
| POST /analytics/.../filtered-analytics | ReportService.get_full_report + AnalyticsService.filter_submissions + compute_chyps_v_scores | (mesmas do full-report) |
| POST /analytics/.../crosstab | ReportService.get_full_report + AnalyticsService.compute_crosstab | (mesmas do full-report) |
| POST /analytics/.../chyps-scores | ReportService.get_full_report + AnalyticsService.compute_chyps_v_scores | (mesmas do full-report) |
