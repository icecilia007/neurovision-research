from nicegui import ui
from services.custom_export_service import custom_export_service, EXPORT_FORMATS
from services.questionnaire_service import questionnaire_service
from services.report_service import report_service
from utils.session_manager import session_manager

# ── Visual constants ──────────────────────────────────────────────────────────

_STEP = (
    'width: 26px; height: 26px; border-radius: 50%; background: #4f46e5; '
    'color: white; font-weight: 700; font-size: 0.82rem; '
    'display: flex; align-items: center; justify-content: center; flex-shrink: 0;'
)
_CARD_OFF = (
    'padding: 1rem 1.25rem; cursor: pointer; transition: border-color 0.15s, background 0.15s; '
    'border: 2px solid #e5e7eb; border-radius: 10px;'
)
_CARD_ON = (
    'padding: 1rem 1.25rem; cursor: pointer; transition: border-color 0.15s, background 0.15s; '
    'border: 2px solid #4f46e5; border-radius: 10px; background: #eef2ff;'
)
_FMT_OFF = (
    'padding: 0.875rem 1rem; cursor: pointer; border: 2px solid #e5e7eb; '
    'border-radius: 8px; transition: all 0.15s; min-width: 130px; text-align: center;'
)
_FMT_ON = (
    'padding: 0.875rem 1rem; cursor: pointer; border: 2px solid #4f46e5; '
    'border-radius: 8px; background: #eef2ff; transition: all 0.15s; min-width: 130px; text-align: center;'
)

# ── Domain constants ──────────────────────────────────────────────────────────

META_FIELDS = {
    'submission_id': 'ID da Submissão',
    'submitted_at':  'Data de Envio',
    'total_score':   'Pontuação Total',
}

QUESTIONNAIRE_FIELDS = {
    'id':             'ID',
    'titulo':         'Título',
    'descricao':      'Descrição',
    'question_order': 'Ordem das Questões',
    'is_active':      'Ativo',
}

MODES = [
    (
        'responses',
        'question_answer',
        'Respostas por Questionário',
        'Selecione questões específicas e exporte cada resposta como coluna',
    ),
    (
        'questionnaires',
        'quiz',
        'Lista de Questionários',
        'Exporte metadados dos seus questionários',
    ),
]


