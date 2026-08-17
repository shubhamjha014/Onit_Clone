import os

from dotenv import load_dotenv

load_dotenv()


def _database_url() -> str:
    """Build the SQLAlchemy URL from DATABASE_URL, or from discrete DB_* variables."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    return (
        "postgresql+psycopg://"
        f"{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', '')}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
        f"/{os.getenv('DB_NAME', 'legal_management')}"
    )


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    APP_NAME = os.getenv("APP_NAME", "Legal Management Portal")
    ENVIRONMENT_LABEL = os.getenv("ENVIRONMENT_LABEL", "Development")
