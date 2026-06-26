from nicegui import ui
from services.user_service import user_service
from utils.validators import validators
from datetime import date, datetime
import re

BTN_FULL = 'width: 100%; height: 40px; border-radius: 8px;'
INPUT_STYLE = 'width: 100%;'


class SignupForm:
    def __init__(self, on_success_callback=None, on_switch_to_login=None):
        self.form_data = {}
        self.on_success_callback = on_success_callback
        self.on_switch_to_login = on_switch_to_login
        self.name_input = None
        self.email_input = None
        self.password_input = None
        self.gender_select = None
        self.birth_date_input = None
        self.education_select = None
        self.phone_input = None
        self.error_label = None

    def render(self):
        with ui.column().style('width: 100%; gap: 0.75rem;'):
            self.name_input = ui.input(label='Nome Completo *', placeholder='Seu nome').style(INPUT_STYLE)
            self.email_input = ui.input(label='Email *', placeholder='voce@email.com').style(INPUT_STYLE)
            self.password_input = ui.input(label='Senha *', password=True, placeholder='••••••').style(INPUT_STYLE)

            self.gender_select = ui.select(
                options={
                    'masculino': 'Masculino',
                    'feminino': 'Feminino',
                    'outro': 'Outro',
                    'nao_informar': 'Não informar',
                },
                label='Gênero *'
            ).style(INPUT_STYLE).props('filled clearable use-chips')

            self._render_birth_date_field()

            self.education_select = ui.select(
                options={
                    'fundamental_incompleto': 'Fundamental Incompleto',
                    'fundamental_completo': 'Fundamental Completo',
                    'medio_incompleto': 'Médio Incompleto',
                    'medio_completo': 'Médio Completo',
                    'superior_incompleto': 'Superior Incompleto',
                    'superior_completo': 'Superior Completo',
                    'pos_graduacao': 'Pós-graduação',
                    'mestrado': 'Mestrado',
                    'doutorado': 'Doutorado',
                },
                label='Escolaridade *'
            ).style(INPUT_STYLE).props('filled clearable use-chips')

            self.phone_input = ui.input(label='Telefone *', placeholder='(11) 99999-9999').style(INPUT_STYLE)

            ui.button('Cadastrar', on_click=self._on_signup, color='primary').style(BTN_FULL)

            self.error_label = ui.label('').style('color: #b91c1c; text-align: center; min-height: 20px;')

            ui.separator()

            with ui.row().style('width: 100%; justify-content: center;'):
                ui.button(
                    'Já tem conta? Fazer login',
                    on_click=(lambda: self.on_switch_to_login() if self.on_switch_to_login else None)
                ).props('flat color=primary').style('border-radius: 8px;')

    def _render_birth_date_field(self):
        with ui.column().style('width: 100%; gap: 0.25rem;'):
            with ui.input(
                    label='Data de Nascimento *',
                    placeholder='DD/MM/AAAA',
                    validation=self._validate_birth_date_input
            ).style(INPUT_STYLE) as self.birth_date_input:
                with self.birth_date_input.add_slot('append'):
                    ui.icon('edit_calendar').on('click', lambda: self._open_calendar()).classes('cursor-pointer')

            with ui.menu() as self.calendar_menu:
                self.date_picker = ui.date().on('update:model-value', self._on_calendar_select)

    def _validate_birth_date_input(self, value):
        if not value:
            return None

        if not re.match(r'^\d{2}/\d{2}/\d{4}$', value):
            return 'Formato deve ser DD/MM/AAAA'

        try:
            day, month, year = map(int, value.split('/'))
            birth_date = date(year, month, day)

            if birth_date > date.today():
                return 'Data de nascimento não pode ser no futuro'

            if birth_date < date(1900, 1, 1):
                return 'Data muito antiga (anterior a 1900)'

            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            if age < 13:
                return 'Idade mínima: 13 anos'

            if age > 120:
                return 'Idade muito avançada, verifique a data'

            return None
        except ValueError:
            return 'Data inválida'

    def _open_calendar(self):
        self.calendar_menu.open()

    def _on_calendar_select(self, e):
        date_str = None

        try:
            if hasattr(e, 'args') and isinstance(e.args, list) and len(e.args) > 0:
                date_str = e.args[0]
            elif hasattr(e, 'args') and isinstance(e.args, dict):
                date_str = e.args.get('value', '')
            elif hasattr(e, 'value'):
                date_str = e.value
            elif isinstance(e, str):
                date_str = e

            if not date_str:
                return

            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

            today = date.today()
            if date_obj > today:
                ui.notify('Data de nascimento não pode ser no futuro', type='warning')
                return

            if date_obj < date(1900, 1, 1):
                ui.notify('Data muito antiga (anterior a 1900)', type='warning')
                return

            age = today.year - date_obj.year - ((today.month, today.day) < (date_obj.month, date_obj.day))
            if age < 13:
                ui.notify('Idade mínima: 13 anos', type='warning')
                return

            if age > 120:
                ui.notify('Idade muito avançada, verifique a data', type='warning')
                return

            formatted_date = date_obj.strftime('%d/%m/%Y')
            self.birth_date_input.value = formatted_date
            self.calendar_menu.close()
            ui.notify(f'Data selecionada: {formatted_date} (Idade: {age} anos)', type='positive')

        except Exception as ex:
            ui.notify(f'Erro ao processar data: {str(ex)}', type='negative')

    def _collect_form_data(self):
        self.form_data = {
            'nome_completo': (self.name_input.value or '').strip() if self.name_input else '',
            'email': (self.email_input.value or '').strip() if self.email_input else '',
            'senha': (self.password_input.value or '') if self.password_input else '',
            'genero': self.gender_select.value if self.gender_select else None,
            'nascimento': self._convert_birth_date_to_iso(),
            'escolaridade': self.education_select.value if self.education_select else None,
            'telefone': (self.phone_input.value or '').strip() if self.phone_input else '',
        }

    def _convert_birth_date_to_iso(self):
        if not self.birth_date_input or not self.birth_date_input.value:
            return None

        try:
            day, month, year = map(int, self.birth_date_input.value.split('/'))
            birth_date = date(year, month, day)
            return birth_date.isoformat()
        except:
            return None

    def _validate_form(self) -> tuple[bool, str]:
        required = ['nome_completo', 'email', 'senha', 'genero', 'nascimento', 'escolaridade', 'telefone']

        for field in required:
            value = self.form_data.get(field)
            if value in (None, '', 0):
                field_names = {
                    'nome_completo': 'Nome Completo',
                    'email': 'Email',
                    'senha': 'Senha',
                    'genero': 'Gênero',
                    'nascimento': 'Data de Nascimento',
                    'escolaridade': 'Escolaridade',
                    'telefone': 'Telefone'
                }
                return False, f'Campo {field_names.get(field, field)} é obrigatório'

        ok_email, email_err = validators.validate_email(self.form_data['email'])
        if not ok_email:
            return False, email_err

        ok_pwd, pwd_err = validators.validate_password(self.form_data['senha'])
        if not ok_pwd:
            return False, pwd_err

        if self.birth_date_input and self.birth_date_input.value:
            birth_date_validation = self._validate_birth_date_input(self.birth_date_input.value)
            if birth_date_validation:
                return False, birth_date_validation

        return True, ''

    def _on_signup(self):
        self.error_label.text = ''

        self._collect_form_data()

        valid, msg = self._validate_form()
        if not valid:
            self.error_label.text = msg
            return

        print(f"[DEBUG] Dados do cadastro: {self.form_data}")

        try:
            user = user_service.create_user(self.form_data)
        except Exception as e:
            error_message = str(e)
            self.error_label.text = error_message
            ui.notify(error_message, type='negative')
            return

        if user:
            ui.notify('Usuário cadastrado com sucesso!', type='positive')
            if self.on_success_callback:
                self.on_success_callback()
        else:
            self.error_label.text = 'Erro ao cadastrar usuário. Verifique os dados e tente novamente.'
