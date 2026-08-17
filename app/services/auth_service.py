from app.database.connection import get_connection
from app.models.user import User


def authenticate_user(email: str, password: str):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, email, password
                    FROM users
                    WHERE email = %s AND password = %s
                    """,
                    (email, password),
                )
                row = cursor.fetchone()
                if row is None:
                    return None

                return User(id=row[0], email=row[1], password=row[2])
    except Exception as exc:
        print(f"Database connection failed: {exc}")
        return None
