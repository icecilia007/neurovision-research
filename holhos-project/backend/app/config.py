from pydantic_settings import BaseSettings
import urllib.request

def _get_public_ip(timeout: float = 5.0) -> str:
    urls = [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://checkip.amazonaws.com"
    ]
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                ip = resp.read().decode().strip()
                if ip:
                    return ip
        except Exception:
            continue
    return "localhost:8080"

class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:password@localhost:5432/formularios_db"
    frontend_base_url: str = _get_public_ip()

    class Config:
        env_file = ".env"
    
settings = Settings()
