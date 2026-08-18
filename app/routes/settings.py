from flask import Blueprint, render_template
from app.services.auth_service import login_required
from app.models.user import User

bp = Blueprint("settings", __name__, url_prefix="/settings")

@bp.route("/")
@login_required
def index():
    users = User.query.order_by(User.name).all()
    return render_template("settings/index.html", users=users)
