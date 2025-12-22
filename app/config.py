from functools import lru_cache

from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Transbank public test credentials (only for integration/testing)
_TRANSBANK_INTEGRATION_CODE = "597055555532"
_TRANSBANK_INTEGRATION_KEY = "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/linkpago"

    # Security (required - no default)
    secret_key: str

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Webpay
    webpay_environment: str = "integration"
    webpay_commerce_code: str = ""
    webpay_api_key: str = ""

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@example.com"

    # App
    app_url: str = "http://localhost:8000"

    @computed_field
    @property
    def is_https(self) -> bool:
        """Derived from app_url - True if using HTTPS."""
        return self.app_url.startswith("https://")

    @model_validator(mode="after")
    def validate_credentials(self):
        if self.webpay_environment == "production":
            if not self.webpay_commerce_code or not self.webpay_api_key:
                raise ValueError(
                    "webpay_commerce_code and webpay_api_key are required in production"
                )
        else:
            # Use Transbank test credentials for integration mode
            if not self.webpay_commerce_code:
                self.webpay_commerce_code = _TRANSBANK_INTEGRATION_CODE
            if not self.webpay_api_key:
                self.webpay_api_key = _TRANSBANK_INTEGRATION_KEY
        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
