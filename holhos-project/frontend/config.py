import os

class Config:
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    API_VERSION: str = "v1"
    STORAGE_SECRET: str = os.getenv("STORAGE_SECRET", "questionnaire-app-secret-key-2024")

    @property
    def api_url(self) -> str:
        return f"{self.API_BASE_URL}/api/{self.API_VERSION}"


config = Config()
