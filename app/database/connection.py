import psycopg

from app.config import Config


def get_connection():
    return psycopg.connect(
        **Config.DB_CONFIG
    )