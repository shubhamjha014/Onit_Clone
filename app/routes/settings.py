import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.services.auth_service import current_user, login_required
from app.models.user import User

bp = Blueprint("settings", __name__, url_prefix="/settings")

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8

@bp.route("/")
@login_required
def index():
    return render_template("settings/index.html")


@bp.route("/users")
@login_required
def users():
    return render_template("settings/users.html", users=User.query.order_by(User.name).all())


@bp.route("/users", methods=["POST"])
@login_required
def create_user():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    errors = []

    if not name:
        errors.append("User Name is required.")
    if not email:
        errors.append("Email is required.")
    elif not EMAIL_PATTERN.fullmatch(email):
        errors.append("Enter a valid email address.")
    if not password:
        errors.append("Password is required.")
    elif len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    if User.query.filter_by(email=email).first():
        errors.append("A user with this email already exists.")

    if errors:
        for error in errors:
            flash(error, "error")
        return redirect(url_for("settings.users"))

    user = User(name=name, email=email)
    user.set_password(password)
    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("A user with this email already exists.", "error")
    except Exception:
        db.session.rollback()
        flash("The user could not be created. Please try again.", "error")
    else:
        flash(f"User {user.name} created successfully.", "success")

    return redirect(url_for("settings.users"))


@bp.route("/lists")
@login_required
def lists():
    return render_template("settings/lists.html")


@bp.route("/users/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_users():
    selected_ids = set()
    for value in request.form.getlist("user_ids"):
        try:
            selected_ids.add(int(value))
        except (TypeError, ValueError):
            continue

    if not selected_ids:
        flash("Select at least one user to delete.", "error")
        return redirect(url_for("settings.users"))

    active_user = current_user()
    if active_user and active_user.id in selected_ids:
        selected_ids.remove(active_user.id)
        flash("Your own signed-in account cannot be deleted.", "error")

    users_to_delete = User.query.filter(User.id.in_(selected_ids)).all() if selected_ids else []
    if not users_to_delete:
        if selected_ids:
            flash("The selected users could not be found.", "error")
        return redirect(url_for("settings.users"))

    try:
        for user in users_to_delete:
            db.session.delete(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("The selected users could not be deleted because they are linked to existing records.", "error")
    except Exception:
        db.session.rollback()
        flash("The selected users could not be deleted. Please try again.", "error")
    else:
        flash(f"Deleted {len(users_to_delete)} user(s).", "success")

    return redirect(url_for("settings.users"))
