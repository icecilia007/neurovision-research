from nicegui import ui
import uuid


class QuestionComponent:
    def __init__(self, item_data, on_update_callback=None):
        self.item_data = item_data
        self.on_update_callback = on_update_callback
        self.uid = item_data['_uid']

        self.main_container = None
        self.options_container = None
        self.text_area = None
        self.tipo_select = None
        self.peso_input = None

        self._updating_options = False

    def create_ui(self, parent_container):
        self.main_container = ui.column().style('width: 100%;')

        with self.main_container:
            self.text_area = ui.textarea(
                label='Texto da pergunta',
                value=self.item_data.get('texto', ''),
                placeholder='Digite o enunciado...'
            ).style('width: 100%; max-width: 100%;').props('autogrow rows=2 maxlength=4000 clear-icon')
            self.text_area.on('input', self._on_text_change)

            controls_row = ui.row().style('width: 100%; gap: 1rem;')
            with controls_row:
                self.tipo_select = ui.select(
                    options={
                        'single': 'Seleção única',
                        'multiple': 'Múltipla seleção',
                        'free_text': 'Texto livre'
                    },
                    label='Tipo',
                    value=self.item_data.get('tipo', 'single')
                ).style('min-width: 220px;')
                self.tipo_select.on('change', self._on_tipo_change)

                self.peso_input = ui.number(
                    label='Peso da pergunta',
                    value=self.item_data.get('peso', 1.0),
                    min=0, max=100, step=0.1
                ).style('min-width: 180px;')
                self.peso_input.on('change', self._on_peso_change)

            self.options_container = ui.column().style('width: 100%; margin-top: 0.5rem;')

            self._update_options_display()

        self.main_container.move(parent_container)

    def _on_text_change(self, e):
        if not self._updating_options:
            new_value = getattr(e, 'value', None)
            if new_value is None:
                new_value = getattr(e, 'args', None)
            if new_value is None:
                new_value = self.text_area.value or ''
            self.item_data['texto'] = new_value
            if self.on_update_callback:
                self.on_update_callback('text_changed', self.uid, new_value)

    def _on_tipo_change(self, e):
        if not self._updating_options:
            new_tipo = self.tipo_select.value
            self.item_data['tipo'] = new_tipo
            if new_tipo == 'free_text':
                self.item_data['options'] = []
            self._update_options_display()
            if self.on_update_callback:
                self.on_update_callback('tipo_changed', self.uid, new_tipo)

    def _on_peso_change(self, e):
        if not self._updating_options:
            try:
                peso = float(self.peso_input.value) if self.peso_input.value not in (None, '') else 1.0
            except:
                peso = 1.0
            self.item_data['peso'] = peso
            if self.on_update_callback:
                self.on_update_callback('peso_changed', self.uid, peso)

    def _update_options_display(self):
        if not self.options_container:
            return

        self._updating_options = True

        self.options_container.clear()

        tipo = self.item_data.get('tipo', 'single')

        if tipo in ('single', 'multiple'):
            with self.options_container:
                options_header = ui.row().style('width: 100%; justify-content: space-between; align-items: center;')
                with options_header:
                    ui.label('Opções').style('font-weight: 600;')
                    ui.button('Adicionar opção', on_click=self._add_option).props('flat color=primary')

                options = sorted(self.item_data.get('options', []), key=lambda o: o.get('ordem', 9999))
                for idx, opt in enumerate(options, start=1):
                    self._render_single_option(opt, idx)

        self._updating_options = False

    def _render_single_option(self, opt, visual_idx):
        with self.options_container:
            with ui.card().style('width: 100%; padding: 0.75rem;'):
                with ui.row().style('width: 100%; gap: 0.75rem; align-items: end;'):
                    opt_text = ui.input(
                        label=f'Opção {visual_idx} - texto',
                        value=opt.get('texto', '')
                    ).style('flex: 1; min-width: 180px;')
                    opt_text.on('input', lambda e, idx=visual_idx: self._on_option_text_change(idx, e.value))

                    opt_order = ui.number(
                        label='Ordem',
                        value=opt.get('ordem', visual_idx),
                        min=1, step=1
                    ).style('width: 110px;')
                    opt_order.on('change', lambda e, idx=visual_idx: self._on_option_order_change(idx, e.value))

                    opt_correct = ui.switch('Correta', value=opt.get('is_correct', False))
                    opt_correct.on('update:model-value',
                                   lambda e, idx=visual_idx: self._on_option_correct_change(idx, e.value))

                    opt_weight = ui.number(
                        label='Peso',
                        value=opt.get('peso', 0.0),
                        min=0, max=100, step=0.1
                    ).style('width: 130px;')
                    opt_weight.on('change', lambda e, idx=visual_idx: self._on_option_weight_change(idx, e.value))

                    ui.button('Remover', on_click=lambda idx=visual_idx: self._remove_option(idx)).props(
                        'flat color=negative')

    def _on_option_text_change(self, visual_idx, text):
        if not self._updating_options:
            options = sorted(self.item_data.get('options', []), key=lambda o: o.get('ordem', 9999))
            if 1 <= visual_idx <= len(options):
                options[visual_idx - 1]['texto'] = text or ''

                if self.on_update_callback:
                    self.on_update_callback('option_text_changed', self.uid, visual_idx, text)

    def _on_option_order_change(self, visual_idx, order):
        if not self._updating_options:
            options = sorted(self.item_data.get('options', []), key=lambda o: o.get('ordem', 9999))
            if 1 <= visual_idx <= len(options):
                try:
                    options[visual_idx - 1]['ordem'] = int(order) if order not in (None, '') else visual_idx
                except:
                    options[visual_idx - 1]['ordem'] = visual_idx

                if self.on_update_callback:
                    self.on_update_callback('option_order_changed', self.uid, visual_idx, order)

    def _on_option_correct_change(self, visual_idx, is_correct):
        if not self._updating_options:
            options = sorted(self.item_data.get('options', []), key=lambda o: o.get('ordem', 9999))
            if 1 <= visual_idx <= len(options):
                options[visual_idx - 1]['is_correct'] = bool(is_correct)

                if self.on_update_callback:
                    self.on_update_callback('option_correct_changed', self.uid, visual_idx, is_correct)

    def _on_option_weight_change(self, visual_idx, weight):
        if not self._updating_options:
            options = sorted(self.item_data.get('options', []), key=lambda o: o.get('ordem', 9999))
            if 1 <= visual_idx <= len(options):
                try:
                    options[visual_idx - 1]['peso'] = float(weight) if weight not in (None, '') else 0.0
                except:
                    options[visual_idx - 1]['peso'] = 0.0

                if self.on_update_callback:
                    self.on_update_callback('option_weight_changed', self.uid, visual_idx, weight)

    def _add_option(self):
        if not self._updating_options:
            options = self.item_data.setdefault('options', [])
            next_order = len(options) + 1

            new_option = {
                'texto': '',
                'ordem': next_order,
                'is_correct': False,
                'peso': 0.0
            }

            options.append(new_option)

            self._update_options_display()

            if self.on_update_callback:
                self.on_update_callback('option_added', self.uid, next_order)

    def _remove_option(self, visual_idx):
        if not self._updating_options:
            options = sorted(self.item_data.get('options', []), key=lambda o: o.get('ordem', 9999))

            if 1 <= visual_idx <= len(options):
                del options[visual_idx - 1]

                for i, opt in enumerate(options, 1):
                    opt['ordem'] = i

                self.item_data['options'] = options

                self._update_options_display()

                if self.on_update_callback:
                    self.on_update_callback('option_removed', self.uid, visual_idx)

    def update_header_order(self, new_order):
        self.item_data['ordem'] = new_order

    def get_data(self):
        return self.item_data.copy()

    def set_data(self, new_data):
        self.item_data.update(new_data)

        if self.text_area:
            self.text_area.value = self.item_data.get('texto', '')
        if self.tipo_select:
            self.tipo_select.value = self.item_data.get('tipo', 'single')
        if self.peso_input:
            self.peso_input.value = self.item_data.get('peso', 1.0)

        self._update_options_display()
