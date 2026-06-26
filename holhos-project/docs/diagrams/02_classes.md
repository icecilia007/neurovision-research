# 02 — Diagrama de Classes

## Diagrama Mermaid

```mermaid
classDiagram

    %% ─── ORM Models ───────────────────────────────────────────────────

    class User {
        +int id
        +str full_name
        +GenderEnum gender
        +Date birth_date
        +EducationLevelEnum education_level
        +str email
        +str phone
        +str password_hash
    }

    class Questionnaire {
        +int id
        +str title
        +str description
        +QuestionOrderEnum question_order
        +bool is_active
        +DateTime created_at
        +int creator_id
        +User creator
        +List~QuestionnaireItem~ items
        +List~QuestionnaireSubmission~ submissions
    }

    class QuestionnaireItem {
        +int id
        +int questionnaire_id
        +ItemTypeEnum item_type
        +int item_id
        +int sort_order
        +Questionnaire questionnaire
    }

    class Question {
        +int id
        +str caption
        +str title
        +str text
        +QuestionTypeEnum question_type
        +bool is_required
        +float weight
        +DateTime created_at
        +List~QuestionOption~ options
        +List~Answer~ answers
    }

    class QuestionOption {
        +int id
        +int question_id
        +str text
        +int sort_order
        +bool is_correct
        +float weight
        +Question question
    }

    class Instruction {
        +int id
        +str text
        +DateTime created_at
    }

    class QuestionnaireSubmission {
        +int id
        +int questionnaire_id
        +float total_score
        +DateTime submitted_at
        +Questionnaire questionnaire
        +List~Answer~ answers
    }

    class Answer {
        +int id
        +int submission_id
        +int question_id
        +JSON selected_options
        +str text_response
        +float score
        +QuestionnaireSubmission submission
        +Question question
    }

    %% ─── Enums ────────────────────────────────────────────────────────

    class GenderEnum {
        <<enumeration>>
        masculino
        feminino
        outro
        nao_informar
    }

    class EducationLevelEnum {
        <<enumeration>>
        fundamental_incompleto
        fundamental_completo
        medio_incompleto
        medio_completo
        superior_incompleto
        superior_completo
        pos_graduacao
        mestrado
        doutorado
    }

    class QuestionTypeEnum {
        <<enumeration>>
        single
        multiple
        free_text
    }

    class QuestionOrderEnum {
        <<enumeration>>
        custom
        ascending
        descending
        random
    }

    class ItemTypeEnum {
        <<enumeration>>
        question
        instruction
        term
    }

    %% ─── ORM Relationships ────────────────────────────────────────────

    User "1" --> "N" Questionnaire : creator
    Questionnaire "1" --> "N" QuestionnaireItem : items
    Questionnaire "1" --> "N" QuestionnaireSubmission : submissions
    QuestionnaireSubmission "1" --> "N" Answer : answers
    Question "1" --> "N" QuestionOption : options
    Question "1" --> "N" Answer : answers
    User ..> GenderEnum : uses
    User ..> EducationLevelEnum : uses
    Question ..> QuestionTypeEnum : uses
    Questionnaire ..> QuestionOrderEnum : uses
    QuestionnaireItem ..> ItemTypeEnum : uses

    %% ─── Backend Services ─────────────────────────────────────────────

    class UserService {
        -CryptContext pwd_context
        +create_user(db, user_data) User
        +get_user_by_id(db, user_id) User
        +update_user(db, user_id, user_update) User
        +delete_user(db, user_id) bool
        +list_users(db, skip, limit) List~User~
        +login_user(db, email, senha) LoginResponse
        +get_user_by_email(db, email) Optional~User~
    }

    class QuestionnaireService {
        +create_instruction(db, instruction_data) Instruction
        +create_questionnaire(db, questionnaire_data) Questionnaire
        +generate_questionnaire_link(db, questionnaire_id) GenerateLinkResponse
        +get_questionnaire_for_response(db, questionnaire_id_param) QuestionnaireForResponse
        +list_questionnaires(db, skip, limit) List~Questionnaire~
        +list_questionnaires_by_creator(db, criador_id) List~Questionnaire~
        +get_questionnaire_by_id(db, questionnaire_id) Questionnaire
        +delete_questionnaire(db, questionnaire_id) bool
        +has_responses(db, questionnaire_id) bool
        +update_instruction(db, instruction_id, instruction_data) Instruction
        +update_questionnaire(db, questionnaire_id, questionnaire_data) Questionnaire
    }

    class QuestionService {
        +create_question(db, question_data) Question
        +get_question_by_id(db, question_id) Question
        +get_question_by_caption(db, caption) Question
        +add_option_to_question(db, question_id, option_data) QuestionOption
        +list_questions(db, skip, limit) List~Question~
        +delete_question(db, question_id) bool
        +update_question(db, question_id, question_data) Question
    }

    class ResponseService {
        +validate_submission(db, submission_data) SubmissionValidationResponse
        +_validate_answer_for_question_type(db, question, answer) Dict
        +calculate_answer_score(question, answer_data) float
        +submit_questionnaire_response(db, submission_data) QuestionnaireSubmission
        +get_submission_by_id(db, submission_id) QuestionnaireSubmission
        +delete_submission(db, submission_id) bool
        +list_submissions_by_questionnaire(db, questionnaire_id) List~QuestionnaireSubmission~
        +get_submission_statistics(db, questionnaire_id) Dict
        +get_answers_by_question(db, questionnaire_id, question_id) List~Answer~
    }

    class ReportService {
        +get_full_report(db, questionnaire_id) Dict
        +get_summary_report(db, questionnaire_id) Dict
        +custom_export(db, questionnaire_id, question_ids, meta_fields, date_from, date_to) Dict
        +get_question_analysis(db, questionnaire_id, question_id) Dict
    }

    class AnalyticsService {
        +compute_descriptive_stats(values) Dict
        +_re_score_answer(selected_options, question_options) float
        +compute_chyps_v_scores(submissions, caption_to_options) Dict
        +compute_cronbachs_alpha(item_matrix) float
        +compute_crosstab(row_values, col_values) Dict
        +filter_submissions(submissions, filters) List~Dict~
        +compute_question_distributions(question_stats) List~Dict~
    }

    %% ─── Frontend Services ────────────────────────────────────────────

    class APIClient {
        -str base_url
        -Session session
        +post(endpoint, data) Optional~Dict~
        +get(endpoint) Optional~Dict~
        +delete(endpoint) bool
        +put(endpoint, data) Optional~Dict~
        -_safe_user_message(status_code, default_msg) str
    }

    class SessionManager {
        +login(user) None
        +logout() None
        +current_user() Optional~Dict~
        +is_authenticated() bool
    }

    class Validators {
        +validate_email(email) Tuple~bool, str~
        +validate_password(password) Tuple~bool, str~
        +validate_age(age) Tuple~bool, str~
        +validate_phone(phone) Tuple~bool, str~
    }

    %% ─── Frontend Pages / Components (simplified) ────────────────────

    class QuestionnaireAnswerPage {
        -str questionnaire_id
        -dict questionnaire_data
        -dict answers
        -bool loading
        +render() None
        +_load_questionnaire() None
        +_render_questionnaire() None
        +_render_questionnaire_item(item) None
        +_render_single_choice(question_id, options) None
        +_render_multiple_choice(question_id, options) None
        +_render_text_input(question_id, question_text) None
        +_render_date_input(question_id, current_text) None
        +_render_term(term) None
        +_is_date_of_birth_field(question_text) bool
        +_validate_answers() Tuple~bool, str~
        +_on_submit() None
    }

    class QuestionItemEditor {
        -dict item_data
        -Callable on_remove
        -Callable on_change
        -bool _is_rendering
        -dict _option_ui_refs
        +render() None
        +_render_body() None
        +_render_options() None
        +_option_row(opt, visual_index) None
        +_add_option() None
        +_remove_option(opt) None
        +_sync_instruction(e) None
        +_sync_question_meta(e) None
        +_sync_term_meta(e) None
        +_sync_all_options_data() None
        +_on_question_type_change(e) None
        +_extract_editor_content(event) str
        +_notify_change() None
    }

    class QuestionnaireDetailedReport {
        -int questionnaire_id
        -dict report_data
        -dict analytics_data
        -list distributions
        -dict filter_options
        -list crosstab_variables
        -dict current_filters
        +render() None
        +_load_data(target) None
        +_render_dashboard() None
        +_render_summary_section() None
        +_render_score_histogram() None
        +_render_subscale_section() None
        +_render_reliability() None
        +_render_spearman_correlation() None
        +_render_questions_section() None
        +_render_question_card(dist) None
        +_render_birthday_card(dist) None
        +_render_observation_card(dist, question_text) None
        +_render_crosstab_section() None
        +_render_export_section() None
        +_on_filter_apply(filters) None
        +_on_filter_clear() None
        +_refresh_dynamic_sections() None
        +_on_crosstab_generate(row_var, col_var) None
        +_get_global_scores() List~float~
        +_get_text_responses_for_question(question_id) List~str~
    }

    class CustomExportPage {
        -Optional~str~ mode
        -list questionnaires
        -Optional~int~ selected_questionnaire_id
        -list questions_data
        -set selected_question_ids
        -set selected_meta_fields
        -str selected_format
        +render() None
        +_on_mode(mode) None
        +_flow_responses() None
        +_load_questions() None
        +_flow_questionnaires() None
        +_do_export() None
        +_export_responses() None
        +_export_questionnaires() None
        +_group_questions(questions) List
    }

    class SortableColumn {
        -Optional~Callable~ _on_change
        +_handle_drop(e) None
        +update_position(element_id, new_place) None
    }

    class AnalyticsServiceFE["AnalyticsService (frontend)"] {
        +get_dashboard_data(questionnaire_id) Optional~Dict~
        +get_filtered_analytics(questionnaire_id, filters) Optional~Dict~
        +get_chyps_scores(questionnaire_id, filters) Optional~Dict~
        +get_crosstab(questionnaire_id, row_variable, col_variable, filters) Optional~Dict~
        +get_question_distributions(questionnaire_id) Optional~Dict~
        +get_text_responses(questionnaire_id, question_id, ...) Optional~Dict~
        +get_filter_options(questionnaire_id) Optional~Dict~
        +get_crosstab_variables(questionnaire_id) Optional~Dict~
    }

    class CustomExportService {
        +to_csv(rows, columns) bytes
        +to_json(rows) bytes
        +to_xlsx(rows, columns, labels) bytes
    }

    %% ─── Config Classes ──────────────────────────────────────────────

    class Settings {
        +str database_url
        +str frontend_base_url
    }

    class Config {
        +str API_BASE_URL
        +str API_VERSION
        +str STORAGE_SECRET
        +api_url() str
    }

    %% ─── Analytics Schemas ───────────────────────────────────────────

    class FilterParams {
        +Optional~List~str~~ diagnosis
        +Optional~List~str~~ medication
        +Optional~Dict~str,int~~ birth_year
        +to_filter_dict() Dict
    }

    class CrosstabRequest {
        +str row_variable
        +str col_variable
        +Optional~FilterParams~ filters
    }

    class TextResponseQuery {
        +int question_id
        +Optional~str~ search
        +int page
        +int page_size
        +Optional~FilterParams~ filters
    }

    class CustomExportRequest {
        +List~int~ question_ids
        +List~str~ meta_fields
        +Optional~Date~ date_from
        +Optional~Date~ date_to
        +str format
    }

    %% ─── Frontend Page Classes ───────────────────────────────────────

    class AuthPage {
        +Optional~Callable~ on_login_success
        +Optional~Callable~ on_switch_to_signup
        +bool force_signup
        +render() None
    }

    class DashboardPage {
        +Optional~Callable~ on_logout
        +Optional content_container
        +render() None
        -_card(icon, title, subtitle, action) None
        -_go_list() None
        -_go_reports() None
        -_back_to_dashboard() None
        -_logout() None
    }

    class QuestionnaireListPage {
        +Optional~Callable~ on_back
        +Optional content_container
        +Optional grid_container
        +render() None
        -_load_my_questionnaires() None
        -_card(q) None
        -_on_ver_link(questionnaire_id) None
        -_on_copiar_link(questionnaire_id) None
        -_on_edit(questionnaire_id) None
        -_delete_questionnaire(questionnaire_id) None
        -_confirm_delete(dialog, questionnaire_id) None
        -_copy_to_clipboard(link, dialog) None
        -_modal_padrao(titulo, conteudo, botoes) dialog
        -_go_create() None
        -_back_to_list() None
    }

    class ReportsPage {
        +Optional~Callable~ on_back
        +Optional content_container
        +Optional grid_container
        +render() None
        -_load_reports() None
        -_render_questionnaire_card(questionnaire) None
        -_render_summary_metrics(questionnaire_id) None
        -_export_format(questionnaire_id, format_type) None
        -_view_full_report(questionnaire_id) None
        -_view_analytics(questionnaire_id) None
        -_go_custom_export() None
        -_back_to_reports() None
    }

    class QuestionnaireAnalyticsReport {
        +int questionnaire_id
        +Optional container
        +Optional~Callable~ on_back
        +render() None
        -_load_analytics(target) None
        -_render_analytics(analytics) None
    }

    %% ─── Auth Component Classes ──────────────────────────────────────

    class LoginForm {
        +Optional~Callable~ on_success_callback
        +Optional~Callable~ on_switch_to_signup
        +render() None
        -_on_login() None
    }

    class SignupForm {
        +Optional~Callable~ on_success_callback
        +Optional~Callable~ on_switch_to_login
        +render() None
        -_render_birth_date_field() None
        -_validate_birth_date_input(value) Optional~str~
        -_open_calendar() None
        -_on_calendar_select(e) None
        -_collect_form_data() None
        -_convert_birth_date_to_iso() Optional~str~
        -_validate_form() Tuple~bool,str~
        -_on_signup() None
    }

    class AuthModal {
        +Optional~Callable~ on_success_callback
        -Optional dialog
        -str current_form
        +show() None
        -_render_current_form() None
        -_switch_to_signup() None
        -_switch_to_login() None
        -_on_auth_success() None
        +close() None
    }

    %% ─── Dashboard Component Classes ─────────────────────────────────

    class SummaryCards {
        +int n_responses
        +dict global_stats
        +Optional~float~ cronbachs_alpha
        +render(container) None
        -_stat_card(value, label, gradient, icon) None
        -_alpha_interpretation(alpha) str
    }

    class PieChartCard {
        +str question_text
        +list labels
        +list counts
        +list percentages
        +render(container) None
    }

    class BarChartCard {
        +str question_text
        +list labels
        +list counts
        +list percentages
        +Optional~dict~ stats
        +render(container) None
    }

    class SubscaleSection {
        +dict subscale_stats
        +Optional~list~ respondent_scores
        +render(container) None
        -_render_subscale_histograms() None
    }

    class ReliabilityCard {
        +Optional~float~ alpha
        +int n_items
        +render(container) None
        -_interpret(alpha) Tuple~str,str~
    }

    class CrosstabTool {
        +list variables
        +Optional~Callable~ on_generate
        +render(container) None
        -_generate() None
        +render_result(result) None
        -_build_cell_colors(table_data) list
    }

    class FilterSidebar {
        +dict filter_options
        +Optional~Callable~ on_apply
        +Optional~Callable~ on_clear
        +render(container) None
        -_apply() None
        -_clear() None
    }

    class ExportButtons {
        +int questionnaire_id
        +render(container) None
        -_export_csv() None
        -_export_excel() None
    }

    class TextResponsesTable {
        +str question_text
        +list responses
        +int total
        +int page
        +int total_pages
        +Optional~Callable~ on_search
        +Optional~Callable~ on_page_change
        +render(container) None
    }

    %% ─── Questionnaire Component Classes ─────────────────────────────

    class QuestionComponent {
        +dict item_data
        +Optional~Callable~ on_update_callback
        +str uid
        +create_ui(parent_container) None
        -_on_text_change(e) None
        -_on_tipo_change(e) None
        -_on_peso_change(e) None
        -_update_options_display() None
        -_render_single_option(opt, visual_idx) None
        -_on_option_text_change(visual_idx, text) None
        -_on_option_order_change(visual_idx, order) None
        -_on_option_correct_change(visual_idx, is_correct) None
        -_on_option_weight_change(visual_idx, weight) None
        -_add_option() None
        -_remove_option(visual_idx) None
        +update_header_order(new_order) None
        +get_data() dict
        +set_data(new_data) None
    }
```

