"""Centralized AppSettings Configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Settings loaded from Environment Variables or .env file."""

    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    SECRET_KEY: str = "super-secret-key-change-in-production-min-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 240  # 4 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # 7 days

    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/aduc_auto_db"

    # VNPay Sandbox Settings
    VNPAY_TMN_CODE: str = "YOUR_TMN_CODE"
    VNPAY_HASH_SECRET: str = "YOUR_HASH_SECRET"
    VNPAY_URL: str = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
    VNPAY_RETURN_URL: str = "http://localhost:3000/orders/result"

    # Mail SMTP Settings
    MAIL_USERNAME: str = "no-reply@aduc-auto.com"
    MAIL_PASSWORD: str = "secret"
    MAIL_FROM: str = "no-reply@aduc-auto.com"
    MAIL_SERVER: str = "localhost"
    MAIL_PORT: int = 1025
    MAIL_STARTTLS: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
