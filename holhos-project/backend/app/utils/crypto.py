import base64
from typing import Union
from urllib.parse import unquote


def _normalize_encoded_id(raw_id: str) -> str:
    """Normalize incoming path IDs to support URL-encoded and unpadded base64 values."""
    normalized = unquote((raw_id or '').strip())
    if not normalized:
        return normalized

    # urlsafe_b64decode requires correct padding length.
    padding = (-len(normalized)) % 4
    if padding:
        normalized += '=' * padding
    return normalized

def encrypt_questionnaire_id(questionnaire_id: int) -> str:
    id_str = str(questionnaire_id)
    id_bytes = id_str.encode('utf-8')
    encoded = base64.urlsafe_b64encode(id_bytes).decode('utf-8')
    return encoded.rstrip('=')

def decrypt_questionnaire_id(encoded_id: str) -> int:
    try:
        normalized_id = _normalize_encoded_id(encoded_id)
        decoded_bytes = base64.urlsafe_b64decode(normalized_id.encode('utf-8'))
        return int(decoded_bytes.decode('utf-8'))
    except Exception:
        try:
            return int(encoded_id)
        except ValueError:
            raise ValueError("ID do questionário inválido")

def is_encrypted_id(id_param: str) -> bool:
    try:
        normalized_id = _normalize_encoded_id(id_param)
        decoded = base64.urlsafe_b64decode(normalized_id.encode('utf-8'))
        int(decoded.decode('utf-8'))
        return True
    except Exception:
        try:
            int(id_param)
            return False
        except ValueError:
            return False