---

---

## Documentação das Classes Adicionadas

### `Settings` — `backend/app/config.py`
Configuração carregada via `pydantic-settings`. Detecta IP público automaticamente na inicialização para compor URLs de links de questionários.

| Atributo | Tipo | Padrão |
|---|---|---|
| `database_url` | `str` | `postgresql://postgres:password@localhost:5432/formularios_db` |
| `frontend_base_url` | `str` | resultado de `_get_public_ip()` ou `"localhost:8080"` |

---

### `Config` — `frontend/config.py`
Configuração do frontend lida de variáveis de ambiente. Provê a URL base da API.

| Atributo | Tipo | Padrão |
|---|---|---|
| `API_BASE_URL` | `str` | `"http://localhost:8000"` (via `API_BASE_URL` env var) |
| `API_VERSION` | `str` | `"v1"` |
| `STORAGE_SECRET` | `str` | `"questionnaire-app-secret-key-2024"` |
| `api_url` (property) | `str` | `f"{API_BASE_URL}/api/{API_VERSION}"` |

---

### Schemas Analytics — `backend/app/schemas/analytics.py`

#### `FilterParams`
Filtros demográficos para analytics. Campos opcionais.
- `diagnosis`: lista de strings de diagnóstico
- `medication`: lista de valores ("Sim"/"Não")
- `birth_year`: dict `{"min": int, "max": int}` para filtro por faixa de ano
- `to_filter_dict()`: converte para dict ignorando campos `None`

