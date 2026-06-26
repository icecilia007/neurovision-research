from nicegui import ui
from utils.session_manager import session_manager
from services.instruction_service import instruction_client
from services.question_service import question_client
from services.questionnaire_service import questionnaire_service
from components.questionnaire.question_item_editor import QuestionItemEditor
from components.questionnaire.sortable_column import SortableColumn
from services.api_client import api_client
import sys
import uuid



ORDER_OPTIONS = {
    'custom': 'Ordem customizada',
    'ascending': 'Ordem crescente',
    'descending': 'Ordem decrescente',
    'random': 'Aleatória'
}


def _new_uid() -> str:
    return uuid.uuid4().hex[:8]


def questionnaire_create_page(on_done=None, on_cancel=None, questionnaire_id=None):
    state = {
        'items': [],
        'title': '',
        'description': '',
        'caption': '',
        'order_value': 'custom',
        'step_labels': [],
        'step_labels_mount': None,
        'item_editors': {},
        'empty_message': None,
        'list_mount': None,
        'title_input': None,
        'desc_input': None,
        'order_select': None,
        'questionnaire_id': questionnaire_id,
        'is_edit': questionnaire_id is not None
    }

    def _check_eligibility():
        if not state['is_edit']:
            return True
        
        eligibility = questionnaire_service.check_eligibility(state['questionnaire_id'])
        if not eligibility or not eligibility.get('eligible'):
            ui.notify('Não é possível editar este questionário, pois ele já possui respostas.', type='warning')
            return False
        return True

    def _load_questionnaire_data():
        data = questionnaire_service.get_questionnaire_for_response(str(state['questionnaire_id']))
        
        if not data:
            ui.notify('Erro ao carregar dados do questionário', type='negative')
            return False
        
        state['title'] = data.get('titulo', '')
        state['description'] = data.get('descricao', '')
        state['order_value'] = data.get('question_order', 'custom')
        state['step_labels'] = list(data.get('step_labels') or [])

        state['items'] = []

        for item in data.get('items', []):
            if item.get('tipo') == 'instruction':
                state['items'].append({
                    '_uid': _new_uid(),
                    'item_type': 'instruction',
                    'item_id': item.get('content', {}).get('id'),
                    'ordem': item.get('ordem', 0),
                    'step': item.get('step', 1) or 1,
                    'texto': item.get('content', {}).get('texto', '')
                })
            elif item.get('tipo') == 'term':
                question_data = item.get('content', {})
                options = []

                for option in question_data.get('options', []):
                    options.append({
                        'option_id': option.get('id'),
                        'texto': option.get('texto', ''),
                        'ordem': option.get('ordem', 0),
                        'is_correct': option.get('is_correct', False),
                        'peso': option.get('peso', 0.0)
                    })

                state['items'].append({
                    '_uid': _new_uid(),
                    'item_type': 'term',
                    'item_id': item.get('content', {}).get('id'),
                    'ordem': item.get('ordem', 0),
                    'step': item.get('step', 1) or 1,
                    'titulo': question_data.get('titulo', ''),
                    'texto': question_data.get('texto', ''),
                    'tipo': question_data.get('tipo', 'single'),
                    'obrigatoria': question_data.get('obrigatoria', True),
                    'caption': question_data.get('caption', ''),
                    'peso': question_data.get('peso', 1.0),
                    'options': options
                })
            else:
                question_data = item.get('content', {})
                options = []

                for option in question_data.get('options', []):
                    options.append({
                        'option_id': option.get('id'),
                        'texto': option.get('texto', ''),
                        'ordem': option.get('ordem', 0),
                        'is_correct': option.get('is_correct', False),
                        'peso': option.get('peso', 0.0)
                    })

                state['items'].append({
                    '_uid': _new_uid(),
                    'item_type': 'question',
                    'item_id': item.get('content', {}).get('id'),
                    'ordem': item.get('ordem', 0),
                    'step': item.get('step', 1) or 1,
                    'texto': question_data.get('texto', ''),
                    'tipo': question_data.get('tipo', 'single'),
                    'obrigatoria': question_data.get('obrigatoria', True),
                    'caption': question_data.get('caption', ''),
                    'peso': question_data.get('peso', 1.0),
                    'depends_on_question_id': question_data.get('depends_on_question_id'),
                    'depends_on_option_id': question_data.get('depends_on_option_id'),
                    'options': options
                })

        # Resolve persisted display conditions (ids) back to editor references
        # (uid of the trigger item + ordem of the trigger option). Instructions
        # live in another table whose ids can collide with question ids, so
        # only question/term items may enter the map.
        id_to_uid = {
            it.get('item_id'): it['_uid']
            for it in state['items']
            if it.get('item_id') and it['item_type'] in ('question', 'term')
        }
        items_by_uid = {it['_uid']: it for it in state['items']}
        for it in state['items']:
            dq = it.pop('depends_on_question_id', None)
            do = it.pop('depends_on_option_id', None)
            if dq and dq in id_to_uid:
                it['depends_on_uid'] = id_to_uid[dq]
                trigger = items_by_uid[id_to_uid[dq]]
                for opt in trigger.get('options', []):
                    if opt.get('option_id') == do:
                        it['depends_on_option_ordem'] = opt.get('ordem')
                        break

        _render_step_labels()

        if state['title_input']:
            state['title_input'].set_value(state['title'])
        if state['desc_input']:
            state['desc_input'].set_value(state['description'])
        if state['order_select']:
            state['order_select'].set_value(state['order_value'])
        
        _update_display()
        return True


    def _render_step_labels():
        mount = state['step_labels_mount']
        if not mount:
            return
        mount.clear()

        with mount:
            ui.label('Etapas do questionário').style('font-weight: 700; color: #111827;')
            ui.label(
                'Defina os nomes das etapas exibidas ao respondente. Cada item abaixo tem '
                'um campo "Etapa" indicando a qual etapa pertence. Com apenas uma etapa, o '
                'questionário é exibido em página única (comportamento padrão).'
            ).style('font-size: 0.85rem; color: #6b7280;')

            for i, label in enumerate(state['step_labels']):
                with ui.row().style('width: 100%; gap: 0.5rem; align-items: center;'):
                    def on_label_change(e, idx=i):
                        state['step_labels'][idx] = e.value or ''

                    ui.input(
                        label=f'Nome da etapa {i + 1}',
                        value=label,
                        on_change=on_label_change
                    ).style('flex: 1; min-width: 0;')

                    def remove_label(idx=i):
                        state['step_labels'].pop(idx)
                        _render_step_labels()

                    ui.button(icon='delete', on_click=remove_label).props('flat color=negative dense')

            def add_label():
                state['step_labels'].append(f'Etapa {len(state["step_labels"]) + 1}')
                _render_step_labels()

            ui.button('Adicionar etapa', on_click=add_label).props('flat color=primary icon=add')

    def _on_title_change(e):
        state['title'] = e.value or '' if hasattr(e, 'value') else state['title_input'].value or ''
        print(f"[DEBUG] Título alterado para: {state['title']}")

    def _on_desc_change(e):
        state['description'] = e.value or '' if hasattr(e, 'value') else state['desc_input'].value or ''
        print(f"[DEBUG] Descrição alterada para: {state['description']}")

    def _on_order_change(e):
        if hasattr(e, 'value'):
            val = e.value
        else:
            val = state['order_select'].value if state['order_select'] else 'custom'

        print(f"[DEBUG] Evento de mudança de ordem disparado. Valor recebido: {val}")

        if val in ORDER_OPTIONS:
            state['order_value'] = val
            print(f"[DEBUG] Ordem atualizada para: {state['order_value']}")
        else:
            state['order_value'] = 'custom'
            print(f"[DEBUG] Valor inválido '{val}', definindo como 'custom'")

        if state['order_select'] and state['order_select'].value != state['order_value']:
            print(f"[DEBUG] Sincronizando select: {state['order_select'].value} -> {state['order_value']}")
            state['order_select'].value = state['order_value']

    def _sync_form_data():
        if state['title_input']:
            state['title'] = state['title_input'].value or ''
        if state['desc_input']:
            state['description'] = state['desc_input'].value or ''
        if state['order_select']:
            val = state['order_select'].value
            state['order_value'] = val if val in ORDER_OPTIONS else 'custom'

        print(
            f"[DEBUG] Dados sincronizados - Título: '{state['title']}', Ordem: '{state['order_value']}', Descrição: '{state['description']}'")

    def _sync_all_editors_data():
        for uid, editor in state['item_editors'].items():
            try:
                if hasattr(editor, '_sync_all_options_data'):
                    editor._sync_all_options_data()
                if editor.item_data.get('item_type') == 'term' and hasattr(editor, '_sync_term_meta'):
                    editor._sync_term_meta()
                elif hasattr(editor, 'q_text') and editor.q_text:
                    editor.item_data['texto'] = editor.q_text.value or ''
                elif hasattr(editor, 'i_text') and editor.i_text:
                    editor.item_data['texto'] = editor.i_text.value or ''
                if hasattr(editor, 't_title') and editor.t_title:
                    editor.item_data['titulo'] = editor.t_title.value or ''
                if hasattr(editor, 'q_caption') and editor.q_caption:
                    editor.item_data['caption'] = editor.q_caption.value or ''
                if hasattr(editor, 'q_type_select') and editor.q_type_select:
                    editor.item_data['tipo'] = editor.q_type_select.value
                if hasattr(editor, 'q_required') and editor.q_required:
                    editor.item_data['obrigatoria'] = bool(editor.q_required.value)
                if hasattr(editor, 'q_weight') and editor.q_weight:
                    try:
                        editor.item_data['peso'] = float(editor.q_weight.value)

                    except Exception as e:
                        pass

                for i, item in enumerate(state['items']):
                    if item['_uid'] == editor.item_data['_uid']:
                        if state['is_edit']:
                            item_id_backup = item.get('item_id')
                        
                        state['items'][i] = editor.item_data.copy()
                        
                        if state['is_edit']:
                            state['items'][i]['item_id'] = item_id_backup
                        break
            except Exception as e:
                print(f"Error syncing editor {uid}: {e}")

    def _show_empty_message():
        if len(state['items']) == 0:
            with state['list_mount']:
                state['empty_message'] = ui.label('Nenhum item adicionado. Use os botões acima.').style('color:#6b7280;')

    def _hide_empty_message():
        if state['empty_message']:
            state['empty_message'].delete()
            state['empty_message'] = None

    def _add_instruction():
        _sync_all_editors_data()
        new_item = {
            '_uid': _new_uid(),
            'item_type': 'instruction',
            'ordem': len(state['items']) + 1,
            'step': 1,
            'texto': ''
        }
        state['items'].append(new_item)
        if len(state['items']) == 1:
            _hide_empty_message()
        _create_item_editor(new_item)

    def _add_question():
        _sync_all_editors_data()
        new_item = {
            '_uid': _new_uid(),
            'item_type': 'question',
            'ordem': len(state['items']) + 1,
            'step': 1,
            'texto': '',
            'tipo': 'single',
            'obrigatoria': True,
            'peso': 1.0,
            'options': [
                {
                    'texto': '',
                    'ordem': 1,
                    'is_correct': False,
                    'peso': 0.0
                },
                {
                    'texto': '',
                    'ordem': 2,
                    'is_correct': False,
                    'peso': 0.0
                },
                {
                    'texto': '',
                    'ordem': 3,
                    'is_correct': False,
                    'peso': 0.0
                },
                {
                    'texto': '',
                    'ordem': 4,
                    'is_correct': False,
                    'peso': 0.0
                }
            ]
        }
        state['items'].append(new_item)
        if len(state['items']) == 1:
            _hide_empty_message()
        _create_item_editor(new_item)

    def _add_term():
        _sync_all_editors_data()
        new_item = {
            '_uid': _new_uid(),
            'item_type': 'term',
            'ordem': len(state['items']) + 1,
            'step': 1,
            'titulo': '',
            'texto': '',
            'tipo': 'single',
            'obrigatoria': True,
            'peso': 1.0,
            'options': [
                {
                    'texto': '',
                    'ordem': 1,
                    'is_correct': False,
                    'peso': 0.0
                },
                {
                    'texto': '',
                    'ordem': 2,
                    'is_correct': False,
                    'peso': 0.0
                },
                {
                    'texto': '',
                    'ordem': 3,
                    'is_correct': False,
                    'peso': 0.0
                },
                {
                    'texto': '',
                    'ordem': 4,
                    'is_correct': False,
                    'peso': 0.0
                }
            ]
        }
        state['items'].append(new_item)
        if len(state['items']) == 1:
            _hide_empty_message()
        _create_item_editor(new_item)

    def _create_item_editor(item_data):
        with state['list_mount']:
            editor = QuestionItemEditor(
                item_data=item_data,
                on_remove=_remove_item,
                on_change=_on_item_change,
                get_siblings=lambda: state['items']
            )
            editor.render()
            state['item_editors'][item_data['_uid']] = editor

    def _remove_item(uid):
        print(f"Removing item with uid: {uid}")
        _sync_all_editors_data()
        original_count = len(state['items'])
        state['items'] = [item for item in state['items'] if item['_uid'] != uid]
        new_count = len(state['items'])
        print(f"Items after removal: {new_count}")
        _update_display()

    def _update_display():
        print(f"Updating display with {len(state['items'])} items")
        state['item_editors'].clear()
        
        if hasattr(state['list_mount'], 'clear'):
            state['list_mount'].clear()
        
        state['empty_message'] = None

        for i, item in enumerate(state['items'], 1):
            item['ordem'] = i

        if len(state['items']) == 0:
            _show_empty_message()
        else:
            for item in state['items']:
                _create_item_editor(item)


    def _on_item_change(item_data):
        for i, item in enumerate(state['items']):
            if item['_uid'] == item_data['_uid']:
                if state['is_edit'] and item.get('item_id'):
                    item_data['item_id'] = item['item_id']
                
                state['items'][i] = item_data
                break

    def _validate():
        _sync_all_editors_data()
        _sync_form_data()

        if not state['title'].strip():
            return False, 'Título é obrigatório'

        if not state['items']:
            return False, 'Adicione pelo menos um item'

        for item in state['items']:
            if item['item_type'] == 'instruction':
                if not item['texto'].strip():
                    return False, f'Instrução #{item["ordem"]} sem texto'
            else:
                if item['item_type'] == 'term':
                    if not item.get('titulo', '').strip():
                        return False, f'Termo #{item["ordem"]} sem título'
                    if not item['texto'].strip():
                        return False, f'Termo #{item["ordem"]} sem texto'
                else:
                    if not item['texto'].strip():
                        return False, f'Pergunta #{item["ordem"]} sem texto'
                
                label = 'Termo' if item['item_type'] == 'term' else 'Pergunta'

                if item['tipo'] in ('single', 'multiple'):
                    if not item.get('options'):
                        return False, f'{label} #{item["ordem"]} precisa de ao menos 1 opção'
                    
                    for opt in item['options']:
                        if not opt['texto'].strip():
                            return False, f'{label} #{item["ordem"]}: opção sem texto'
                    
                    correct_options = [opt for opt in item['options'] if opt.get('is_correct', False)]
                    
                    if item['tipo'] == 'single':
                        if len(correct_options) == 0:
                            return False, f'{label} #{item["ordem"]} (seleção única) precisa ter exatamente 1 opção marcada como correta'
                        elif len(correct_options) > 1:
                            return False, f'{label} #{item["ordem"]} está marcada como seleção única, mas tem {len(correct_options)} opções corretas. Apenas 1 opção pode ser marcada'
                    
                    if item['tipo'] == 'multiple':
                        if len(correct_options) == 0:
                            return False, f'{label} #{item["ordem"]} (múltipla seleção) precisa ter ao menos 1 opção marcada como correta'

        return True, ''

    def _save_display_conditions(uid_to_question_id):
        """Second pass after all questions exist: resolve editor references
        (trigger uid + option ordem) into real ids and persist them."""
        for item in state['items']:
            if item['item_type'] not in ('question', 'term'):
                continue

            question_id = uid_to_question_id.get(item['_uid'])
            if not question_id:
                continue

            trigger_uid = item.get('depends_on_uid')
            trigger_ordem = item.get('depends_on_option_ordem')
            trigger_question_id = uid_to_question_id.get(trigger_uid) if trigger_uid else None

            depends_on_question_id = None
            depends_on_option_id = None

            if trigger_question_id and trigger_ordem is not None:
                trigger_question = api_client.get(f"/questions/{trigger_question_id}")
                if trigger_question:
                    for opt in trigger_question.get('options', []):
                        if opt.get('ordem') == trigger_ordem:
                            depends_on_option_id = opt.get('id')
                            break
                if depends_on_option_id:
                    depends_on_question_id = trigger_question_id

            resp = api_client.put(f"/questions/{question_id}", {
                'depends_on_question_id': depends_on_question_id,
                'depends_on_option_id': depends_on_option_id
            })
            if resp is None:
                ui.notify(
                    f'Erro ao salvar a condição de exibição do item #{item.get("ordem", "?")}',
                    type='negative'
                )

    def _save():
        _sync_form_data()
        ok, msg = _validate()
        if not ok:
            ui.notify(msg, type='warning')
            return
        
        _sync_all_editors_data()

        creator = session_manager.current_user or {}
        cid = creator.get('id')
        if not cid:
            ui.notify('Sessão inválida', type='negative')
            return

        built_items = []
        uid_to_question_id = {}
        for item in sorted(state['items'], key=lambda x: x['ordem']):
            if item['item_type'] == 'instruction':
                if item.get('item_id'):
                    resp = api_client.put(f"/questionnaires/instructions/{item['item_id']}", {'texto': item['texto']})
                else:
                    resp = instruction_client.create_instruction({'texto': item['texto']})

                if not resp or not resp.get('id'):
                    ui.notify('Erro ao salvar instrução', type='negative')
                    return

                built_items.append({
                    'item_type': 'instruction',
                    'item_id': resp['id'],
                    'ordem': item['ordem'],
                    'step': item.get('step', 1) or 1
                })
            else:
                payload = {
                    'titulo': item.get('titulo'),
                    'texto': item['texto'],
                    'tipo': item['tipo'],
                    'obrigatoria': item.get('obrigatoria', True),
                    'caption': item.get('caption', ''),
                    'peso': item['peso'],
                    'options': item['options']
                }
                
                if item.get('item_id'):
                    resp = api_client.put(f"/questions/{item['item_id']}", payload)
                else:
                    try:
                        resp = question_client.create_question(payload)
                        if not resp or not resp.get('id'):
                            error_detail = resp.get('detail', 'Dados inválidos') if isinstance(resp, dict) else 'Erro desconhecido'
                            label = 'Termo' if item['item_type'] == 'term' else 'Pergunta'
                            ui.notify(f'Erro ao salvar {label.lower()} #{item["ordem"]}: {error_detail}', type='negative')
                            return
                    except Exception as e:
                        error_msg = str(e)
                        label = 'Termo' if item['item_type'] == 'term' else 'Pergunta'
                        ui.notify(f'Erro ao salvar {label.lower()} #{item["ordem"]}: {error_msg}', type='negative')
                        return

                
                built_items.append({
                    'item_type': item['item_type'],
                    'item_id': resp['id'],
                    'ordem': item['ordem'],
                    'step': item.get('step', 1) or 1
                })
                uid_to_question_id[item['_uid']] = resp['id']

        _save_display_conditions(uid_to_question_id)

        payload = {
            'titulo': state['title'].strip(),
            'descricao': state['description'].strip(),
            'question_order': state['order_value'],
            'step_labels': [l for l in state['step_labels'] if l.strip()] or None,
            'criador_id': int(cid),
            'items': built_items
        }

        if state['is_edit']:
            updated = questionnaire_service.update_questionnaire(state['questionnaire_id'], payload)
            if not updated or not updated.get('id'):
                ui.notify('Erro ao atualizar questionário', type='negative')
                return
            
            ui.notify('Questionário atualizado com sucesso!', type='positive')
            
        else:
            try:
                created = questionnaire_service.create_questionnaire(payload)
                
                link = questionnaire_service.generate_link(created['id'])
                if link:
                    ui.notify(f'Questionário criado! Link: {link["link"]}', type='positive')
                else:
                    ui.notify('Questionário criado sem link', type='warning')
            
            except Exception as e:
                error_msg = str(e)
                
                if "identificador" in error_msg.lower():
                    ui.notify(f'{error_msg}', type='negative')
                else:
                    ui.notify(f'Erro ao criar questionário: {error_msg}', type='negative')
                return
            
        if on_done:
            on_done()

    
    def _handle_item_reorder(e):
        _sync_all_editors_data()
        old_index = e.args['old_index']
        new_index = e.args['new_index']
        
        if old_index == new_index:
            return
        
        moved_item = state['items'].pop(old_index)
        state['items'].insert(new_index, moved_item)
        
        for i, item in enumerate(state['items'], 1):
            item['ordem'] = i
        
        _update_display()

    def _cancel():
        if on_cancel:
            on_cancel()
    
    if not _check_eligibility():
        return

    with ui.column().style('width:100%; padding:1.5rem 2rem; gap:1rem;'):
        title_text = 'Editar Questionário' if state['is_edit'] else 'Criar Questionário'
        ui.label(title_text).style('font-size:1.4rem; font-weight:700; color:#111827;')

        with ui.card().style('padding:1rem; width:100%; overflow: hidden;'):
            with ui.column().style('width:100%; gap:1rem;'):
                with ui.column().style('width:100%; gap:1rem; min-width: 0;'):
                    with ui.row().style('width:100%; gap:1rem; flex-wrap: wrap; align-items: flex-end;'):
                        state['title_input'] = ui.input(
                            label='Título *',
                            value=state['title'],
                            on_change=_on_title_change
                        ).style('flex: 1 1 auto; min-width: 0; min-width: 250px;')
                        
                        state['order_select'] = ui.select(
                            options=ORDER_OPTIONS,
                            value=state['order_value'],
                            label='Ordem das perguntas',
                            on_change=_on_order_change
                        ).style('flex: 0 0 auto; width: auto; min-width: 220px;')
                
                state['desc_input'] = ui.textarea(
                    label='Descrição (opcional)',
                    value=state['description'],
                    on_change=_on_desc_change
                ).style('width:100%; min-width: 0;').props('autogrow rows=2')

                state['step_labels_mount'] = ui.column().style('width:100%; gap:0.5rem;')
        _render_step_labels()


        
        with ui.card().style('padding:1rem; width:100%;'):
            with ui.row().style('width:100%; justify-content:space-between; align-items:center;'):
                ui.label('Perguntas (arraste para reordenar)').style('font-weight:700;')

            state['list_mount'] = SortableColumn(on_change=_handle_item_reorder, group='questions')
            state['list_mount']._classes.append('gap-3')
            state['list_mount']._classes.append('mt-2')
            state['list_mount']._classes.append('w-full')
            _show_empty_message()

            with ui.row().style('width:100%; justify-content:flex-end; gap:1rem; margin-top:1rem;'):
                ui.button('Adicionar Instrução', on_click=_add_instruction).props('flat color=primary')
                ui.button('Adicionar Termo', on_click=_add_term).props('flat color=primary')
                ui.button('Adicionar Pergunta', on_click=_add_question).props('flat color=primary')
            
            
        with ui.row().style('justify-content:space-between; width:100%;'):
            ui.button('Cancelar', on_click=_cancel).props('outline color=grey-8')
            button_text = 'Atualizar questionário' if state['is_edit'] else 'Salvar questionário'
            ui.button(button_text, on_click=_save).props('color=primary')

    if state['is_edit']:
        _load_questionnaire_data()