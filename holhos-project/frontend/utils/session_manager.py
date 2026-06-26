from typing import Optional, Dict, Any
from nicegui import app

class SessionManager:
    def login(self, user: Dict[str, Any]) -> None:
        app.storage.user['current_user'] = user
        app.storage.user['is_authenticated'] = True

    def logout(self) -> None:
        app.storage.user['current_user'] = None
        app.storage.user['is_authenticated'] = False

    @property
    def current_user(self) -> Optional[Dict[str, Any]]:
        return app.storage.user.get('current_user')

    @property
    def is_authenticated(self) -> bool:
        return app.storage.user.get('is_authenticated', False)


session_manager = SessionManager()
