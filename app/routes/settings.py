import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.services.auth_service import current_user, login_required
from app.models.user import User
from app.models.app_setting import AppSetting

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

import json
import re # <--- Make sure 're' is imported at the top

@bp.route("/app-settings", methods=["GET", "POST"])
@login_required
def app_settings():
    if request.method == "POST":
        for key, raw_string in request.form.items():
            if key == "csrf_token":
                continue
            
            # 1. Aggressively clean the input using Regex
            # This instantly removes [, ], ", ', and all hidden newlines/returns
            cleaned_string = re.sub(r'[\[\]"\'\n\r]', '', raw_string)
            
            # 2. Split by comma and remove extra whitespace
            clean_list = [item.strip() for item in cleaned_string.split(",") if item.strip()]
            
            # 3. Find or create the setting
            setting = AppSetting.query.filter_by(key=key).first()
            if not setting:
                if key.startswith("matter"):
                    app_name = "Matters"
                elif key.startswith("task"):
                    app_name = "Tasks"
                else:
                    app_name = "General"
                    
                setting = AppSetting(app_name=app_name, key=key)
                db.session.add(setting)
                
            # 4. Save as a pure Python list (SQLAlchemy automatically handles the JSON conversion)
            setting.value = clean_list
            
        try:
            db.session.commit()
            flash("App settings updated successfully.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating settings: {str(e)}", "error")
            
        return redirect(url_for('settings.app_settings'))

    # ==========================================
    # GET Request: Fetch and prepare for the UI
    # ==========================================
    settings_query = AppSetting.query.all()
    settings_data = {}
    
    for item in settings_query:
        val = item.value
        
        # Failsafe: Parse stringified JSON if the database returned a string
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except json.JSONDecodeError:
                val = [val]
                
        # Join the list back into a beautiful comma-separated string for the UI textareas
        if isinstance(val, list) and len(val) > 0:
            settings_data[item.key] = ", ".join(val)
        else:
            settings_data[item.key] = ""
            
    return render_template("settings/app_settings.html", settings=settings_data)