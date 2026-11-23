import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "Freight Transportation Management System"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./freight_dev.db")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "freight-transport-secret-key-2026")

settings = Settings()
