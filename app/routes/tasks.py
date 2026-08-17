from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Matter, Task, User
from app.models.task import TASK_PRIORITIES, TASK_STATUSES
from app.services.auth_service import current_user, login_required
from app.services.matter_service import log_activity

bp = Blueprint("tasks", __name__, url_prefix="/tasks")

PAGE_SIZE = 10


def _parse_date(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _choices():
    return {
        "matters": Matter.query.order_by(Matter.matter_number.desc()).all(),
        "users": User.query.order_by(User.name).all(),
        "statuses": TASK_STATUSES,
        "priorities": TASK_PRIORITIES,
    }


@bp.route("/")
@login_required
def list_tasks():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    page = request.args.get("page", 1, type=int)

    query = Task.query
    if search:
        query = query.filter(Task.title.ilike(f"%{search}%"))
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)

    pagination = query.order_by(Task.due_date.is_(None), Task.due_date).paginate(
        page=page, per_page=PAGE_SIZE, error_out=False
    )

    return render_template(
        "tasks/list.html",
        pagination=pagination,
        tasks=pagination.items,
        search=search,
        status=status,
        priority=priority,
        statuses=TASK_STATUSES,
        priorities=TASK_PRIORITIES,
    )


def _save_task(task: Task, form) -> bool:
    if not form.get("title", "").strip():
        flash("Task Name is required.", "error")
        return False

    task.title = form["title"].strip()
    task.matter_id = int(form["matter_id"]) if form.get("matter_id") else None
    task.assignee_id = int(form["assignee_id"]) if form.get("assignee_id") else None
    task.description = form.get("description", "").strip() or None
    task.due_date = _parse_date(form.get("due_date", ""))
    task.priority = form.get("priority") or "Medium"
    task.status = form.get("status") or "Open"

    is_new = task.id is None
    try:
        db.session.add(task)
        db.session.flush()
        if task.matter:
            log_activity(
                "Task Created" if is_new else "Task Updated",
                f"Task '{task.title}' is {task.status}",
                matter=task.matter,
                user=current_user(),
            )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash("The task could not be saved. Please try again.", "error")
        return False
    return True


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_task():
    if request.method == "POST":
        task = Task()
        if _save_task(task, request.form):
            flash("Task created.", "success")
            return redirect(url_for("tasks.list_tasks"))
        return render_template(
            "tasks/form.html", form=request.form, task=None, **_choices()
        ), 400

    return render_template("tasks/form.html", form={}, task=None, **_choices())


@bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = Task.query.get(task_id) or abort(404)

    if request.method == "POST":
        if _save_task(task, request.form):
            flash("Task updated.", "success")
            return redirect(url_for("tasks.list_tasks"))
        return render_template(
            "tasks/form.html", form=request.form, task=task, **_choices()
        ), 400

    return render_template(
        "tasks/form.html", form=task.__dict__, task=task, **_choices()
    )
