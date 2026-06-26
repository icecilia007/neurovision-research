import re
from typing import List, Tuple


class Validators:
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return True, ""
        return False, "Email inválido"

    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        if len(password) < 6:
            return False, "Senha deve ter pelo menos 6 caracteres"
        return True, ""

    @staticmethod
    def validate_age(age: int) -> Tuple[bool, str]:
        if age < 1 or age > 120:
            return False, "Idade deve estar entre 1 e 120 anos"
        return True, ""

    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        pattern = r'^\(\d{2}\)\s\d{4,5}-\d{4}$'
        if re.match(pattern, phone) or len(
                phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")) >= 10:
            return True, ""
        return False, "Telefone inválido"


validators = Validators()