class CustomExportPage:
    def __init__(self, on_back=None, content_container=None):
        self.on_back = on_back
        self.content_container = content_container

        # ── State ──────────────────────────────────────────────────────
        self.mode: str | None = None
        self.questionnaires: list = []
        self.selected_questionnaire_id: int | None = None
        self.questions_data: list = []           # [{question_id, caption, question_text}]
        self.selected_question_ids: set = set()
        self.selected_meta_fields: set = set(META_FIELDS)
        self.selected_q_fields: set = {'id', 'titulo', 'descricao', 'is_active'}
        self.selected_format: str = 'csv'
        self.filter_date_from: str = ''
        self.filter_date_to: str = ''

        # ── UI refs ────────────────────────────────────────────────────
        self._mode_cards: dict = {}
        self._format_cards: dict = {}
        self._q_cbs: dict = {}           # question_id → checkbox (responses)
        self._qf_cbs: dict = {}          # field_key → checkbox (questionnaires)
        self._select_widget = None
        self._mode_content = None
        self._responses_dynamic = None
        self._date_from_input = None
        self._date_to_input = None

    # ── Entry point ───────────────────────────────────────────────────

    def render(self):
        creator_id = (session_manager.current_user or {}).get('id')
        try:
            self.questionnaires = questionnaire_service.list_by_creator(creator_id) or []
        except Exception:
            self.questionnaires = []

        with ui.column().style('width: 100%; max-width: 960px; gap: 1.5rem;'):
            self._render_header()
            self._render_mode_section()
            self._mode_content = ui.column().style('width: 100%; gap: 1.5rem;')

    # ── Header ────────────────────────────────────────────────────────

    def _render_header(self):
        with ui.row().style('width: 100%; justify-content: space-between; align-items: center;'):
            with ui.column().style('gap: 0.2rem;'):
                ui.label('Exportação Personalizada').style(
                    'font-size: 1.4rem; font-weight: 700; color: #111827;')
                ui.label(
                    'Escolha questões, aplique filtros e exporte no formato que preferir'
                ).style('font-size: 0.9rem; color: #6b7280;')
            if self.on_back:
                ui.button('Voltar', on_click=self.on_back, icon='arrow_back') \
                    .props('outline').style('border-radius: 8px; height: 36px;')

    # ── Step 1 — mode ─────────────────────────────────────────────────

    def _render_mode_section(self):
        with ui.card().style('width: 100%; padding: 1.5rem;'):
            self._sh('1', 'O que deseja exportar?')
            with ui.row().style('gap: 1rem; flex-wrap: wrap;'):
                for key, icon, label, desc in MODES:
                    card = ui.card().style(_CARD_OFF)
                    self._mode_cards[key] = card
                    with card:
                        with ui.row().style('align-items: flex-start; gap: 0.75rem;'):
                            ui.icon(icon, size='1.75rem', color='primary') \
                                .style('flex-shrink: 0; margin-top: 2px;')
                            with ui.column().style('gap: 0.2rem;'):
                                ui.label(label).style(
                                    'font-weight: 600; color: #111827; font-size: 0.95rem;')
                                ui.label(desc).style(
                                    'font-size: 0.8rem; color: #6b7280; line-height: 1.3;')
                    card.on('click', lambda _e, k=key: self._on_mode(k))

    def _on_mode(self, mode: str):
        self.mode = mode
        for k, c in self._mode_cards.items():
            c.style(_CARD_ON if k == mode else _CARD_OFF)
        self._mode_content.clear()
        with self._mode_content:
            if mode == 'responses':
                self._flow_responses()
            else:
                self._flow_questionnaires()

    # ── RESPONSES FLOW ────────────────────────────────────────────────

    def _flow_responses(self):
        # Step 2 — questionnaire picker
        with ui.card().style('width: 100%; padding: 1.5rem;'):
            self._sh('2', 'Questionário')
            ui.label('Selecione o questionário de origem das respostas').style(
                'color: #6b7280; font-size: 0.9rem; margin-bottom: 1rem;')

            if not self.questionnaires:
                with ui.row().style('gap: 0.5rem; align-items: center; color: #9ca3af;'):
                    ui.icon('inbox')
                    ui.label('Nenhum questionário encontrado.')
                return

            opts = {
                str(q['id']): q.get('titulo', f"Questionário {q['id']}")
                for q in self.questionnaires
            }
            self._select_widget = ui.select(
                opts,
                label='Selecione um questionário',
                on_change=lambda _e: self._load_questions(),
            ).style('min-width: 280px; max-width: 480px;')

        # Placeholder — filled after loading
        self._responses_dynamic = ui.column().style('width: 100%; gap: 1.5rem;')

    def _load_questions(self):
        val = getattr(self._select_widget, 'value', None)
        if not val:
            return

        self.selected_questionnaire_id = int(val)
        self.selected_question_ids = set()
        self.questions_data = []
        self._q_cbs = {}

        self._responses_dynamic.clear()
        with self._responses_dynamic:
            with ui.row().style('align-items: center; gap: 1rem; padding: 1rem;'):
                ui.spinner(size='1.5rem', color='primary')
                ui.label('Carregando questões...').style('color: #6b7280;')

        try:
            # Usa o endpoint leve de estrutura — não carrega submissões
            qr = questionnaire_service.get_questionnaire_for_response(str(self.selected_questionnaire_id))
            if not qr:
                raise Exception('Questionário não encontrado')
            self.questions_data = self._extract_questions_from_structure(qr)
            self.selected_question_ids = {q['question_id'] for q in self.questions_data}
        except Exception as e:
            self._responses_dynamic.clear()
            with self._responses_dynamic:
                with ui.row().style('gap: 0.5rem; align-items: center; color: #b91c1c;'):
                    ui.icon('error_outline')
                    ui.label(f'Erro ao carregar: {e}')
            return

        n_q = len(self.questions_data)
        self._responses_dynamic.clear()
        with self._responses_dynamic:
            with ui.row().style(
                'gap: 0.5rem; align-items: center; padding: 0.5rem 0.75rem; '
                'background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px;'
            ):
                ui.icon('check_circle', color='positive', size='1.2rem')
                ui.label(f'{n_q} questões carregadas').style(
                    'color: #15803d; font-size: 0.9rem; font-weight: 500;')

            self._render_meta_section()
            self._render_question_groups()
            self._render_filters('submitted_at', 'Data de Envio')
            self._render_format_export()

    def _extract_questions_from_structure(self, qr: dict) -> list:
        """Extrai questões da estrutura do questionário (endpoint /respond), em ordem."""
        questions = []
        for item in qr.get('items', []):
            if item.get('tipo') not in ('question', 'term'):
                continue
            content = item.get('content', {})
            q_id = content.get('id')
            if not q_id:
                continue
            questions.append({
                'question_id': q_id,
                'caption':       (content.get('caption') or '').strip(),
                'question_text': (content.get('titulo') or content.get('texto') or '').strip(),
            })
        return questions

    # ── Step 3 — submission metadata ──────────────────────────────────

    def _render_meta_section(self):
        with ui.card().style('width: 100%; padding: 1.5rem;'):
            self._sh('3', 'Dados da Submissão')
            ui.label('Inclua campos de controle em cada linha exportada').style(
                'color: #6b7280; font-size: 0.9rem; margin-bottom: 1rem;')
            with ui.row().style('gap: 2rem; flex-wrap: wrap;'):
                for fk, fl in META_FIELDS.items():
                    ui.checkbox(
                        fl,
                        value=fk in self.selected_meta_fields,
                        on_change=lambda e, k=fk: (
                            self.selected_meta_fields.add(k)
                            if e.value else self.selected_meta_fields.discard(k)
                        ),
                    )

    # ── Steps 4+ — question groups ────────────────────────────────────

    def _render_question_groups(self):
        if not self.questions_data:
            with ui.card().style(
                'width: 100%; padding: 1.5rem; '
                'border-left: 4px solid #f59e0b; background: #fffbeb;'
            ):
                with ui.row().style('gap: 0.5rem; align-items: center; color: #92400e;'):
                    ui.icon('warning_amber')
                    ui.label(
                        'Nenhuma questão disponível. '
                        'Pode não haver submissões neste questionário.'
                    )
            return

        groups = self._group_questions(self.questions_data)
        step = 4

        for _key, g_label, g_questions in groups:
            if not g_questions:
                continue
            g_ids = [q['question_id'] for q in g_questions]

            with ui.card().style('width: 100%; padding: 1.5rem;'):
                # Group header: step + label + bulk actions
                with ui.row().style(
                    'align-items: center; justify-content: space-between; '
                    'margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem;'
                ):
                    self._sh(str(step), g_label)
                    step += 1

                    with ui.row().style('gap: 0.5rem;'):
                        ui.button(
                            'Selecionar todas',
                            on_click=lambda _, ids=g_ids: self._set_group(ids, True),
                        ).props('flat dense color=primary').style('font-size: 0.8rem;')
                        ui.button(
                            'Desmarcar todas',
                            on_click=lambda _, ids=g_ids: self._set_group(ids, False),
                        ).props('flat dense color=grey-7').style('font-size: 0.8rem;')

                # Question checkboxes
                with ui.column().style('gap: 0.35rem;'):
                    for q in g_questions:
                        q_id = q['question_id']
                        cap  = q.get('caption', '')
                        text = q.get('question_text', '')
                        label = f"{cap}: {text}" if cap else text
                        if len(label) > 95:
                            label = label[:92] + '…'
                        cb = ui.checkbox(
                            label,
                            value=q_id in self.selected_question_ids,
                            on_change=lambda e, k=q_id: (
                                self.selected_question_ids.add(k)
                                if e.value else self.selected_question_ids.discard(k)
                            ),
                        )
                        self._q_cbs[q_id] = cb

    def _group_questions(self, questions: list) -> list:
        socio, main, other = [], [], []
        for q in questions:
            cap = (q.get('caption') or '').upper()
            if cap.startswith('T'):
                socio.append(q)
            elif cap.startswith('Q'):
                main.append(q)
            else:
                other.append(q)
        return [
            ('socio',  'Sociodemográfico',         socio),
            ('main',   'Questões do Instrumento',  main),
            ('other',  'Outras Questões',           other),
        ]

    def _set_group(self, ids: list, state: bool):
        for q_id in ids:
            self.selected_question_ids.add(q_id) if state \
                else self.selected_question_ids.discard(q_id)
            if q_id in self._q_cbs:
                self._q_cbs[q_id].value = state

    # ── QUESTIONNAIRES FLOW ───────────────────────────────────────────

    def _flow_questionnaires(self):
        with ui.card().style('width: 100%; padding: 1.5rem;'):
            self._sh('2', 'Campos')
            ui.label('Selecione os campos dos questionários a exportar').style(
                'color: #6b7280; font-size: 0.9rem; margin-bottom: 1rem;')

            with ui.row().style('gap: 0.5rem; margin-bottom: 0.75rem;'):
                ui.button('Selecionar todos',
                          on_click=lambda: self._qf_set_all(True)) \
                    .props('flat dense color=primary').style('font-size: 0.8rem;')
                ui.button('Desmarcar todos',
                          on_click=lambda: self._qf_set_all(False)) \
                    .props('flat dense color=grey-7').style('font-size: 0.8rem;')

            self._qf_cbs = {}
            with ui.grid(columns=2).style('width: 100%; gap: 0.25rem;'):
                for fk, fl in QUESTIONNAIRE_FIELDS.items():
                    cb = ui.checkbox(
                        fl,
                        value=fk in self.selected_q_fields,
                        on_change=lambda e, k=fk: (
                            self.selected_q_fields.add(k)
                            if e.value else self.selected_q_fields.discard(k)
                        ),
                    )
                    self._qf_cbs[fk] = cb

        self._render_filters('created_at', 'Data de Criação')
        self._render_format_export()

    def _qf_set_all(self, state: bool):
        self.selected_q_fields = set(QUESTIONNAIRE_FIELDS) if state else set()
        for cb in self._qf_cbs.values():
            cb.value = state

    # ── Filters ───────────────────────────────────────────────────────

    def _render_filters(self, date_field: str, date_label: str):
        self.filter_date_from = ''
        self.filter_date_to = ''
        self._date_field = date_field

        with ui.card().style('width: 100%; padding: 1.5rem;'):
            with ui.row().style('align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;'):
                ui.icon('filter_list', size='1.25rem', color='primary')
                ui.label('Filtros').style('font-size: 1.05rem; font-weight: 700; color: #111827;')

            ui.label('Restrinja os dados por período — opcional').style(
                'color: #6b7280; font-size: 0.9rem; margin-bottom: 0.75rem;')
            ui.label(f'Filtrar por {date_label}').style(
                'font-size: 0.85rem; font-weight: 600; color: #374151; margin-bottom: 0.5rem;')

            with ui.row().style('gap: 1rem; flex-wrap: wrap; align-items: flex-end;'):
                self._date_from_input = ui.input(
                    'Data inicial',
                    on_change=lambda e: setattr(self, 'filter_date_from', e.value or ''),
                ).style('min-width: 170px;')
                self._date_from_input.props('type=date')

                self._date_to_input = ui.input(
                    'Data final',
                    on_change=lambda e: setattr(self, 'filter_date_to', e.value or ''),
                ).style('min-width: 170px;')
                self._date_to_input.props('type=date')

                ui.button('Limpar', icon='clear', on_click=self._clear_dates) \
                    .props('flat dense color=grey-7').style('height: 40px;')

    def _clear_dates(self):
        self.filter_date_from = ''
        self.filter_date_to = ''
        if self._date_from_input:
            self._date_from_input.value = ''
        if self._date_to_input:
            self._date_to_input.value = ''

    # ── Format + Export ───────────────────────────────────────────────

    def _render_format_export(self):
        self._format_cards = {}
        self.selected_format = 'csv'

        with ui.card().style('width: 100%; padding: 1.5rem;'):
            with ui.row().style('align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;'):
                ui.icon('download', size='1.25rem', color='primary')
                ui.label('Formato e Exportação').style(
                    'font-size: 1.05rem; font-weight: 700; color: #111827;')

            ui.label('Escolha o formato do arquivo e confirme a exportação').style(
                'color: #6b7280; font-size: 0.9rem; margin-bottom: 1rem;')

            with ui.row().style('gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem;'):
                for fmt_key, fmt_label, fmt_desc, fmt_icon in EXPORT_FORMATS:
                    fc = ui.card().style(_FMT_ON if fmt_key == 'csv' else _FMT_OFF)
                    self._format_cards[fmt_key] = fc
                    with fc:
                        with ui.column().style('align-items: center; gap: 0.4rem;'):
                            ui.icon(fmt_icon, size='1.5rem', color='primary')
                            ui.label(fmt_label).style(
                                'font-weight: 600; color: #111827; font-size: 0.9rem;')
                            ui.label(fmt_desc).style(
                                'font-size: 0.72rem; color: #9ca3af; line-height: 1.3;')
                    fc.on('click', lambda _e, k=fmt_key: self._on_format(k))

            ui.separator().style('margin: 0.25rem 0 1rem 0;')
            with ui.row().style('justify-content: flex-end;'):
                ui.button('Exportar Dados', on_click=self._do_export, icon='download') \
                    .props('color=primary').style(
                    'border-radius: 8px; height: 42px; font-size: 1rem; padding: 0 1.5rem;')

    def _on_format(self, fmt: str):
        self.selected_format = fmt
        for k, c in self._format_cards.items():
            c.style(_FMT_ON if k == fmt else _FMT_OFF)

    # ── Export action ─────────────────────────────────────────────────

    def _do_export(self):
        if not self.mode:
            ui.notify('Selecione o tipo de exportação.', type='warning')
            return
        try:
            if self.mode == 'responses':
                self._export_responses()
            else:
                self._export_questionnaires()
        except Exception as e:
            ui.notify(f'Erro ao exportar: {e}', type='negative')

    def _export_responses(self):
        if not self.selected_questionnaire_id:
            ui.notify('Carregue as questões de um questionário primeiro.', type='warning')
            return
        if not self.selected_question_ids and not self.selected_meta_fields:
            ui.notify('Selecione pelo menos um campo ou questão.', type='warning')
            return

        q_title = next(
            (q.get('titulo', 'questionario') for q in self.questionnaires
             if str(q.get('id')) == str(self.selected_questionnaire_id)),
            'questionario',
        )
        slug     = q_title.lower().replace(' ', '_')[:30]
        fmt      = self.selected_format
        filename = f'exportacao_respostas_{slug}.{fmt}'

        content = report_service.custom_export(
            questionnaire_id=self.selected_questionnaire_id,
            question_ids=list(self.selected_question_ids),
            meta_fields=list(self.selected_meta_fields),
            date_from=self.filter_date_from,
            date_to=self.filter_date_to,
            format_type=fmt,
        )
        ui.download(content, filename)
        ui.notify(f'Exportação {fmt.upper()} concluída.', type='positive')

    def _export_questionnaires(self):
        if not self.selected_q_fields:
            ui.notify('Selecione pelo menos um campo.', type='warning')
            return

        creator_id = (session_manager.current_user or {}).get('id')
        raw = questionnaire_service.list_by_creator(creator_id) or []

        filtered = []
        for q in raw:
            ts = str(q.get('created_at', '') or '')[:10]
            if self.filter_date_from and ts < self.filter_date_from:
                continue
            if self.filter_date_to and ts > self.filter_date_to:
                continue
            filtered.append(q)

        columns = [f for f in QUESTIONNAIRE_FIELDS if f in self.selected_q_fields]
        rows = [{c: q.get(c, '') for c in columns} for q in filtered]

        if not rows:
            ui.notify('Nenhum questionário encontrado.', type='warning')
            return

        self._download(rows, columns, 'questionarios', QUESTIONNAIRE_FIELDS)

    def _download(self, rows: list, columns: list, name: str, labels: dict = None):
        fmt      = self.selected_format
        filename = f'exportacao_{name}.{fmt}'
        lbl      = labels or {c: c for c in columns}

        if fmt == 'csv':
            content = custom_export_service.to_csv(rows, columns)
        elif fmt == 'json':
            content = custom_export_service.to_json(rows)
        elif fmt == 'xlsx':
            content = custom_export_service.to_xlsx(rows, columns, lbl)

        ui.download(content, filename)
        ui.notify(f'{len(rows)} registros exportados em {fmt.upper()}.', type='positive')

    # ── Helper ────────────────────────────────────────────────────────

    def _sh(self, step: str, title: str):
        """Render a section header with a numbered step circle."""
        with ui.row().style('align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;'):
            ui.label(step).style(_STEP)
            ui.label(title).style('font-size: 1.05rem; font-weight: 700; color: #111827;')
