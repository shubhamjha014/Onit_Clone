from flask import Blueprint, render_template, request

from app.services.auth_service import authenticate_user

bp = Blueprint("auth", __name__)


@bp.route("/", methods=["GET"])
def login_page():
    return render_template("index.html")


@bp.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    user = authenticate_user(email, password)

    if user:
        return render_template("success.html", email=user.email)

    return render_template("index.html", error="Invalid email or password")
