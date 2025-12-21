from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/linkpago"

    # Security
    secret_key: str = "change-this-to-a-secure-random-string"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Webpay
    webpay_environment: str = "integration"
    webpay_commerce_code: str = "597055555532"
    webpay_api_key: str = "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@example.com"

    # App
    app_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
