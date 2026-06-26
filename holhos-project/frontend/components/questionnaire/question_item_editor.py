from nicegui import ui
from components.questionnaire.sortable_column import SortableColumn

TEXTAREA_PROPS = 'autogrow clear-icon'
TEXTAREA_STYLE = 'width: 100%; max-width: 100%;'

QUESTION_TYPES = {
    'single': 'Seleção única',
    'multiple': 'Múltipla seleção',
    'free_text': 'Texto livre',
}


def _fresh_value(e, widget, default=''):
    """Return the up-to-date value for `widget`. If the event `e` fired from
    `widget`, prefer the value carried by the event (avoids the stale-value
    issue where `widget.value` hasn't been synced yet on `input` events)."""
    if widget is None:
        return default
    if e is not None and getattr(e, 'sender', None) is widget:
        val = getattr(e, 'value', None)
        if val is None:
            val = getattr(e, 'args', None)
        if val is not None:
            return val
    return widget.value if widget.value is not None else default


class QuestionItemEditor:
    def __init__(self, item_data: dict, on_remove=None, on_change=None, get_siblings=None):
        self.item_data = item_data
        self.on_remove = on_remove
        self.on_change = on_change
        # Callback that returns the questionnaire's current item list, so the
        # condition selects can offer the other questions as triggers.
        self.get_siblings = get_siblings
        self.item_type_select = None
        self.i_text = None
        self.q_text = None
        self.t_title = None
        self.t_text = None
        self.q_type_select = None
        self.q_required = None
        self.q_weight = None
        self.q_caption = None
        self.q_step = None
        self.cond_trigger_select = None
        self.cond_option_select = None
        self.options_container = None
        self._is_rendering = False
        self._option_ui_refs = {}

    def _extract_editor_content(self, event=None) -> str:
        # NiceGUI editor payload can vary by version (string, dict-like payload, or component value).
        if event is not None and hasattr(event, 'value') and isinstance(event.value, str):
            return event.value

        if self.t_text is None:
            return ''

        value = self.t_text.value
        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            for key in ('html', 'content', 'text'):
                payload = value.get(key)
                if isinstance(payload, str):
                    return payload

        return str(value) if value is not None else ''

    def render(self):
        with ui.card().style('width: 100%; border-radius: 12px; padding: 1rem;'):
           with ui.row().style('width: 100%; align-items: center; justify-content: space-between;'):
            with ui.row().style('align-items: center; gap: 0.5rem;'):
                ui.icon('drag_indicator').classes('drag-handle cursor-move').style('color: #9ca3af;')
                item_type = self.item_data.get('item_type', 'question')
                if item_type == 'instruction':
                    item_label = 'Instrução'
                elif item_type == 'term':
                    item_label = 'Termo'
                else:
                    item_label = 'Pergunta'
                ui.label(f'{item_label} #{self.item_data.get("ordem", 0)}').style('font-weight: 700; color: #111827;')
            ui.button('Remover', on_click=self._remove).props('flat color=negative icon=delete')

            self.body = ui.column().style('width: 100%; gap: 0.75rem;')
            self._render_body()

    def _render_body(self):
        self.body.clear()
        itype = self.item_data.get('item_type', 'question')

        if itype == 'instruction':
            with self.body:
                self.i_text = ui.textarea(
                    label='Texto da instrução',
                    value=self.item_data.get('texto', ''),
                    placeholder='Escreva a orientação ao respondente...',
                ).style(TEXTAREA_STYLE).props(TEXTAREA_PROPS).props('rows=2 maxlength=4000')
                self.i_text.on('input', self._sync_instruction)

                self._render_step_input()
        elif itype == 'term':
            with self.body:
                self.q_caption = ui.input(
                    label='Código/Identificador (opcional)',
                    value=self.item_data.get('caption', ''),
                    placeholder='Ex: T1, TERM-01, COD-TERMO'
                ).style('width: 100%; margin-bottom: 0.5rem;').props('maxlength=50')
                self.q_caption.on('input', self._sync_term_meta)

                self.t_title = ui.input(
                    label='Título do termo',
                    value=self.item_data.get('titulo', ''),
                    placeholder='Digite o título do termo...'
                ).style('width: 100%;')
                self.t_title.on('input', self._sync_term_meta)

                ui.label('Texto do termo').style('font-weight: 600; color: #111827;')
                self.t_text = ui.editor(value=self.item_data.get('texto', '')).props(
                    ':toolbar="[['
                    "'left','center','right','justify'],"
                    "['bold','italic','underline'],"
                    "['unordered','ordered','outdent','indent'],"
                    "['undo','redo']"
                    ']"'
                ).style(
                    'width: 100%; min-height: 220px; border: 1px solid #d1d5db; border-radius: 0.5rem;'
                )
                # Sync on blur to avoid cursor reposition issues while typing (especially on Enter).
                self.t_text.on('blur', self._sync_term_meta)

                with ui.row().style('width: 100%; gap: 1rem;'):
                    self.q_type_select = ui.select(
                        options=QUESTION_TYPES,
                        label='Tipo',
                        value=self.item_data.get('tipo', 'single')
                    ).style('min-width: 220px;').on('update:model-value', self._on_question_type_change)

                    self.q_required = ui.switch(
                        'Resposta obrigatória',
                        value=self.item_data.get('obrigatoria', True)
                    ).style('min-width: 220px;').on('update:model-value', self._sync_term_meta)
                    if (self.item_data.get('tipo', 'single') != 'free_text'):
                        self.q_required.disable()

                    self.q_weight = ui.number(
                        label='Peso do termo',
                        value=self.item_data.get('peso', 1.0),
                        min=0, max=100, step=0.1
                    ).style('min-width: 180px;').on('change', self._sync_term_meta)

                self._render_step_input()

                self.options_container = ui.column().style('width: 100%; gap: 0.5rem;')
                self._render_options()
        else:
            with self.body:
                self.q_caption = ui.input(
                    label='Código/Identificador (opcional)',
                    value=self.item_data.get('caption', ''),
                    placeholder='Ex: Q1, P01, COD-001'
                ).style('width: 100%; margin-bottom: 0.5rem;').props('maxlength=50')
                self.q_caption.on('input', self._sync_question_meta)

                self.q_text = ui.textarea(
                    label='Texto da pergunta',
                    value=self.item_data.get('texto', ''),
                    placeholder='Digite o enunciado...',
                ).style(TEXTAREA_STYLE).props(TEXTAREA_PROPS).props('rows=2 maxlength=4000')
                self.q_text.on('input', self._sync_question_meta)

                with ui.row().style('width: 100%; gap: 1rem;'):
                    self.q_type_select = ui.select(
                        options=QUESTION_TYPES,
                        label='Tipo',
                        value=self.item_data.get('tipo', 'single')
                    ).style('min-width: 220px;').on('update:model-value', self._on_question_type_change)

                    self.q_required = ui.switch(
                        'Resposta obrigatória',
                        value=self.item_data.get('obrigatoria', True)
                    ).style('min-width: 220px;').on('update:model-value', self._sync_question_meta)
                    if (self.item_data.get('tipo', 'single') != 'free_text'):
                        self.q_required.disable()

                    self.q_weight = ui.number(
                        label='Peso da pergunta',
                        value=self.item_data.get('peso', 1.0),
                        min=0, max=100, step=0.1
                    ).style('min-width: 180px;').on('change', self._sync_question_meta)

                self._render_step_input()
                self._render_condition_section()

                self.options_container = ui.column().style('width: 100%; gap: 0.5rem;')
                self._render_options()

    def _render_step_input(self):
        self.q_step = ui.number(
            label='Etapa',
            value=self.item_data.get('step', 1) or 1,
            min=1, max=20, step=1
        ).style('min-width: 120px; max-width: 160px;')

        def sync_step():
            if self._is_rendering:
                return
            try:
                self.item_data['step'] = max(1, int(self.q_step.value or 1))
            except Exception:
                self.item_data['step'] = 1
            self._notify_change()

        self.q_step.on('change', sync_step)

    def _condition_trigger_options(self) -> dict:
        """Other single/multiple items of the questionnaire that can act as the
        condition trigger for this question."""
        siblings = self.get_siblings() if self.get_siblings else []
        options = {None: '— Sempre exibir —'}
        for sib in siblings:
            if sib.get('_uid') == self.item_data.get('_uid'):
                continue
            if sib.get('item_type') not in ('question', 'term'):
                continue
            if sib.get('tipo') not in ('single', 'multiple'):
                continue
            label = sib.get('caption') or sib.get('titulo') or sib.get('texto') or ''
            label = label.strip()[:60] or f'Item #{sib.get("ordem", "?")}'
            options[sib['_uid']] = label
        return options

    def _condition_option_choices(self, trigger_uid) -> dict:
        siblings = self.get_siblings() if self.get_siblings else []
        for sib in siblings:
            if sib.get('_uid') == trigger_uid:
                return {
                    opt.get('ordem'): (opt.get('texto') or f'Opção {opt.get("ordem")}')
                    for opt in sib.get('options', [])
                }
        return {}

    def _render_condition_section(self):
        with ui.expansion('Condição de exibição (opcional)').classes('w-full').style(
            'border: 1px solid #e5e7eb; border-radius: 0.5rem;'
        ):
            ui.label(
                'Exibir esta pergunta somente quando determinada opção '
                'de outra pergunta for selecionada.'
            ).style('font-size: 0.85rem; color: #6b7280;')

            # NiceGUI 3.x raises ValueError when a select is built with a value
            # that is not among its options, so stale references (trigger
            # removed or changed to free_text) must be discarded before render.
            trigger_options = self._condition_trigger_options()
            if self.item_data.get('depends_on_uid') not in trigger_options:
                self.item_data['depends_on_uid'] = None
                self.item_data['depends_on_option_ordem'] = None

            option_choices = self._condition_option_choices(self.item_data.get('depends_on_uid'))
            if self.item_data.get('depends_on_option_ordem') not in option_choices:
                self.item_data['depends_on_option_ordem'] = None

            with ui.row().style('width: 100%; gap: 1rem; align-items: flex-end; flex-wrap: wrap;'):
                self.cond_trigger_select = ui.select(
                    options=trigger_options,
                    label='Depende da pergunta',
                    value=self.item_data.get('depends_on_uid')
                ).style('flex: 1 1 220px; min-width: 0;')

                self.cond_option_select = ui.select(
                    options=option_choices,
                    label='Quando a opção for',
                    value=self.item_data.get('depends_on_option_ordem')
                ).style('flex: 1 1 220px; min-width: 0;')

                ui.button(icon='refresh', on_click=self._refresh_condition_options).props(
                    'flat dense color=grey-7'
                ).tooltip('Atualizar lista de perguntas')

            def sync_trigger():
                if self._is_rendering:
                    return
                self.item_data['depends_on_uid'] = self.cond_trigger_select.value
                self.item_data['depends_on_option_ordem'] = None
                self.cond_option_select.set_options(
                    self._condition_option_choices(self.cond_trigger_select.value)
                )
                self.cond_option_select.set_value(None)
                self._notify_change()

            def sync_option():
                if self._is_rendering:
                    return
                self.item_data['depends_on_option_ordem'] = self.cond_option_select.value
                self._notify_change()

            self.cond_trigger_select.on('update:model-value', sync_trigger)
            self.cond_option_select.on('update:model-value', sync_option)

    def _refresh_condition_options(self):
        if self.cond_trigger_select:
            self.cond_trigger_select.set_options(self._condition_trigger_options())
        if self.cond_option_select:
            self.cond_option_select.set_options(
                self._condition_option_choices(self.item_data.get('depends_on_uid'))
            )

    def _on_question_type_change(self, e=None):
        if getattr(self, '_is_rendering', False):
            return

        self._sync_all_options_data()
        if self.item_data.get('item_type') == 'term':
            self._sync_term_meta()
        else:
            self._sync_question_meta()
        qtype = self.q_type_select.value if self.q_type_select else 'single'

        if qtype == 'free_text':
            self._is_rendering = True
            self.item_data['tipo'] = 'free_text'
            self.item_data['obrigatoria'] = bool(self.item_data.get('obrigatoria', True))
            self.item_data['options'] = []
            self._option_ui_refs.clear()
            if getattr(self, 'options_container', None):
                self.options_container.clear()
            if getattr(self, 'body', None):
                self.body.clear()
            self._render_body()
            self._is_rendering = False
            self._notify_change()
            return

        if not self.item_data.get('options'):
            self.item_data['options'] = [
                {'texto': '', 'ordem': i, 'is_correct': False, 'peso': 0.0}
                for i in range(1, 5)
            ]
        self.item_data['obrigatoria'] = True

        self._render_options()

    def _sync_all_options_data(self):
        for opt_id, ui_refs in self._option_ui_refs.items():
            if ui_refs and len(self.item_data.get('options', [])) > 0:
                try:
                    for opt in self.item_data['options']:
                        if id(opt) == opt_id:
                            if 'text' in ui_refs and ui_refs['text']:
                                opt['texto'] = ui_refs['text'].value or ''
                            if 'correct' in ui_refs and ui_refs['correct']:
                                opt['is_correct'] = bool(ui_refs['correct'].value)
                            if 'weight' in ui_refs and ui_refs['weight']:
                                try:
                                    opt['peso'] = float(ui_refs['weight'].value) if ui_refs['weight'].value not in (None, '') else 0.0
                                except:
                                    pass
                            break
                except:
                    pass

    def _render_options(self):
        
        if not self.options_container:
            return

        self._sync_all_options_data()
        self._is_rendering = True
        self.options_container.clear()
        self._option_ui_refs.clear()

        qtype = self.q_type_select.value if self.q_type_select else 'single'
        self.item_data['tipo'] = qtype

        if qtype == 'free_text':
            with self.options_container:
                ui.label('Item de texto livre (sem opções).').style('color: #6b7280; font-style: italic;')
            self.item_data['options'] = []
            self._notify_change()
            self._is_rendering = False
            return

        with self.options_container:
            ui.separator().style('margin: 0.75rem 0;')
            with ui.row().style('width: 100%; justify-content: space-between; align-items: center;'):
                ui.label('Opções (arraste para reordenar)').style('font-weight: 600;')
                ui.button('Adicionar opção', on_click=self._add_option).props('flat color=primary icon=add')

            sortable = SortableColumn(on_change=self._handle_option_reorder, group='options')
            sortable._classes.append('w-full')
            with sortable:
                self.item_data['options'].sort(key=lambda o: o.get('ordem', 9999))
                for idx, opt in enumerate(self.item_data.get('options', []), start=1):
                    self._option_row(opt, idx)

        self._is_rendering = False

    def _handle_option_reorder(self, e):
        if self._is_rendering:
            return
        
        self._sync_all_options_data()
        old_index = e.args['old_index']
        new_index = e.args['new_index']
        
        if old_index == new_index:
            return
        
        options = self.item_data.get('options', [])
        moved_opt = options.pop(old_index)
        options.insert(new_index, moved_opt)
        
        for i, opt in enumerate(options, 1):
            opt['ordem'] = i
        
        self._notify_change()
        self._render_options()
    def _option_row(self, opt: dict, visual_index: int):
        opt_id = id(opt)

        def sync_text(e=None):
            if not self._is_rendering:
                opt['texto'] = _fresh_value(e, o_text)
                self._notify_change()

        def sync_correct():
            if not self._is_rendering:
                if self.item_data.get('tipo') == 'single' and o_correct.value:
                    for other_opt in self.item_data.get('options', []):
                        if other_opt is not opt:
                            other_opt['is_correct'] = False
                opt['is_correct'] = bool(o_correct.value)
                self._notify_change()
                if self.item_data.get('tipo') == 'single' and o_correct.value:
                    self._render_options()

        def sync_weight():
            if not self._is_rendering:
                try:
                    opt['peso'] = float(o_weight.value) if o_weight.value not in (None, '') else 0.0
                except Exception:
                    opt['peso'] = 0.0
                self._notify_change()

        with ui.card().style('width: 100%; padding: 0.75rem; box-sizing: border-box;'):
            with ui.row().style('width: 100%; gap: 0.75rem; align-items: center; flex-wrap: nowrap;'):
                ui.icon('drag_indicator').classes('drag-handle cursor-move').style('color: #9ca3af;')
                
                o_text = ui.input(
                    label=f'Opção {visual_index}',
                    value=opt.get('texto', '')
                ).style('flex: 1; min-width: 0;')
                o_correct = ui.switch('Correta', value=opt.get('is_correct', False)).style('min-width: 100px;')
                
                o_weight = ui.number(
                    label='Peso',
                    value=opt.get('peso', 0.0),
                    min=0, max=100, step=0.1
                ).style('width: 120px;')
                
                ui.button(icon='delete', on_click=lambda opt_ref=opt: self._remove_option(opt_ref)).props('flat color=negative dense')

        self._option_ui_refs[opt_id] = {
            'text': o_text,
            'correct': o_correct,
            'weight': o_weight
        }

        o_text.on('input', sync_text)
        o_correct.on('update:model-value', sync_correct)
        o_weight.on('change', sync_weight)

    def _add_option(self):
        if self._is_rendering:
            return

        self._sync_all_options_data()

        opts = self.item_data.setdefault('options', [])
        existing_ordens = [o.get('ordem', 0) for o in opts]
        next_ordem = max(existing_ordens, default=0) + 1

        new_option = {
            'texto': '',
            'ordem': next_ordem,
            'is_correct': False,
            'peso': 0.0
        }
        opts.append(new_option)
        self._notify_change()

        self._render_options()

    def _remove_option(self, opt: dict):
        if self._is_rendering:
            return

        self._sync_all_options_data()

        opts = self.item_data.get('options', [])
        if opt in opts:
            opts.remove(opt)

        for i, o in enumerate(opts, start=1):
            o['ordem'] = i

        self._notify_change()
        self._render_options()

    def _sync_instruction(self, e=None):
        if self._is_rendering:
            return
        self.item_data['item_type'] = 'instruction'
        self.item_data['texto'] = _fresh_value(e, self.i_text)
        self._notify_change()

    def _sync_question_meta(self, e=None):
        if self._is_rendering:
            return
        self.item_data['item_type'] = 'question'
        self.item_data['texto'] = _fresh_value(e, self.q_text)
        caption_value = _fresh_value(e, self.q_caption)
        self.item_data['caption'] = caption_value.strip() if caption_value and caption_value.strip() else None
    
        self.item_data['tipo'] = self.q_type_select.value if self.q_type_select else 'single'
        if self.item_data['tipo'] == 'free_text':
            self.item_data['obrigatoria'] = bool(self.q_required.value) if self.q_required else True
        else:
            self.item_data['obrigatoria'] = True
        try:
            self.item_data['peso'] = float(self.q_weight.value) if self.q_weight and self.q_weight.value not in (
            None, '') else 1.0
        except Exception:
            self.item_data['peso'] = 1.0
        self._notify_change()

    def _sync_term_meta(self, e=None):
        if self._is_rendering:
            return
        self.item_data['item_type'] = 'term'
        self.item_data['titulo'] = _fresh_value(e, self.t_title)
        self.item_data['texto'] = self._extract_editor_content(e)
        caption_value = _fresh_value(e, self.q_caption)
        self.item_data['caption'] = caption_value.strip() if caption_value and caption_value.strip() else None

        self.item_data['tipo'] = self.q_type_select.value if self.q_type_select else 'single'
        if self.item_data['tipo'] == 'free_text':
            self.item_data['obrigatoria'] = bool(self.q_required.value) if self.q_required else True
        else:
            self.item_data['obrigatoria'] = True
        try:
            self.item_data['peso'] = float(self.q_weight.value) if self.q_weight and self.q_weight.value not in (
            None, '') else 1.0
        except Exception:
            self.item_data['peso'] = 1.0
        self._notify_change()

    def _remove(self):
        if self.on_remove:
            self.on_remove(self.item_data.get('_uid'))

    def _notify_change(self):
        if self.on_change and not self._is_rendering:
            self.on_change(self.item_data)
