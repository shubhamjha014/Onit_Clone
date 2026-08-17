from flask import Blueprint, render_template

from app.models import Activity, Invoice, Matter, Task
from app.services.auth_service import current_user, login_required

bp = Blueprint("home", __name__)


@bp.route("/")
@login_required
def dashboard():
    user = current_user()

    cards = {
        "pending_tasks": Task.query.filter(
            Task.assignee_id == user.id, Task.status.in_(["Open", "In Progress"])
        ).count(),
        "pending_approvals": Invoice.query.filter_by(status="Pending Approval").count(),
        "open_matters": Matter.query.filter(
            Matter.matter_manager_id == user.id,
            Matter.status.in_(["Draft", "Pending Allocation", "Open", "On Hold"]),
        ).count(),
        "pending_invoices": Invoice.query.filter(
            Invoice.status.in_(["Draft", "Pending Approval"])
        ).count(),
    }

    newest_matters = Matter.query.order_by(Matter.created_at.desc()).limit(5).all()
    recent_activity = Activity.query.order_by(Activity.created_at.desc()).limit(8).all()

    return render_template(
        "home.html",
        cards=cards,
        newest_matters=newest_matters,
        recent_activity=recent_activity,
    )
