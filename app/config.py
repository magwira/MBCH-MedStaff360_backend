import os
from dotenv import load_dotenv
load_dotenv()
from pydantic_settings import BaseSettings

# Settings class to load environment variables
class Settings(BaseSettings):
    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    SUPERBASE_USER: str = os.getenv("SUPERBASE_USER")
    SUPERBASE_PASSWORD: str = os.getenv("SUPERBASE_PASSWORD")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    GMAIL_PASSWORD: str = os.getenv("GMAIL_PASSWORD")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 999999
    OTP_EXPIRY_MINUTES: int = 599


    class Config:
        env_file = ".env"

# Initialize settings
settings = Settings()