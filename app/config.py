import os
import secrets
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()


def _database_url() -> str:
    """Build the SQLAlchemy URL from DATABASE_URL, or from discrete DB_* variables."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    user = quote(os.getenv("DB_USER", "postgres"), safe="")
    password = quote(os.getenv("DB_PASSWORD", ""), safe="")
    return (
        f"postgresql+psycopg://{user}:{password}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
        f"/{os.getenv('DB_NAME', 'legal_management')}"
    )


class Config:
    # A random per-process key keeps sessions unforgeable when SECRET_KEY is unset,
    # at the cost of invalidating them on restart.
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    APP_NAME = os.getenv("APP_NAME", "Legal Management Portal")
    ENVIRONMENT_LABEL = os.getenv("ENVIRONMENT_LABEL", "Development")
