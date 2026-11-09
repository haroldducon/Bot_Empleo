import secrets
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    encryption_key: str
    cors_origins: str = "http://localhost:5173"
    access_token_minutes: int = 60 * 24  # 24 horas
    gemini_model: str = "gemini-flash-latest"
    jooble_api_key: str = ""
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32 or value.lower() in {"secret", "changeme", "change-me"}:
            raise ValueError("SECRET_KEY debe tener al menos 32 caracteres aleatorios")
        return value

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, value: str) -> str:
        from cryptography.fernet import Fernet
        try:
            Fernet(value.encode())
        except Exception as exc:
            raise ValueError("ENCRYPTION_KEY no es una clave Fernet válida") from exc
        return value

    @field_validator("access_token_minutes")
    @classmethod
    def validate_token_lifetime(cls, value: int) -> int:
        if not 5 <= value <= 1440:
            raise ValueError("ACCESS_TOKEN_MINUTES debe estar entre 5 y 1440")
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
