from functools import lru_cache
from pydantic import model_validator, Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    postgres_user: str = "portfolio"
    postgres_password: str
    postgres_db: str = "portfolio"
    db_host: str = "localhost"
    db_port: int = 5432
    site_url: str = "http://localhost:8080"
    cors_origins: list[str] = ["http://localhost:8080"]
    cookie_secure: bool = False
    admin_session_hours: int = 8
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = Field("",validation_alias=AliasChoices("SMTP_USERNAME","SMTP_USER","smtp_user"))
    smtp_password: str = ""
    smtp_from: str = Field("",validation_alias=AliasChoices("SMTP_FROM_EMAIL","SMTP_FROM","smtp_from"))
    smtp_starttls: bool = Field(True,validation_alias=AliasChoices("SMTP_USE_STARTTLS","SMTP_STARTTLS","smtp_starttls"))
    contact_notification_email: str = "pericacs@gmail.com"

    @model_validator(mode="after")
    def validate_environment(self):
        if not 1 <= self.admin_session_hours <= 24:
            raise ValueError("Sessão administrativa deve durar entre 1 e 24 horas")
        if len(self.postgres_password) < 16:
            raise ValueError("POSTGRES_PASSWORD deve conter pelo menos 16 caracteres")
        if self.app_env == "production":
            if self.smtp_host and not self.smtp_starttls:
                raise ValueError("SMTP em produção exige STARTTLS")
            if not self.cookie_secure or not self.site_url.startswith("https://"):
                raise ValueError("Produção exige HTTPS e cookies Secure")
            if any(not origin.startswith("https://") for origin in self.cors_origins):
                raise ValueError("Produção exige origens HTTPS explícitas")
        return self

    @property
    def smtp_configured(self):
        return bool(self.smtp_host and self.smtp_from and (not self.smtp_user or self.smtp_password))

    @property
    def database_url(self):
        return URL.create("postgresql+psycopg", username=self.postgres_user,
                          password=self.postgres_password, host=self.db_host,
                          port=self.db_port, database=self.postgres_db)


@lru_cache
def get_settings():
    return Settings()
