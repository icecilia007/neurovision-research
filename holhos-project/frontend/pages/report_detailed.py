from nicegui import ui
from services.report_service import report_service
from services.analytics_service import analytics_service
from components.shared.plotly_config import create_histogram, create_correlation_heatmap, create_pie_chart, create_bar_chart, create_bar_chart_h
from components.dashboard.summary_cards import SummaryCards
from components.dashboard.subscale_section import SubscaleSection
from components.dashboard.crosstab_tool import CrosstabTool
from components.dashboard.reliability_card import ReliabilityCard
from components.dashboard.export_buttons import ExportButtons
from components.dashboard.filter_sidebar import FilterSidebar
import re
from html import escape, unescape

EXCLUDED_PATTERNS = [
    "TCLE",
    "TERMO DE CONSENTIMENTO",
    "consentimento",
]

EXCLUDED_EXACT = [
    "Nome",
    "Email",
]

# T5: Only match the definition question, Race/Ethnicity, Sex — NOT Q1-Q20
PIE_CHART_PATTERNS = [
    "indique o que queremos dizer",
    "Raça",
    "Raca",
    "Etnia",
    "Sexo",
]

BIRTHDAY_PATTERN = "data de nascimento"
OBSERVATION_PATTERNS = ["observação", "observacao", "obs:"]
DISCOMFORT_DEFINITION_PATTERN = "indique o que queremos dizer"


def _passthrough_html(value: str) -> str:
    return value


def _matches_patterns(text: str, patterns: list) -> bool:
    lower = text.lower()
    return any(p.lower() in lower for p in patterns)


def _is_excluded(question_text: str, question_title: str) -> bool:
    combined = f"{question_text or ''} {question_title or ''}"
    for exact in EXCLUDED_EXACT:
        if exact.lower() == combined.strip().lower():
            return True
    return _matches_patterns(combined, EXCLUDED_PATTERNS)


def _force_pie(question_text: str) -> bool:
    return _matches_patterns(question_text or "", PIE_CHART_PATTERNS)


def _is_birthday(question_text: str) -> bool:
    return BIRTHDAY_PATTERN in (question_text or "").lower()


def _is_observation(question_text: str) -> bool:
    lower = (question_text or "").lower()
    return any(p in lower for p in OBSERVATION_PATTERNS)


def _is_discomfort_definition(question_text: str) -> bool:
    return DISCOMFORT_DEFINITION_PATTERN in (question_text or "").lower()


def _truncate_discomfort_labels(labels: list) -> list:
    result = []
    for i, label in enumerate(labels):
        if i == 3 and len(label) > 15:
            comma_pos = label.find(",")
            if comma_pos > 0:
                result.append(label[:comma_pos] + ", ...")
            else:
                result.append(label[:15] + "...")
        else:
            result.append(label)
    return result