#### `CrosstabRequest`
Requisição de tabulação cruzada: variável linha, variável coluna, filtros opcionais.

#### `TextResponseQuery`
Query de respostas de texto livre com paginação (`page`, `page_size`) e busca textual opcional.

#### `CustomExportRequest`
Payload de exportação personalizada: IDs de questões, campos de metadados, filtro de datas, formato (csv/xlsx/json).

---

### `AuthPage` — `frontend/pages/auth_page.py`
Página de autenticação que renderiza `LoginForm` ou `SignupForm` dependendo de `force_signup`. Recebe callbacks para sucesso de login e troca de modo.

### `DashboardPage` — `frontend/pages/dashboard.py`
Dashboard pós-login com dois cards de navegação (Questionários, Relatórios). Usa `session_manager` para exibir o nome do usuário e `router.clear_and_render` para troca de página.

### `QuestionnaireListPage` — `frontend/pages/questionnaire_list_page.py`
Lista questionários do usuário autenticado via `questionnaire_service.list_by_creator`. Oferece ações: Ver Link, Copiar Link, Editar (com verificação de elegibilidade), Deletar (com confirmação). Usa JavaScript para acesso ao clipboard.

### `ReportsPage` — `frontend/pages/reports_page.py`
Lista questionários com cards de métricas resumidas (total respostas, média, máx, mín) carregadas via `report_service.get_summary_report`. Oferece download de relatório completo (CSV/JSON) e acesso ao relatório detalhado.

