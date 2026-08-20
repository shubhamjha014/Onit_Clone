from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column("password_hash", db.String(255), nullable=False)
    # Compatibility/audit field. It deliberately stores a hash, never plaintext.
    original_password = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        password_hash = generate_password_hash(password)
        self.password_hash = password_hash
        self.original_password = password

    def check_password(self, password: str) -> bool:
        print("Password -->", password)
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.email}>"
