import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # A sensible default for local development if user doesn't set POSTGRES URL.
    #  "sqlite:///./hostel.db",
   "postgresql+psycopg://postgres:postgres@localhost:5432/hostel",

)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
auth_key = os.getenv("MSG91_AUTH_KEY")
otp_template_id = os.getenv("MSG91_OTP_TEMPLATE_ID")

import os

from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "HR Management System"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///./hostel.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 * 24 * 60  # 30 days
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ["*"]
    
    # SMS (MSG91) - Optional for production
    MSG91_AUTH_KEY: Optional[str] = None
    MSG91_TEMPLATE_ID: Optional[str] = None
    MSG91_SENDER_ID: Optional[str] = None

    # Redis (for OTP storage)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Google Cloud Vision API
    GOOGLE_CLOUD_CREDENTIALS_PATH: Optional[str] = None

    # Upload storage configuration
    UPLOAD_BASE_DIR: str = "modules/static/uploads"
    UPLOAD_URL_BASE: str = "/static/uploads"

    @field_validator(
        "GOOGLE_CLOUD_CREDENTIALS_PATH",
        "UPLOAD_BASE_DIR",
        "UPLOAD_URL_BASE",
        mode="before"
    )
    def strip_inline_comment(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if "#" in text:
            text = text.split("#", 1)[0].strip()
        return text or None

    @property
    def owner_image_dir(self) -> str:
        return os.path.abspath(os.path.join(self.UPLOAD_BASE_DIR, "owners"))

    @property
    def tenant_image_dir(self) -> str:
        return os.path.abspath(os.path.join(self.UPLOAD_BASE_DIR, "tenants"))

    @property
    def hostel_image_dir(self) -> str:
        return os.path.abspath(os.path.join(self.UPLOAD_BASE_DIR, "hostels"))

    @property
    def aadhaar_image_dir(self) -> str:
        return os.path.abspath(os.path.join(self.UPLOAD_BASE_DIR, "aadhaar"))

    @property
    def owner_image_url(self) -> str:
        return f"{self.UPLOAD_URL_BASE}/owners"

    @property
    def tenant_image_url(self) -> str:
        return f"{self.UPLOAD_URL_BASE}/tenants"

    @property
    def hostel_image_url(self) -> str:
        return f"{self.UPLOAD_URL_BASE}/hostels"

    @property
    def aadhaar_image_url(self) -> str:
        return f"{self.UPLOAD_URL_BASE}/aadhaar"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