class QuestionnaireDetailedReport:
    def __init__(self, questionnaire_id, container=None, on_back=None):
        self.questionnaire_id = questionnaire_id
        self.container = container
        self.on_back = on_back
        self.report_data = None
        self.analytics_data = None
        self.distributions = None
        self.filter_options = {}
        self.crosstab_variables = []
        self.validity_questions = []
        self.current_filters = {}

        # Dynamic containers
        self.summary_container = None
        self.questions_container = None
        self.crosstab_container = None
        self.score_hist_container = None
        self.subscale_container = None
        self.reliability_container = None
        self.spearman_container = None
        self.export_container = None
        self.crosstab_tool = None
        self.filter_sidebar = None

    def render(self):
        ui.add_head_html('''
        <style>
            .report-richtext p { margin: 0.35rem 0; }
            .report-richtext ul, .report-richtext ol {
                margin: 0.35rem 0;
                padding-left: 1.25rem;
                list-style-position: outside;
                list-style: initial !important;
            }
            .report-richtext ul { list-style-type: disc !important; }
            .report-richtext ol { list-style-type: decimal !important; }
            .report-richtext li {
                margin: 0.2rem 0;
                display: list-item !important;
            }
            .report-richtext li::marker { color: #4b5563 !important; }
            @media (max-width: 900px) {
                .dashboard-grid {
                    flex-direction: column !important;
                }
                .dashboard-grid > div:first-child {
                    width: 100% !important;
                    max-width: 100% !important;
                    flex: none !important;
                }
            }
            /* Quasar q-checkbox labels: allow wrapping inside the narrow sidebar */
            .validity-opts .q-checkbox {
                max-width: 100%;
            }
            .validity-opts .q-checkbox__label {
                white-space: normal !important;
                word-break: break-word;
                line-height: 1.3;
                min-width: 0;
            }
        </style>
        <script>
        window.addEventListener('load', function() {
            setTimeout(function() {
                document.querySelectorAll('.js-plotly-plot').forEach(function(el) {
                    if (window.Plotly) { window.Plotly.Plots.resize(el); }
                });
            }, 400);
        });
        </script>
        ''')

        target = self.container or ui.column().style('width: 100%;')
        with target:
            with ui.row().style('width: 100%; justify-content: space-between; align-items: center;'):
                ui.label('Relatório Detalhado').style(
                    'font-size: 1.4rem; font-weight: 700; color: #111827;')
                ui.button('Voltar', on_click=self.on_back).props('outline')

            self._load_data(target)

    # ── Data Loading ───────────────────────────────────────────────────

    def _load_data(self, target):
        loading = ui.column().style('width: 100%;')
        with loading:
            with ui.row().style('justify-content: center; margin: 2rem;'):
                ui.spinner(size='2rem', color='primary')
                ui.label('Carregando relatório...').style('margin-left: 1rem;')

        try:
            dashboard_data = analytics_service.get_dashboard_data(self.questionnaire_id)

            self.report_data = {
                "questionnaire": dashboard_data.get("questionnaire", {}),
                "general_stats": dashboard_data.get("general_stats", {}),
                "anonymous_submissions": dashboard_data.get("anonymous_submissions", []),
            }
            self.analytics_data = dashboard_data.get("analytics", {})
            self.distributions = dashboard_data.get("distributions", [])
            self.filter_options = dashboard_data.get("filter_options", {})
            self.crosstab_variables = dashboard_data.get("crosstab_variables", [])

            try:
                vq_data = analytics_service.get_validity_questions(self.questionnaire_id)
                self.validity_questions = vq_data.get("questions", []) if vq_data else []
            except Exception:
                self.validity_questions = []

            loading.clear()
            with target:
                self._render_dashboard()
        except Exception as e:
            loading.clear()
            with target:
                with ui.card().style('padding: 2rem; text-align: center;'):
                    ui.icon('error', size='3rem', color='negative')
                    ui.label(f'Erro ao carregar relatório: {str(e)}').style('color: #b91c1c;')

    # ── Dashboard Rendering ────────────────────────────────────────────
    # T10: Order = Summary → Questions → Crosstab → ScoreHist → Subscale → Reliability → Spearman → Export

    def _render_dashboard(self):
        questionnaire = self.report_data.get('questionnaire', {})

        with ui.card().style('width: 100%; padding: 1.5rem; margin-bottom: 1rem;'):
            ui.label(questionnaire.get('title', '')).style(
                'font-size: 1.5rem; font-weight: 700; color: #111827;')
            if questionnaire.get('description'):
                ui.label(questionnaire.get('description')).style(
                    'color: #6b7280; margin-top: 0.5rem;')

        with ui.element('div').classes('dashboard-grid').style(
            'display: flex; flex-direction: row; gap: 1.5rem; '
            'width: 100%; align-items: flex-start;'
        ):
            # Sidebar: fixed 260px, never grows or shrinks, clips overflow
            with ui.element('div').style(
                'flex: 0 0 260px; width: 260px; max-width: 260px; overflow: hidden;'
            ):
                self.filter_container = ui.column().style('width: 100%; overflow: hidden;')
                with self.filter_container:
                    self.filter_sidebar = FilterSidebar(
                        filter_options=self.filter_options,
                        on_apply=self._on_filter_apply,
                        on_clear=self._on_filter_clear,
                        validity_questions=self.validity_questions,
                    )
                    self.filter_sidebar.render()

            self.main_content = ui.column().style('flex: 1 1 0; min-width: 0; gap: 1rem;')
            with self.main_content:
                self._render_summary_section()
                self._render_questions_section()
                self._render_crosstab_section()
                self._render_score_histogram()
                self._render_subscale_section()
                self._render_reliability()
                self._render_spearman_correlation()
                self._render_export_section()

    # ── Summary ────────────────────────────────────────────────────────

    def _render_summary_section(self):
        self.summary_container = ui.column().style('width: 100%;')
        with self.summary_container:
            stats = self.analytics_data.get('global_stats', {}) if self.analytics_data else {}
            n = stats.get('n', self.report_data.get('general_stats', {}).get('total_submissions', 0))
            alpha = self.analytics_data.get('cronbachs_alpha') if self.analytics_data else None
            SummaryCards(n_responses=n, global_stats=stats, cronbachs_alpha=alpha).render()

    # ── Score Histogram ────────────────────────────────────────────────

    def _render_score_histogram(self):
        self.score_hist_container = ui.column().style('width: 100%;')
        with self.score_hist_container:
            scores = self._get_global_scores()
            if scores:
                with ui.card().style('width: 100%; padding: 1rem;'):
                    fig = create_histogram(
                        values=scores,
                        title="Distribuição do escore global CHYPS-V",
                        x_label="Escore (0-60)",
                        nbins=max(5, len(set(scores))),
                        use_set1=True,
                    )
                    ui.plotly(fig).style("width: 100%; max-width: 650px;")

    # ── Subscale Section ───────────────────────────────────────────────

    def _render_subscale_section(self):
        self.subscale_container = ui.column().style('width: 100%;')
        with self.subscale_container:
            if self.analytics_data and self.analytics_data.get('subscale_stats'):
                with ui.card().style('width: 100%; padding: 1.5rem;'):
                    SubscaleSection(
                        subscale_stats=self.analytics_data['subscale_stats'],
                        respondent_scores=self.analytics_data.get('respondent_scores'),
                    ).render()

    # ── Reliability ────────────────────────────────────────────────────

    def _render_reliability(self):
        self.reliability_container = ui.column().style('width: 100%;')
        with self.reliability_container:
            alpha = self.analytics_data.get('cronbachs_alpha') if self.analytics_data else None
            ReliabilityCard(alpha=alpha, n_items=20).render()

    # ── Spearman Correlation ───────────────────────────────────────────

    def _render_spearman_correlation(self):
        self.spearman_container = ui.column().style('width: 100%;')
        with self.spearman_container:
            corr_data = self.analytics_data.get('spearman_correlation') if self.analytics_data else None
            if corr_data and corr_data.get('matrix'):
                with ui.card().style('width: 100%; padding: 1rem;'):
                    ui.label("Matriz de correlação cruzada de Spearman (ρ)").style(
                        'font-size: 1.2rem; font-weight: 700; color: #111827; margin-bottom: 0.5rem;'
                    )
                    fig = create_correlation_heatmap(
                        matrix=corr_data['matrix'],
                        labels=corr_data.get('labels', [f"Q{i}" for i in range(1, 21)]),
                        title="",
                        height=850,
                        width=900,
                    )
                    ui.plotly(fig).style("max-width: 1000px; overflow-x: auto;")

    # ── Question Cards ─────────────────────────────────────────────────

    def _render_questions_section(self):
        self.questions_container = ui.column().style('width: 100%;')
        with self.questions_container:
            with ui.card().style('width: 100%; padding: 1.5rem;'):
                ui.label('Distribuição por Questão').style(
                    'font-size: 1.2rem; font-weight: 700; color: #111827; margin-bottom: 1rem;')

                if not self.distributions:
                    ui.label('Nenhuma distribuição disponível.').style('color: #9ca3af;')
                    return

                with ui.element('div').style(
                    'display: grid; '
                    'grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); '
                    'gap: 1rem; width: 100%; align-items: stretch;'
                ):
                    for dist in self.distributions:
                        self._render_question_card(dist)

    def _render_question_card(self, dist: dict):
        chart_type = dist.get('chart_type', 'none')
        question_text = dist.get('question_title') or dist.get('question_text', '')
        question_body = dist.get('question_body')

        # T7 (excluded fields): skip TCLE, Nome, Email
        if _is_excluded(question_text, dist.get('question_title')):
            return

        # T5: Force pie only for definition question, race, sex
        if _force_pie(question_text) and chart_type == 'bar':
            chart_type = 'pie'

        # Item 9: Truncate 4th label ONLY for the discomfort definition question
        labels = dist.get('labels', [])
        if _is_discomfort_definition(question_text) and len(labels) >= 4:
            labels = _truncate_discomfort_labels(labels)

        # T7: Birthday → histogram by year, label "Ano de nascimento"
        if _is_birthday(question_text):
            self._render_birthday_card(dist)
            return

        # T9: Observation → text with expand button
        if _is_observation(question_text):
            self._render_observation_card(dist, question_text)
            return

        # T6: Full width card (no max-width constraint) to fit ~700px+ charts
        with ui.card().style(
            'width: 100%; padding: 1rem; '
            'background: #fafafa; border-radius: 8px;'
        ):
            self._render_question_content(question_text, question_body, chart_type, labels, dist)

    def _render_question_content(self, question_text, question_body, chart_type, labels, dist):
        ui.label(question_text).style(
            'font-weight: 600; color: #111827; font-size: 0.95rem; margin-bottom: 0.25rem;'
        )
        if question_body:
            formatted = self._format_rich_text(question_body)
            with ui.element('div').classes('report-richtext').style(
                'color: #6b7280; font-size: 0.85rem; line-height: 1.4; '
                'max-height: 100px; overflow-y: auto; margin-bottom: 0.5rem;'
            ):
                ui.html(formatted, sanitize=_passthrough_html)

        if chart_type == 'pie':
            fig = create_pie_chart(labels=labels, values=dist.get('counts', []), title="")
            fig.update_layout(height=300, margin={"l": 10, "r": 10, "t": 10, "b": 60})
            ui.plotly(fig).style("width: 100%;")

        elif chart_type == 'bar':
            counts = dist.get('counts', [])
            percentages = dist.get('percentages', [])
            max_label_len = max((len(l) for l in labels), default=0)
            num_labels = len(labels)
            use_horizontal = max_label_len > 20 or num_labels > 7

            if use_horizontal:
                bar_height = max(280, num_labels * 40 + 80)
                l_margin = min(200, max_label_len * 6 + 10)
                fig = create_bar_chart_h(
                    labels=labels, counts=counts, percentages=percentages,
                    title="", height=bar_height,
                )
                fig.update_layout(margin={"l": l_margin, "r": 80, "t": 10, "b": 40})
            else:
                fig = create_bar_chart(
                    labels=labels, counts=counts, percentages=percentages, title="",
                )
                tick_angle = -30 if max_label_len > 8 else 0
                b_margin = 80 if max_label_len > 8 else 50
                fig.update_layout(
                    height=320,
                    margin={"l": 40, "r": 20, "t": 20, "b": b_margin},
                    xaxis={"tickangle": tick_angle},
                )

            ui.plotly(fig).style("width: 100%;")
            stats = dist.get('stats')
            if stats:
                with ui.row().style(
                    "gap: 0.75rem; flex-wrap: wrap; margin-top: 0.5rem; justify-content: center;"
                ):
                    for lbl, key in [
                        ("Média", "mean"), ("DP", "sd"), ("Mediana", "median"),
                        ("Moda", "mode"), ("IIQ", "iqr"),
                    ]:
                        val = stats.get(key, 0)
                        with ui.badge(f"{lbl}: {val:.2f}").style(
                            "background-color: #40479f; color: #f7f0f7; "
                            "padding: 0.25rem 0.6rem; font-size: 0.75rem; font-weight: 500;"
                        ):
                            pass

        elif chart_type == 'text_table':
            qid = dist.get('question_id')
            responses = self._get_text_responses_for_question(qid)
            if responses:
                with ui.column().style('width: 100%; gap: 0.25rem;'):
                    for i, text in enumerate(responses[:5], 1):
                        ui.label(f'{i}. {text[:150]}{"..." if len(text) > 150 else ""}').style(
                            'font-size: 0.85rem; color: #374151; padding: 0.25rem 0.5rem; '
                            'background: white; border-radius: 4px; border: 1px solid #e5e7eb;'
                        )
                    if len(responses) > 5:
                        ui.label(f"... e mais {len(responses) - 5} respostas").style(
                            'color: #9ca3af; font-size: 0.8rem; font-style: italic;'
                        )
            else:
                ui.label("Nenhuma resposta textual.").style(
                    'color: #9ca3af; font-style: italic; font-size: 0.85rem;'
                )

    # T7: Birthday card with "Ano de nascimento" label
    def _render_birthday_card(self, dist: dict):
        qid = dist.get('question_id')
        responses = self._get_text_responses_for_question(qid)

        years = []
        for text in responses:
            try:
                parts = text.strip().split('/')
                if len(parts) == 3:
                    year = int(parts[2])
                    years.append(year)
            except (ValueError, IndexError):
                pass

        with ui.card().style(
            'width: 100%; padding: 1rem; '
            'background: #fafafa; border-radius: 8px;'
        ):
            ui.label("Ano de nascimento").style(
                'font-weight: 600; color: #111827; font-size: 0.95rem; margin-bottom: 0.5rem;'
            )
            if years:
                fig = create_histogram(
                    values=years,
                    title="",
                    x_label="Ano",
                    nbins=max(5, len(set(years))),
                    height=300,
                )
                ui.plotly(fig).style("width: 100%;")
            else:
                ui.label("Nenhuma data válida encontrada.").style(
                    'color: #9ca3af; font-style: italic; font-size: 0.85rem;'
                )

    # T9: Observation card with expand button
    def _render_observation_card(self, dist: dict, question_text: str):
        qid = dist.get('question_id')
        responses = self._get_text_responses_for_question(qid)

        with ui.card().style(
            'width: 100%; padding: 1rem; '
            'background: #fafafa; border-radius: 8px;'
        ):
            ui.label(question_text).style(
                'font-weight: 600; color: #111827; font-size: 0.95rem; margin-bottom: 0.25rem;'
            )

            if responses:
                with ui.column().style('width: 100%; gap: 0.25rem;'):
                    for i, text in enumerate(responses[:5], 1):
                        ui.label(f'{i}. {text[:150]}{"..." if len(text) > 150 else ""}').style(
                            'font-size: 0.85rem; color: #374151; padding: 0.25rem 0.5rem; '
                            'background: white; border-radius: 4px; border: 1px solid #e5e7eb;'
                        )
                    if len(responses) > 5:
                        ui.label(f"... e mais {len(responses) - 5} respostas").style(
                            'color: #9ca3af; font-size: 0.8rem; font-style: italic;'
                        )

                ui.button(
                    'Expandir',
                    icon='unfold_more',
                    on_click=lambda: self._show_observation_dialog(question_text, responses),
                ).props('flat dense color=primary').style('margin-top: 0.5rem;')
            else:
                ui.label("Nenhuma observação registrada.").style(
                    'color: #9ca3af; font-style: italic; font-size: 0.85rem;'
                )

    def _show_observation_dialog(self, question_text: str, responses: list):
        with ui.dialog() as dialog, ui.card().style(
            'width: 700px; max-width: 95vw; max-height: 80vh; padding: 1.5rem;'
        ):
            with ui.row().style('width: 100%; justify-content: space-between; align-items: center;'):
                ui.label(question_text).style(
                    'font-weight: 700; color: #111827; font-size: 1.1rem;')
                ui.button(icon='close', on_click=dialog.close).props('flat dense')

            ui.label(f'{len(responses)} observação(ões)').style(
                'color: #6b7280; font-size: 0.85rem; margin: 0.5rem 0;'
            )

            with ui.scroll_area().style('height: 60vh; width: 100%;'):
                with ui.column().style('width: 100%; gap: 0.5rem;'):
                    for i, text in enumerate(responses, 1):
                        with ui.card().style(
                            'width: 100%; padding: 0.75rem; '
                            'background: white; border: 1px solid #e5e7eb; border-radius: 6px;'
                        ):
                            ui.label(f'{i}. {text}').style(
                                'font-size: 0.9rem; color: #374151; white-space: pre-wrap;'
                            )

            with ui.row().style('width: 100%; justify-content: flex-end; margin-top: 1rem;'):
                ui.button('Fechar', on_click=dialog.close).props('flat color=primary')

        dialog.open()

    # ── Crosstab Section ───────────────────────────────────────────────

    def _render_crosstab_section(self):
        self.crosstab_container = ui.column().style('width: 100%;')
        with self.crosstab_container:
            self.crosstab_tool = CrosstabTool(
                variables=self.crosstab_variables,
                on_generate=self._on_crosstab_generate,
            )
            self.crosstab_tool.render()

    # ── Export Section ──────────────────────────────────────────────────

    def _render_export_section(self):
        self.export_container = ui.column().style('width: 100%;')
        with self.export_container:
            ExportButtons(self.questionnaire_id).render()

    # ── Event Handlers ─────────────────────────────────────────────────

    def _on_filter_apply(self, filters: dict):
        self.current_filters = filters
        self._refresh_dynamic_sections()

    def _on_filter_clear(self):
        self.current_filters = {}
        self._refresh_dynamic_sections()

    def _refresh_dynamic_sections(self):
        try:
            self.analytics_data = analytics_service.get_filtered_analytics(
                self.questionnaire_id,
                self.current_filters or None
            )
        except Exception:
            self.analytics_data = None

        for container in [
            self.summary_container,
            self.score_hist_container,
            self.subscale_container,
            self.reliability_container,
            self.spearman_container,
        ]:
            if container:
                container.clear()

        if self.summary_container:
            with self.summary_container:
                stats = self.analytics_data.get('global_stats', {}) if self.analytics_data else {}
                n = stats.get('n', 0)
                alpha = self.analytics_data.get('cronbachs_alpha') if self.analytics_data else None
                SummaryCards(n_responses=n, global_stats=stats, cronbachs_alpha=alpha).render()

        if self.score_hist_container:
            with self.score_hist_container:
                scores = self._get_global_scores()
                if scores:
                    with ui.card().style('width: 100%; padding: 1rem;'):
                        fig = create_histogram(
                            values=scores,
                            title="Distribuição do escore global CHYPS-V",
                            x_label="Escore (0-60)",
                            nbins=max(5, len(set(scores))),
                            use_set1=True,
                        )
                        ui.plotly(fig).style("width: 100%; max-width: 650px;")

        if self.subscale_container:
            with self.subscale_container:
                if self.analytics_data and self.analytics_data.get('subscale_stats'):
                    with ui.card().style('width: 100%; padding: 1.5rem;'):
                        SubscaleSection(
                            subscale_stats=self.analytics_data['subscale_stats'],
                            respondent_scores=self.analytics_data.get('respondent_scores'),
                        ).render()

        if self.reliability_container:
            with self.reliability_container:
                alpha = self.analytics_data.get('cronbachs_alpha') if self.analytics_data else None
                ReliabilityCard(alpha=alpha, n_items=20).render()

        if self.spearman_container:
            with self.spearman_container:
                corr_data = self.analytics_data.get('spearman_correlation') if self.analytics_data else None
                if corr_data and corr_data.get('matrix'):
                    with ui.card().style('width: 100%; padding: 1rem;'):
                        ui.label("Matriz de correlação cruzada de Spearman (ρ)").style(
                            'font-size: 1.2rem; font-weight: 700; color: #111827; margin-bottom: 0.5rem;'
                        )
                        fig = create_correlation_heatmap(
                            matrix=corr_data['matrix'],
                            labels=corr_data.get('labels', [f"Q{i}" for i in range(1, 21)]),
                            title="",
                            height=850,
                            width=900,
                        )
                        ui.plotly(fig).style("max-width: 1000px; overflow-x: auto;")

    def _on_crosstab_generate(self, row_var: str, col_var: str):
        if not self.crosstab_tool:
            return
        try:
            result = analytics_service.get_crosstab(
                self.questionnaire_id,
                row_var,
                col_var,
                self.current_filters or None,
            )
            self.crosstab_tool.render_result(result or {})
        except Exception as e:
            self.crosstab_tool.render_result({})
            ui.notify(f"Erro ao gerar tabulação: {e}", type="negative")

    # ── Helpers ────────────────────────────────────────────────────────

    def _get_global_scores(self):
        if self.analytics_data and self.analytics_data.get('respondent_scores'):
            return [r['global_score'] for r in self.analytics_data['respondent_scores']]
        submissions = self.report_data.get('anonymous_submissions', [])
        return [s.get('chyps_score', s.get('total_score', 0)) for s in submissions]

    def _get_text_responses_for_question(self, question_id: int) -> list:
        responses = []
        for sub in self.report_data.get('anonymous_submissions', []):
            for ans in sub.get('answers', []):
                if ans.get('question_id') == question_id and ans.get('text_response'):
                    responses.append(ans['text_response'])
        return responses

    def _format_rich_text(self, text: str) -> str:
        if not text:
            return ''
        decoded_text = unescape(text)
        if re.search(r'<\s*\/?\s*[a-zA-Z][^>]*>', decoded_text):
            return decoded_text
        if re.search(r'<(p|ul|ol|li|strong|b|em|br|div|span)[\s>/]', text, re.IGNORECASE):
            return text
        return escape(text).replace('\n', '<br>')