### `QuestionnaireAnalyticsReport` — `frontend/pages/report_analytics.py`
Analytics simplificados (distribuição de scores, top performers, perguntas difíceis) carregados via `report_service.get_analytics`.

---

### `LoginForm` — `frontend/components/auth/login_form.py`
Formulário de login com campos email e senha, validação via `Validators`, autenticação via `UserService.authenticate_user`, sessão via `SessionManager.login`.

### `SignupForm` — `frontend/components/auth/signup_form.py`
Formulário de cadastro com 7 campos obrigatórios (nome, email, senha, gênero, nascimento, escolaridade, telefone). Implementa datepicker via `ui.date` com validação de faixa etária (13-120 anos).

### `AuthModal` — `frontend/components/auth/auth_modal.py`
Modal de autenticação flutuante para respondentes que precisam autenticar antes de responder. Permite troca entre modos login/signup via `_switch_to_signup` / `_switch_to_login`.

---

### `SummaryCards` — `frontend/components/dashboard/summary_cards.py`
Cards de estatísticas globais (N respostas, média±DP, mediana±IIQ, Alpha de Cronbach quando disponível). Usa gradientes CSS. `_alpha_interpretation` classifica alpha em 5 níveis (Excelente/Boa/Aceitável/Questionável/Inaceitável).

