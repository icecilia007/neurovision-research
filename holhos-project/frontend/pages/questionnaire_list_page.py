from nicegui import ui
from services.questionnaire_service import questionnaire_service
from utils.session_manager import session_manager
from pages.questionnaire_create_page import questionnaire_create_page
import router

CARD = '''
width: 100%;
border-radius: 12px;
padding: 1rem 1.25rem;
box-shadow: 0 1px 3px rgba(0,0,0,0.1);
transition: 0.2s ease;
flex-wrap: wrap;
word-wrap: break-word;
overflow-wrap: break-word;
white-space: normal;
box-sizing: border-box;
margin: 0 auto;
'''

MODAL_CARD_STYLE = '''
min-width: 300px;
max-width: 90vw;
padding: 1.5rem;
border-radius: 12px;
box-sizing: border-box;
'''

GRID_STYLE = 'width: 100%; gap: 1rem; margin-top: 0.75rem; align-items: center;'

class QuestionnaireListPage:
    def __init__(self, on_back=None, content_container=None):
        self.on_back = on_back
        self.content_container = content_container
        self.grid_container = None

    def render(self):
        with ui.column().style('width: 100%; max-width: 1100px; gap: 1rem; margin: 0 auto; box-sizing: border-box;'):
            with ui.row().style('width: 100%; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;'):
                ui.label('Questionários').style('font-size: 1.4rem; font-weight: 700; color: #111827;')
                with ui.row().style('gap: 0.5rem; flex-wrap: wrap; justify-content: flex-end; width: 100%; max-width: 300px;'):
                    ui.button('Criar Questionário', on_click=self._go_create).props('color=primary').style('border-radius: 8px; height: 36px;')
                    if self.on_back:
                        ui.button('Voltar', on_click=self.on_back).props('outline')

            self.grid_container = ui.column().style(GRID_STYLE)
            self._load_my_questionnaires()

    def _load_my_questionnaires(self):
        self.grid_container.clear()
        creator_id = (session_manager.current_user or {}).get('id')
        if not creator_id:
            with self.grid_container:
                ui.label('Sessão inválida: usuário não identificado.').style('color: #b91c1c;')
            return

        data = questionnaire_service.list_by_creator(creator_id) or []
        if not data:
            with self.grid_container:
                ui.label('Você ainda não possui questionários.').style('color: #6b7280;')
            return

        with self.grid_container:
            with ui.column().style('width: 100%; align-items: center; gap: 1rem;'):
                for q in data:
                    self._card(q)

    def _card(self, q: dict):
        qid = q.get('id')
        title = q.get('titulo', 'Sem título')
        desc = q.get('descricao') or ''

        with ui.card().style(CARD):
            ui.label(title).style('''
                font-size: 1.1rem;
                font-weight: 700;
                color: #111827;
                word-break: break-word;
                white-space: normal;
                line-height: 1.4;
            ''')

            if desc:
                ui.label(desc).style('''
                    color: #6b7280;
                    margin-top: 0.25rem;
                    word-break: break-word;
                    white-space: normal;
                    line-height: 1.4;
                ''')

            with ui.row().style('''
                justify-content: flex-end;
                gap: 0.5rem;
                margin-top: 1rem;
                flex-wrap: wrap;
                width: 100%;
                box-sizing: border-box;
            '''):
                ui.button('Ver Links', icon='visibility', on_click=lambda q_id=qid: self._on_ver_link(q_id)).props('flat color=primary dense')
                ui.button('Copiar Link', icon='content_copy', on_click=lambda q_id=qid: self._on_copiar_link(q_id)).props('flat color=primary dense')
                ui.button('Editar', icon='edit', on_click=lambda q_id=qid: self._on_edit(q_id)).props('flat color=primary dense')
                ui.button('Deletar', icon='delete', on_click=lambda i=qid: self._delete_questionnaire(i)).props('flat color=negative dense')


    def _on_ver_link(self, questionnaire_id: int):
        try:
            response = questionnaire_service.generate_link(questionnaire_id)
            if response and 'link' in response:
                link = response['link']

                def copiar_e_fechar():
                    self._copy_to_clipboard(link)
                    dialog.close()

                dialog = self._modal_padrao(
                    'Link do Questionário',
                    link,
                    [
                        {'texto': 'Fechar', 'acao': lambda: dialog.close(), 'props': 'flat'},
                        {'texto': 'Copiar', 'acao': copiar_e_fechar, 'props': 'color=primary'},
                    ],
                )
                dialog.open()
            else:
                ui.notify('Erro ao gerar link do questionário', type='negative')
        except Exception as e:
            ui.notify(f'Erro ao gerar link: {str(e)}', type='negative')

    def _copy_to_clipboard(self, link: str, dialog=None):
        js_code = f"""
        async function copyToClipboard() {{
            try {{
                if (navigator.clipboard && window.isSecureContext) {{
                    await navigator.clipboard.writeText("{link}");
                    return true;
                }} else {{
                    const textArea = document.createElement('textarea');
                    textArea.value = "{link}";
                    textArea.style.position = 'fixed';
                    textArea.style.left = '-999999px';
                    textArea.style.top = '-999999px';
                    document.body.appendChild(textArea);
                    textArea.focus();
                    textArea.select();
                    try {{
                        document.execCommand('copy');
                        document.body.removeChild(textArea);
                        return true;
                    }} catch (err) {{
                        document.body.removeChild(textArea);
                        return false;
                    }}
                }}
            }} catch (err) {{
                return false;
            }}
        }}

        copyToClipboard().then(success => {{
            if (success) {{
                window.copySuccess = true;
            }} else {{
                window.copySuccess = false;
            }}
        }});
        """

        ui.run_javascript(js_code)
        ui.timer(0.1, lambda: self._check_copy_result(dialog), once=True)

    def _check_copy_result(self, dialog=None):
        check_js = """
        if (window.copySuccess === true) {
            window.copyResult = 'success';
            window.copySuccess = undefined;
        } else if (window.copySuccess === false) {
            window.copyResult = 'error';
            window.copySuccess = undefined;
        } else {
            window.copyResult = 'pending';
        }
        """

        ui.run_javascript(check_js)
        ui.timer(0.1, lambda: self._handle_copy_feedback(dialog), once=True)

    def _handle_copy_feedback(self, dialog=None):
        ui.run_javascript("""
        if (window.copyResult === 'success') {
            window.showCopySuccess = true;
            window.copyResult = undefined;
        } else if (window.copyResult === 'error') {
            window.showCopyError = true;
            window.copyResult = undefined;
        }
        """)
        ui.notify('Link copiado!', type='positive')
        if dialog:
            dialog.close()

    def _on_edit(self, questionnaire_id: int):
        eligibility = questionnaire_service.check_eligibility(questionnaire_id)
        if not eligibility or not eligibility.get('eligible'):
            ui.notify('Não é possível editar este questionário, pois ele já possui respostas.', type='negative')
            return
        def render_edit():
            questionnaire_create_page(on_done=self._back_to_list, on_cancel=self._back_to_list, questionnaire_id=questionnaire_id)
        router.clear_and_render(self.content_container, render_edit)

    def _on_copiar_link(self, questionnaire_id: int):
        try:
            response = questionnaire_service.generate_link(questionnaire_id)
            if response and 'link' in response:
                self._copy_to_clipboard(response['link'])
            else:
                ui.notify('Erro ao gerar link do questionário', type='negative')
        except Exception as e:
            ui.notify(f'Erro ao gerar link: {str(e)}', type='negative')

    def _delete_questionnaire(self, questionnaire_id: int):
        dialog = ui.dialog()
        with dialog, ui.card().style(MODAL_CARD_STYLE):
            ui.label('Confirmação de Exclusão').style('font-size: 1.2rem; font-weight: 700; margin-bottom: 1rem; text-align: center;')
            ui.label(f'Deseja realmente apagar o questionário #{questionnaire_id}?').style('text-align: center; color: #6b7280; margin-bottom: 1.5rem; word-break: break-word;')
            with ui.row().style('justify-content: center; gap: 0.5rem; width: 100%; flex-wrap: wrap;'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button('Deletar', on_click=lambda: self._confirm_delete(dialog, questionnaire_id)).props('color=negative')
        dialog.open()

    def _modal_padrao(self, titulo: str, conteudo: str, botoes: list):
        dialog = ui.dialog()
        with dialog, ui.card().style(MODAL_CARD_STYLE):
            ui.label(titulo).style('font-size: 1.2rem; font-weight: 700; margin-bottom: 1rem; text-align: center;')
            ui.label(conteudo).style('text-align: center; color: #6b7280; margin-bottom: 1.5rem; word-break: break-all;')
            with ui.row().style('justify-content: center; gap: 0.5rem; width: 100%; flex-wrap: wrap;'):
                for btn in botoes:
                    ui.button(btn['texto'], on_click=btn['acao']).props(btn.get('props', 'flat'))
        return dialog

    def _confirm_delete(self, dialog, questionnaire_id: int):
        try:
            dialog.close()
            success = questionnaire_service.delete(questionnaire_id)
            if success:
                ui.notify('Questionário deletado com sucesso', type='positive')
                self._load_my_questionnaires()
            else:
                ui.notify('Erro ao deletar questionário', type='negative')
        except Exception as e:
            ui.notify(f'Erro ao deletar: {str(e)}', type='negative')

    def _go_create(self):
        def render_create():
            questionnaire_create_page(on_done=self._back_to_list, on_cancel=self._back_to_list)
        router.clear_and_render(self.content_container, render_create)

    def _back_to_list(self):
        router.clear_and_render(self.content_container, self.render)
