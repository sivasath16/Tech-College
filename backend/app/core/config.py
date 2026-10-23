from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg://localhost/placement_portal"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173"
    upload_dir: Path = BASE_DIR / "uploads"
    max_logo_bytes: int = 2 * 1024 * 1024
    otp_expire_minutes: int = 5
    otp_max_attempts: int = 5
    admin_email: str = "admin@college.edu"
    admin_password: str = "Admin@12345"


settings = Settings()