### `PieChartCard` — `frontend/components/dashboard/pie_chart_card.py`
Card com gráfico pizza Plotly para questões com poucas opções. Usa `create_pie_chart` de `plotly_config`.

### `BarChartCard` — `frontend/components/dashboard/bar_chart_card.py`
Card com gráfico de barras Plotly e badges de estatísticas (média, DP, mediana, moda, IIQ). Usa `create_bar_chart` de `plotly_config`.

### `SubscaleSection` — `frontend/components/dashboard/subscale_section.py`
Seção de subescalas CHYPS-V com badges de stats por subescala e histogramas por subescala (quando há múltiplos respondentes). Usa `create_histogram`.

### `ReliabilityCard` — `frontend/components/dashboard/reliability_card.py`
Card de Alpha de Cronbach com valor numérico, badge interpretativo colorido e legenda de faixas. `_interpret` retorna tupla `(color_hex, label)`.

### `CrosstabTool` — `frontend/components/dashboard/crosstab_tool.py`
Ferramenta de tabulação cruzada interativa. Exibe tabela Plotly com heatmap de contagens/percentagens e testa independência via qui-quadrado (χ², valor-p, graus de liberdade). `_build_cell_colors` usa colorscale "Blues" normalizada.

### `FilterSidebar` — `frontend/components/dashboard/filter_sidebar.py`
Sidebar de filtros demográficos com checkboxes para diagnóstico e medicação, e range slider para ano de nascimento. `_apply` coleta filtros ativos e dispara `on_apply`. `_clear` reseta todos os controles.

