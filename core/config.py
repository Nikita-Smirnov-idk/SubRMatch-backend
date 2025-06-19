from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    AI_API_KEY: str
    AI_API_URL: str

    REDDIT_CLIENT_ID: str
    REDDIT_CLIENT_SECRET: str
    REDDIT_USER_AGENT: str
    REDDIT_BASE_URL: str
    REDDIT_USER_NAME: str
    REDDIT_USER_PASSWORD: str
    
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str

    MAIL_FROM_NAME: str
    MAIL_VERIFICATION_COOLDOWN: int = 300

    VERIFICATION_TOKEN_SECRET: str
    VERIFICATION_TOKEN_LIFETIME_HOURS: int = 24

    APP_URL: str = "http://localhost:8000"

    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    SECRET_KEY: str

    REDIS_URL: str = "redis://localhost:6379/"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    APP_NAME: str
    DOMAIN: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

broker_url = settings.REDIS_URL
result_backend = settings.REDIS_URL
DATABASE_URL = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
broker_connection_retry_on_startup = True