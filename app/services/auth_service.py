from functools import wraps

from flask import g, redirect, session, url_for

from app.models import User


def authenticate_user(email: str, password: str) -> User | None:
    user = User.query.filter_by(email=email.lower()).first()
    if user and user.check_password(password):
        return user
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