### `ExportButtons` — `frontend/components/dashboard/export_buttons.py`
Botões de exportação rápida CSV e JSON (o botão "Excel" internamente chama format `json`). Delega ao `report_service.download_report`.

### `TextResponsesTable` — `frontend/components/dashboard/text_responses_table.py`
Tabela paginada de respostas de texto livre. Suporta busca por `keydown.enter`, paginação via callbacks `on_page_change`, truncamento de texto em 200 caracteres.

---

### `QuestionComponent` — `frontend/components/questionnaire/question_component.py`
Componente UI para edição de uma pergunta individual. Gerencia texto, tipo (single/multiple/free_text) e peso. Para tipos com opções, renderiza cards de opção com campos: texto, ordem, is_correct, peso. Usa flag `_updating_options` para evitar callbacks reentrantes. `on_update_callback` é chamado com eventos: `text_changed`, `tipo_changed`, `peso_changed`, `option_text_changed`, `option_order_changed`, `option_correct_changed`, `option_weight_changed`, `option_added`, `option_removed`.

---

## Instâncias Singleton (módulo-nível)

| Variável | Classe | Arquivo |
|---|---|---|
| `api_client` | `APIClient` | `frontend/services/api_client.py` |
| `session_manager` | `SessionManager` | `frontend/utils/session_manager.py` |
| `validators` | `Validators` | `frontend/utils/validators.py` |
| `questionnaire_service` | `QuestionnaireService` | `frontend/services/questionnaire_service.py` |
| `question_client` | `QuestionClient` | `frontend/services/question_service.py` |
| `instruction_client` | `InstructionClient` | `frontend/services/instruction_service.py` |
| `response_service` | `ResponseService` | `frontend/services/response_service.py` |
| `report_service` | `ReportService` | `frontend/services/report_service.py` |
| `analytics_service` | `AnalyticsService` | `frontend/services/analytics_service.py` |
| `custom_export_service` | `CustomExportService` | `frontend/services/custom_export_service.py` |
| `user_service` | `UserService` | `frontend/services/user_service.py` |
| `report_service` (backend) | `ReportService` | `backend/app/services/report_service.py` |
| `analytics_service` (backend) | `AnalyticsService` | `backend/app/services/analytics_service.py` |
| `settings` | `Settings` | `backend/app/config.py` |
| `config` | `Config` | `frontend/config.py` |
