from nicegui import ui, app
import re
from datetime import datetime
from html import escape, unescape
from services.questionnaire_service import questionnaire_service
from services.response_service import response_service
from utils.session_manager import session_manager
from components.auth.auth_modal import AuthModal


def _passthrough_html(value: str) -> str:
    return value


EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$')


class QuestionnaireAnswerPage:
    def __init__(self, questionnaire_id: str):
        self.questionnaire_id = questionnaire_id
        self.questionnaire_data = None
        self.answers = {}
        self.loading = False
        self.steps = []          # list of (step_number, label, [items])
        self.current_step_index = 0
        self.conditional_children = {}  # trigger question_id -> [refs to dependent questions]
        self.questions_by_id = {}       # question_id -> content dict (questions and terms)

    def render(self):
        ui.add_head_html('''
        <style>
            .term-richtext p { margin: 0.5rem 0; }
            .term-richtext ul, .term-richtext ol {
                margin: 0.5rem 0;
                padding-left: 1.5rem;
                list-style-position: outside;
                list-style: initial !important;
            }
            .term-richtext ul { list-style-type: disc !important; }
            .term-richtext ol { list-style-type: decimal !important; }
            .term-richtext li {
                margin: 0.25rem 0;
                display: list-item !important;
            }
            .term-richtext li::marker { color: #374151 !important; }
        </style>
        ''')

        self.main_container = ui.column().style(
            'width: 100%; max-width: 900px; margin: 0 auto; padding: 1rem;'
        )

        self._render_loading()
        self._load_questionnaire()

    # ─── Session persistence (survives F5) ────────────────────────────────────

    def _storage_key(self) -> str:
        return f'qresp_{self.questionnaire_id}'

    def _save_progress(self):
        try:
            app.storage.user[self._storage_key()] = {
                'step': self.current_step_index,
                'answers': {str(k): v for k, v in self.answers.items()},
            }
        except Exception as e:
            print(f"DEBUG: erro ao salvar progresso: {e}")

    def _restore_progress(self):
        """Restore saved answers, discarding anything that no longer matches the
        current questionnaire (question removed, option ids changed) — NiceGUI 3.x
        raises ValueError when a radio/select is built with a value that is not
        among its options. Must run after `_build_steps`."""
        try:
            saved = app.storage.user.get(self._storage_key())
            if not saved:
                return

            restored = {}
            for key, answer in (saved.get('answers') or {}).items():
                try:
                    question_id = int(key)
                except (TypeError, ValueError):
                    continue
                question = self.questions_by_id.get(question_id)
                if not question or not isinstance(answer, dict):
                    continue
                valid_option_ids = {opt.get('id') for opt in question.get('options', [])}
                restored[question_id] = {
                    'selected_options': [
                        oid for oid in (answer.get('selected_options') or [])
                        if oid in valid_option_ids
                    ],
                    'text_response': answer.get('text_response'),
                }
            self.answers = restored

            step = int(saved.get('step', 0))
            if 0 <= step < len(self.steps):
                self.current_step_index = step
        except Exception as e:
            print(f"DEBUG: erro ao restaurar progresso: {e}")

    def _clear_progress(self):
        try:
            app.storage.user.pop(self._storage_key(), None)
        except Exception:
            pass

    # ─── Loading ───────────────────────────────────────────────────────────────

    def _render_loading(self):
        with self.main_container:
            with ui.element('div').style(
                    'display: flex; '
                    'flex-direction: column; '
                    'align-items: center; '
                    'justify-content: center; '
                    'min-height: 75vh; '
                    'width: 100%; '
                    'padding: 2rem 1rem; '
                    'box-sizing: border-box;'
            ):
                with ui.column().style(
                        'align-items: center; '
                        'gap: 2rem; '
                        'max-width: 400px; '
                        'width: 100%; '
                        'text-align: center;'
                ):
                    ui.label('Carregando questionário...').style(
                        'font-size: clamp(1.25rem, 4vw, 1.75rem); '
                        'font-weight: 600; '
                        'color: #111827; '
                        'text-align: center; '
                        'margin: 0; '
                        'line-height: 1.3; '
                        'word-wrap: break-word;'
                    )

                    ui.spinner(size='3rem', color='primary')

    def _load_questionnaire(self):
        if hasattr(self, 'main_container'):
            self.main_container.clear()

        try:
            self.questionnaire_data = questionnaire_service.get_questionnaire_for_response(self.questionnaire_id)

            if self.questionnaire_data:
                self.real_questionnaire_id = self.questionnaire_data.get('id')
                print(f"DEBUG: ID real obtido: {self.real_questionnaire_id}")
                print(f"DEBUG: Título: {self.questionnaire_data.get('titulo')}")
                print(f"DEBUG: Total de items: {len(self.questionnaire_data.get('items', []))}")

                if self.real_questionnaire_id:
                    self._build_steps()
                    self._restore_progress()
                    self._render_questionnaire()
                else:
                    self._render_error("Erro: Não foi possível obter ID do questionário")

            else:
                self._render_error("Questionário não encontrado")

        except Exception as e:
            self._render_error(f"Erro ao carregar questionário: {str(e)}")

    def _build_steps(self):
        """Group items by their `step` field; labels come from the
        questionnaire's `step_labels` (fallback: 'Etapa N')."""
        items = self.questionnaire_data.get('items', [])
        labels = self.questionnaire_data.get('step_labels') or []

        grouped = {}
        self.questions_by_id = {}
        for item in items:
            step = item.get('step', 1) or 1
            grouped.setdefault(step, []).append(item)
            if item.get('tipo') in ('question', 'term'):
                content = item.get('content') or {}
                if content.get('id'):
                    self.questions_by_id[content['id']] = content

        self.steps = []
        for step_number in sorted(grouped.keys()):
            # Preserve the order the API delivered (it already applies the
            # questionnaire's question_order, including random shuffling).
            step_items = grouped[step_number]
            if 0 < step_number <= len(labels) and labels[step_number - 1]:
                label = labels[step_number - 1]
            else:
                label = f'Etapa {step_number}'
            self.steps.append((step_number, label, step_items))

    @property
    def _is_multi_step(self) -> bool:
        return len(self.steps) > 1

    # ─── Main shell ─────────────────────────────────────────────────────────────

    def _render_questionnaire(self):
        ui.page_title(self.questionnaire_data['titulo'])

        with self.main_container:
            with ui.column().style('width: 100%; gap: 1rem;'):
                ui.label(self.questionnaire_data['titulo']).style(
                    'font-size: 2.5rem; font-weight: 700; text-align: center; color: #111827; '
                    'margin-bottom: 0.5rem; line-height: 1.2;'
                )

                if self.questionnaire_data.get('descricao'):
                    ui.label(self.questionnaire_data['descricao']).style(
                        'font-size: 1.1rem; text-align: center; color: #6b7280; margin-bottom: 1rem; '
                        'line-height: 1.5; max-width: 800px; margin-left: auto; margin-right: auto;'
                    )

                self.step_indicator_mount = ui.element('div').style('width: 100%;')

                ui.separator().style('margin: 0.5rem 0;')

                self.step_content = ui.column().style('width: 100%; gap: 2rem;')

                ui.separator().style('margin: 2rem 0 1rem 0;')

                self.nav_mount = ui.row().style(
                    'width: 100%; justify-content: center; gap: 1rem; flex-wrap: wrap;'
                )

        self._render_current_step()

    def _render_step_indicator(self):
        if not self._is_multi_step:
            return

        # 'safe center' keeps the first steps reachable when the indicator
        # overflows horizontally on narrow screens (plain 'center' would clip
        # them outside the scrollable area).
        with ui.element('div').style(
            'display: flex; align-items: flex-start; justify-content: safe center; '
            'width: 100%; padding: 0.75rem 0.25rem; overflow-x: auto;'
        ):
            for i, (_, label, _items) in enumerate(self.steps):
                is_active = i == self.current_step_index
                is_done = i < self.current_step_index

                circle_bg = '#2563eb' if is_active else ('#059669' if is_done else '#e5e7eb')
                number_color = 'white' if (is_active or is_done) else '#9ca3af'
                label_color = '#1f2937' if is_active else ('#374151' if is_done else '#6b7280')
                label_weight = '600' if is_active else '400'

                with ui.element('div').style(
                    'display: flex; flex-direction: column; align-items: center; '
                    'gap: 0.4rem; min-width: 70px; max-width: 110px;'
                ):
                    with ui.element('div').style(
                        f'width: 2.25rem; height: 2.25rem; border-radius: 50%; '
                        f'background: {circle_bg}; display: flex; align-items: center; '
                        f'justify-content: center; flex-shrink: 0;'
                    ):
                        ui.label('✓' if is_done else str(i + 1)).style(
                            f'font-size: 0.9rem; font-weight: 700; color: {number_color}; line-height: 1;'
                        )
                    ui.label(label).style(
                        f'font-size: 0.7rem; text-align: center; color: {label_color}; '
                        f'font-weight: {label_weight}; line-height: 1.2; word-break: break-word;'
                    )

                if i < len(self.steps) - 1:
                    line_color = '#059669' if is_done else '#e5e7eb'
                    ui.element('div').style(
                        f'flex: 1; height: 2px; background: {line_color}; '
                        f'margin-top: 1.1rem; min-width: 0.75rem; max-width: 4rem;'
                    )

    def _render_current_step(self):
        self.step_indicator_mount.clear()
        with self.step_indicator_mount:
            self._render_step_indicator()

        self.step_content.clear()
        self.nav_mount.clear()
        self.conditional_children = {}

        if not self.steps:
            return

        _, label, step_items = self.steps[self.current_step_index]
        is_first = self.current_step_index == 0
        is_last = self.current_step_index == len(self.steps) - 1

        with self.step_content:
            if self._is_multi_step:
                ui.label(label).style(
                    'font-size: 1.75rem; font-weight: 700; text-align: center; '
                    'color: #111827; margin-bottom: 0.5rem; width: 100%;'
                )

            for item in step_items:
                self._render_questionnaire_item(item)

        self._refresh_conditionals()

        with self.nav_mount:
            if is_first:
                ui.button('Cancelar', on_click=self._on_cancel).props(
                    'outline color=grey-8'
                ).style('min-width: 120px; height: 45px;')
            else:
                ui.button('Anterior', on_click=self._go_previous).props(
                    'outline color=grey-8 icon=arrow_back'
                ).style('min-width: 120px; height: 45px;')

            if is_last:
                self.submit_button = ui.button(
                    'Enviar Respostas', on_click=self._on_submit
                ).props('color=primary icon=send').style('min-width: 150px; height: 45px;')
            else:
                ui.button('Próximo', on_click=self._go_next).props(
                    'color=primary icon-right=arrow_forward'
                ).style('min-width: 120px; height: 45px;')

    def _go_next(self):
        is_valid, error_message = self._validate_step(self.current_step_index)
        if not is_valid:
            ui.notify(error_message, type='warning')
            return

        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            self._save_progress()
            self._render_current_step()
            ui.run_javascript('window.scrollTo(0, 0)')

    def _go_previous(self):
        if self.current_step_index > 0:
            self.current_step_index -= 1
            self._save_progress()
            self._render_current_step()
            ui.run_javascript('window.scrollTo(0, 0)')

    # ─── Conditional questions ──────────────────────────────────────────────────

    def _question_visible(self, question) -> bool:
        """A question with a display condition is only shown/required when the
        trigger option of the question it depends on is selected."""
        depends_qid = question.get('depends_on_question_id')
        depends_oid = question.get('depends_on_option_id')
        if not depends_qid or not depends_oid:
            return True
        selected = self.answers.get(depends_qid, {}).get('selected_options') or []
        return depends_oid in selected

    def _refresh_conditionals(self):
        # The answer of a hidden question is kept in `self.answers` so it
        # reappears when the trigger is re-selected (the widget keeps showing
        # it either way); hidden questions are filtered out at submit time.
        for refs in self.conditional_children.values():
            for ref in refs:
                ref['container'].set_visibility(self._question_visible(ref['question']))

    def _on_answer_changed(self, question_id):
        if question_id in self.conditional_children:
            self._refresh_conditionals()

    # ─── Item rendering ─────────────────────────────────────────────────────────

    def _render_questionnaire_item(self, item):
        content = item['content']
        is_conditional = (
            item['tipo'] in ('question', 'term')
            and content.get('depends_on_question_id')
            and content.get('depends_on_option_id')
        )

        card = ui.card().style(
            'width: 100%; padding: 2rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);'
        )
        with card:
            if item['tipo'] == 'instruction':
                self._render_instruction(content)
            elif item['tipo'] == 'term':
                self._render_term(content)
            elif item['tipo'] == 'question':
                self._render_question(content)

        if is_conditional:
            trigger_qid = content['depends_on_question_id']
            self.conditional_children.setdefault(trigger_qid, []).append({
                'container': card,
                'question': content,
            })

    def _render_instruction(self, instruction):
        ui.label('Instruções').style(
            'font-size: 1.5rem; font-weight: 700; color: #374151; margin-bottom: 1rem;'
        )
        ui.label(instruction['texto']).style(
            'font-size: 1.1rem; line-height: 1.6; color: #374151;'
        )

    def _render_question(self, question):
        question_id = question['id']
        question_text = question['texto']
        question_type = question['tipo']
        options = question.get('options', [])
        question_caption = question.get('caption', '')
        is_required = question.get('obrigatoria', True)

        if question_caption:
            with ui.row().style('width: 100%; align-items: baseline; gap: 0.5rem; flex-wrap: wrap;'):
                ui.label(f"[{question_caption}]").style(
                    'font-size: 0.9rem; font-weight: 600; color: #6b7280;'
                )
                ui.label(f"{question_text}").style(
                    'font-size: 1.5rem; font-weight: 700; margin-bottom: 1.5rem; color: #111827; line-height: 1.3;'
                )
                if not is_required:
                    ui.label('(opcional)').style(
                        'font-size: 0.9rem; font-weight: 400; color: #9ca3af; font-style: italic;'
                    )
        else:
            with ui.row().style('width: 100%; align-items: baseline; gap: 0.5rem; flex-wrap: wrap;'):
                ui.label(f"{question_text}").style(
                    'font-size: 1.5rem; font-weight: 700; margin-bottom: 1.5rem; color: #111827; line-height: 1.3;'
                )
                if not is_required:
                    ui.label('(opcional)').style(
                        'font-size: 0.9rem; font-weight: 400; color: #9ca3af; font-style: italic;'
                    )

        if question_type == 'single':
            self._render_single_choice(question_id, options)
        elif question_type == 'multiple':
            self._render_multiple_choice(question_id, options)
        elif question_type == 'free_text':
            self._render_text_input(question_id, question_text)

    def _render_term(self, term):
        term_id = term['id']
        term_title = term.get('titulo', '')
        term_text = term.get('texto', '')
        term_type = term.get('tipo', 'single')
        options = term.get('options', [])
        term_caption = term.get('caption', '')

        if term_caption:
            with ui.element('div').style(
                'width: 100%; display: grid; grid-template-columns: auto 1fr; '
                'gap: 0.5rem; align-items: start; margin-bottom: 0.5rem;'
            ):
                ui.label(f"[{term_caption}]").style(
                    'font-size: 0.9rem; font-weight: 600; color: #6b7280; white-space: nowrap;'
                )
                ui.label(term_title).style(
                    'font-size: 1.5rem; font-weight: 700; color: #111827; line-height: 1.3; '
                    'min-width: 0; overflow-wrap: anywhere; word-break: break-word; white-space: normal;'
                )
        else:
            ui.label(term_title).style(
                'font-size: 1.5rem; font-weight: 700; color: #111827; line-height: 1.3; margin-bottom: 0.5rem;'
            )

        if term_text:
            formatted_text = self._format_term_text(term_text)
            with ui.element('div').classes('term-richtext').style(
                'margin-top: 0.5rem; max-height: 40vh; overflow-y: auto; padding-right: 0.5rem; '
                'font-size: 1.1rem; line-height: 1.6; color: #374151; '
                'overflow-wrap: anywhere; word-break: break-word; white-space: normal;'
            ):
                ui.html(formatted_text, sanitize=_passthrough_html)

        if term_type == 'single':
            self._render_single_choice(term_id, options)
        elif term_type == 'multiple':
            self._render_multiple_choice(term_id, options)
        elif term_type == 'free_text':
            self._render_text_input(term_id, term_title or term_text)

    def _format_term_text(self, text: str) -> str:
        if not text:
            return ''

        decoded_text = unescape(text)
        if re.search(r'<\s*\/?\s*[a-zA-Z][^>]*>', decoded_text):
            return decoded_text

        if re.search(r'<(p|ul|ol|li|strong|b|em|br|div|span)[\s>/]', text, re.IGNORECASE):
            return text

        return escape(text).replace('\n', '<br>')

    def _render_single_choice(self, question_id, options):
        option_group = ui.radio(
            options={opt['id']: opt['texto'] for opt in options},
            value=self.answers.get(question_id, {}).get('selected_options', [None])[0]
            if self.answers.get(question_id, {}).get('selected_options') else None
        ).style('width: 100%; font-size: 1rem;')

        def on_option_change(e):
            selected_value = option_group.value
            self.answers[question_id] = {
                'selected_options': [selected_value] if selected_value else [],
                'text_response': None
            }
            self._on_answer_changed(question_id)
            self._save_progress()

        option_group.on('update:model-value', on_option_change)

    def _render_multiple_choice(self, question_id, options):
        current_selections = self.answers.get(question_id, {}).get('selected_options', [])

        with ui.column().style('gap: 0.75rem;'):
            for option in options:
                option_id = option['id']
                option_text = option['texto']

                checkbox = ui.checkbox(
                    text=option_text,
                    value=option_id in current_selections
                ).style('font-size: 1rem;')

                def on_checkbox_change(e, opt_id=option_id, cb=checkbox):
                    checkbox_value = cb.value

                    if question_id not in self.answers:
                        self.answers[question_id] = {'selected_options': [], 'text_response': None}

                    selected_options = self.answers[question_id]['selected_options']

                    if checkbox_value:
                        if opt_id not in selected_options:
                            selected_options.append(opt_id)
                    else:
                        if opt_id in selected_options:
                            selected_options.remove(opt_id)

                    self._on_answer_changed(question_id)
                    self._save_progress()

                checkbox.on('update:model-value', on_checkbox_change)

    def _is_date_of_birth_field(self, question_text: str) -> bool:
        text_lower = (question_text or '').lower()
        has_keyword = 'nascimento' in text_lower
        has_template = '__/__/____' in (question_text or '') or '__ / __ / ____' in (question_text or '')
        return has_keyword or has_template

    def _is_email_field(self, question_text: str) -> bool:
        text_lower = (question_text or '').lower()
        return 'e-mail' in text_lower or 'email' in text_lower

    @staticmethod
    def _is_valid_birth_date(value: str) -> bool:
        """Complete dd/mm/aaaa date, plausible for a birth date (the Quasar
        mask constrains the format but accepts incomplete input like 01/01/01)."""
        value = (value or '').strip()
        if not value:
            return True  # emptiness is handled by the required-field check
        try:
            parsed = datetime.strptime(value, '%d/%m/%Y')
        except ValueError:
            return False
        return 1900 <= parsed.year and parsed.date() <= datetime.now().date()

    @staticmethod
    def _is_valid_email(value: str) -> bool:
        value = (value or '').strip()
        if not value:
            return True  # emptiness is handled by the required-field check
        return bool(EMAIL_RE.match(value))

    def _render_text_input(self, question_id, question_text: str = ''):
        current_text = self.answers.get(question_id, {}).get('text_response') or ''
        self.answers[question_id] = {'selected_options': [], 'text_response': current_text}

        if self._is_date_of_birth_field(question_text):
            self._render_date_input(question_id, current_text)
            return

        if self._is_email_field(question_text):
            self._render_email_input(question_id, current_text)
            return

        max_chars = 1000
        counter_label = None

        def on_text_change(e):
            current_value = e.value if e.value is not None else ''
            length = len(current_value)

            if counter_label is not None:
                counter_label.text = f'{length} / {max_chars}'

                if length > max_chars * 0.9:
                    counter_label.style('color: #dc2626;')
                elif length > max_chars * 0.75:
                    counter_label.style('color: #f59e0b;')
                else:
                    counter_label.style('color: #6b7280;')

            self.answers[question_id]['text_response'] = current_value
            self._save_progress()

        with ui.column().style('width: 100%; gap: 0.5rem;'):
            ui.textarea(
                placeholder='Digite sua resposta aqui...',
                value=current_text,
                on_change=on_text_change
            ).props(f'rows=6 maxlength={max_chars} autogrow').style(
                'width: 100%; font-size: 1rem; padding: 0.75rem; '
                'border: 2px solid #d1d5db; border-radius: 0.5rem; resize: vertical;'
            )

            counter_label = ui.label(f'{len(current_text)} / {max_chars}').style(
                'font-size: 0.75rem; color: #6b7280; text-align: right; margin-top: 0.25rem;'
            )

    def _render_date_input(self, question_id, current_text: str):
        def on_text_change(e):
            current_value = e.value if e.value is not None else ''
            self.answers[question_id]['text_response'] = current_value
            self._save_progress()

        with ui.column().style('width: 100%; gap: 0.5rem;'):
            ui.input(
                placeholder='__/__/____',
                value=current_text,
                on_change=on_text_change,
                validation={
                    'Data incompleta ou inválida — use dia/mês/ano com 4 dígitos (ex.: 05/03/1990)':
                        self._is_valid_birth_date,
                }
            ).props('mask="##/##/####" inputmode=numeric').style(
                'width: 100%; font-size: 1rem; padding: 0.75rem; '
                'border: 2px solid #d1d5db; border-radius: 0.5rem;'
            )

    def _render_email_input(self, question_id, current_text: str):
        def on_text_change(e):
            current_value = e.value if e.value is not None else ''
            self.answers[question_id]['text_response'] = current_value
            self._save_progress()

        with ui.column().style('width: 100%; gap: 0.5rem;'):
            ui.input(
                placeholder='nome@exemplo.com',
                value=current_text,
                on_change=on_text_change,
                validation={
                    'Informe um e-mail válido (ex.: nome@exemplo.com)':
                        self._is_valid_email,
                }
            ).props('type=email inputmode=email autocomplete=email').style(
                'width: 100%; font-size: 1rem; padding: 0.75rem; '
                'border: 2px solid #d1d5db; border-radius: 0.5rem;'
            )

    # ─── Validation ─────────────────────────────────────────────────────────────

    def _validate_items(self, items) -> tuple[bool, str]:
        for item in items:
            if item['tipo'] in ('question', 'term'):
                question = item['content']
                question_id = question['id']
                question_text = question.get('titulo') or question.get('texto')
                is_required = question.get('obrigatoria', True)

                if not self._question_visible(question):
                    continue

                if question_id not in self.answers:
                    if is_required:
                        return False, f'Por favor, responda a pergunta: "{question_text}"'
                    continue

                answer = self.answers[question_id]

                if question['tipo'] in ['single', 'multiple']:
                    if not answer.get('selected_options') and is_required:
                        return False, f'Por favor, selecione uma opção para: "{question_text}"'
                elif question['tipo'] == 'free_text':
                    text_value = (answer.get('text_response') or '').strip()
                    if is_required and not text_value:
                        return False, f'Por favor, preencha o campo de texto: "{question_text}"'
                    if text_value:
                        if self._is_date_of_birth_field(question_text) and not self._is_valid_birth_date(text_value):
                            return False, (
                                f'Data inválida em "{question_text}". '
                                'Use dia/mês/ano com 4 dígitos (ex.: 05/03/1990).'
                            )
                        if self._is_email_field(question_text) and not self._is_valid_email(text_value):
                            return False, f'E-mail inválido em "{question_text}". Ex.: nome@exemplo.com'

        return True, ''

    def _validate_step(self, step_index) -> tuple[bool, str]:
        _, _, items = self.steps[step_index]
        return self._validate_items(items)

    def _validate_answers(self) -> tuple[bool, str]:
        for i in range(len(self.steps)):
            is_valid, message = self._validate_step(i)
            if not is_valid:
                return is_valid, message
        return True, ''

    # ─── Submission ─────────────────────────────────────────────────────────────

    def _on_submit(self):
        if self.loading:
            return

        is_valid, error_message = self._validate_answers()
        if not is_valid:
            ui.notify(error_message, type='warning')
            return

        if not hasattr(self, 'real_questionnaire_id') or not self.real_questionnaire_id:
            ui.notify("Erro: ID do questionário não encontrado", type='negative')
            return

        try:
            answers_data = []
            for question_id_str, answer_data in self.answers.items():
                try:
                    question_id = int(question_id_str)

                    question = self.questions_by_id.get(question_id)
                    if question and not self._question_visible(question):
                        continue

                    selected_options = answer_data.get('selected_options', [])

                    if selected_options:
                        selected_options = [int(opt) for opt in selected_options if str(opt).isdigit()]

                    processed_answer = {
                        "question_id": question_id,
                        "selected_options": selected_options,
                        "text_response": answer_data.get('text_response') or None
                    }

                    answers_data.append(processed_answer)
                except (ValueError, TypeError) as e:
                    ui.notify(f"Erro ao processar resposta da pergunta {question_id_str}: {str(e)}", type='negative')
                    return

            if not answers_data:
                ui.notify("Nenhuma resposta válida encontrada", type='negative')
                return

            submission_data = {
                "questionnaire_id": int(self.real_questionnaire_id),
                "answers": answers_data
            }

            print(f"DEBUG: Enviando dados validados: {submission_data}")

            self.loading = True
            self.submit_button.props('loading=true')
            self.submit_button.text = "Enviando..."

            response = response_service.submit_response(submission_data)

            if response and response.get('success'):
                self._clear_progress()
                ui.notify("Respostas enviadas com sucesso!", type='positive')
                self._render_success(response.get('data'))
            else:
                error_msg = response.get('message') if response else "Erro desconhecido"
                ui.notify(f"Erro ao enviar respostas: {error_msg}", type='negative')

        except Exception as e:
            ui.notify(f"Erro ao enviar respostas: {str(e)}", type='negative')
        finally:
            self.loading = False
            if hasattr(self, 'submit_button'):
                self.submit_button.props('loading=false')
                self.submit_button.text = "Enviar Respostas"

    def _render_success(self, submission_response):
        self.main_container.clear()

        with self.main_container:
            with ui.element('div').style(
                'display: flex; '
                'justify-content: center; '
                'align-items: center; '
                'min-height: 70vh; '
                'width: 100%;'
            ):
                with ui.card().style(
                    'padding: 3rem; '
                    'text-align: center; '
                    'width: 100%;'
                ):
                    ui.icon('check_circle', size='5rem', color='green')

                    ui.label('Respostas Enviadas com Sucesso!').style(
                        'font-size: 2rem; font-weight: 700; color: #059669; margin: 1.5rem 0;'
                    )

                    ui.label('Obrigado por participar.').style(
                        'font-size: 1.1rem; color: #6b7280; margin-bottom: 1.5rem;'
                    )

    def _on_cancel(self):
        ui.navigate.to('/')

    def _render_error(self, error_message):
        with ui.element('div').style(
                'display: flex; '
                'justify-content: center; '
                'align-items: center; '
                'min-height: 70vh; '
                'width: 100%;'
            ):
                with ui.column().style(
                    'text-align: center; '
                    'align-items: center; '
                    'width: 100%;'
                ):
                    ui.icon('error', size='5rem', color='red')

                    ui.label('Erro').style(
                        'font-size: 2rem; font-weight: 700; color: #dc2626; margin: 1.5rem 0;'
                    )

                    ui.label(error_message).style(
                        'font-size: 1.1rem; color: #6b7280; margin-bottom: 2rem;'
                    )


def questionnaire_answer_page(questionnaire_id: str):
    page = QuestionnaireAnswerPage(questionnaire_id)
    page.render()
