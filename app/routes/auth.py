from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.services.auth_service import (
    authenticate_user,
    current_user,
    login_user,
    logout_user,
)

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET"])
def login_page():
    if current_user():
        return redirect(url_for("home.dashboard"))
    return render_template("auth/login.html")


@bp.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    user = authenticate_user(email, password)
    if user is None:
        return render_template(
            "auth/login.html", error="Invalid email or password", email=email
        )

    login_user(user)
    return redirect(url_for("home.dashboard"))


@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login_page"))
