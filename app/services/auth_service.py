from functools import wraps

from flask import g, redirect, session, url_for
from sqlalchemy import or_

from app.models import User


def authenticate_user(identifier: str, password: str) -> User | None:
    """Authenticate by the initial username or by an email address."""
    identifier = identifier.strip().lower()
    if not identifier:
        return None

    user = User.query.filter(
        or_(User.email == identifier, User.name.ilike(identifier))
    ).first()
    if user is None:
        return None

    try:
        if user.check_password(password):
            return user
    # A malformed legacy hash must behave like a failed login, never a server error.
    except (TypeError, ValueError):
        return None
    return None


def login_user(user: User) -> None:
    session["user_id"] = user.id


def logout_user() -> None:
    session.pop("user_id", None)


def current_user() -> User | None:
    if "user" not in g:
        user_id = session.get("user_id")
        g.user = User.query.get(user_id) if user_id else None
    return g.user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("auth.login_page"))
        return view(*args, **kwargs)

    return wrapped
