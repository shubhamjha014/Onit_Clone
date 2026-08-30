from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Matter, Task, User, Comment, Participant, AppSetting
from app.models.task import TASK_PRIORITIES
from app.services.auth_service import current_user, login_required
from app.services.matter_service import log_activity

bp = Blueprint("tasks", __name__, url_prefix="/tasks")

GRID_COLUMNS = [
    {"key": "id", "label": "ID", "default": True, "type": "integer"},
    {"key": "title", "label": "Title", "default": True, "type": "link"},
    {"key": "matter_id", "label": "Matter ID", "default": True, "type": "integer"},
    {"key": "assignee_id", "label": "Assignee", "default": True, "type": "integer"},
    {"key": "description", "label": "Description", "default": True, "type": "text"},
    {"key": "due_date", "label": "Due Date", "default": True, "type": "date"},
    {"key": "priority", "label": "Priority", "default": True, "type": "text"},
    {"key": "status", "label": "Status", "default": True, "type": "badge"},
    {"key": "migrated", "label": "Migrated Data", "default": True, "type": "boolean"},
    {"key": "created_at", "label": "Created At", "default": False, "type": "date"},
    {"key": "updated_at", "label": "Updated At", "default": False, "type": "date"}
]

def get_participant_roles():
    """Fetches the latest participant roles directly from the JSON database column."""
    setting = AppSetting.query.filter_by(key="task_roles").first()
    # Returns the dynamic list, or a safe fallback if the database is empty
    if setting and setting.value:
        return setting.value
    return ["Requester"]

def get_task_statuses():
    """Fetches the latest matter statuses directly from the JSON database column."""
    setting = AppSetting.query.filter_by(key="task_statuses").first()
    if setting and setting.value:
        return setting.value
    return ["Pending Allocation"]

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
        "statuses": get_task_statuses(),
        "priorities": TASK_PRIORITIES,
    }


@bp.route("/")
@login_required
def list_tasks():
    #task = Task.query.get(task.id) or abort(404)
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    
    # 1. Grab page and per_page dynamically (Defaulting to 10 rows)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    
    # Safely restrict dropdown values to prevent UI tampering
    if per_page not in [10, 50, 100, 200]:
        per_page = 10

    query = Task.query
    if search:
        query = query.filter(Task.title.ilike(f"%{search}%"))
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)

    # 2. Pass per_page directly into the standard SQLAlchemy query
    pagination = query.order_by(Task.due_date.is_(None), Task.due_date).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    choices = _choices()
    return render_template(
        "tasks/list.html",
        pagination=pagination, # Passes the native object seamlessly!
        tasks=pagination.items,
        search=search,
        status=status,
        priority=priority,
        statuses=get_task_statuses(),
        priorities=TASK_PRIORITIES,
        grid_columns=GRID_COLUMNS,
        users=choices["users"],
        matters=choices["matters"],
    )

'''
@bp.route("/<int:task_id>/", methods=["POST"])
@login_required
def add_task(task_id):
    task = Task.query.get(task_id) or abort(404)
    title = request.form.get("title", "").strip()

    if not title:
        flash("Task title is required.", "error")
        return redirect(url_for("tasks"))

    assignee_id_raw = request.form.get("assignee_id")
    assignee_id = int(assignee_id_raw) if assignee_id_raw else None
    
    due_date_raw = request.form.get("due_date")
    due_date = _parse_date(due_date_raw) if due_date_raw else None

    new_task = Task(
        title=title,
        task_id=task.id,
        assignee_id=assignee_id,
        description=request.form.get("description", "").strip() or None,
        due_date=due_date,
        priority=request.form.get("priority") or "Medium",
        status=request.form.get("status") or "Open"
    )
    
    db.session.add(new_task)
    log_activity("Task Added", f"Task created: {title}", task=task, user=current_user())
    db.session.commit()
    
    flash("Task added successfully.", "success")
    return redirect(url_for("tasks"))
'''

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

'''
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
'''
@bp.route("/bulk-delete", methods=["POST"])
@login_required
def bulk_delete():
    try:
        data = request.get_json()
        raw_ids = data.get("ids", [])
        
        if not raw_ids:
            return {"success": False, "error": "No tasks selected."}, 400
            
        # Add this line to convert the JS strings into Python integers!
        task_ids = [int(tid) for tid in raw_ids]
            
        # Find all tasks that match the selected IDs and delete them
        Task.query.filter(Task.id.in_(task_ids)).delete(synchronize_session=False)
        db.session.commit()
        
        return {"success": True}
        
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}, 500


@bp.route("/<int:task_id>/status", methods=["POST"])
@login_required
def change_status(task_id):
    task = Task.query.get(task_id) or abort(404)
    status = request.form.get("status", "")

    if status not in get_task_statuses():
        flash("Unknown matter status.", "error")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    previous, task.status = task.status, status
    log_activity(
        "Status Changed",
        f"Status changed from {previous} to {status}",
        task=task,
        user=current_user(),
    )
    db.session.commit()
    flash(f"Matter status updated to {status}.", "success")
    return redirect(url_for("tasks.task_detail", task_id=task.id))

@bp.route("/<int:task_id>")
@login_required
def task_detail(task_id):
    # Local import to prevent circular dependencies
    from app.routes.matters import GRID_COLUMNS as MATTER_GRID_COLUMNS

    task = Task.query.get(task_id) or abort(404)
    # This ensures the Assignee dropdown populates!
    users = User.query.order_by(User.name).all()
    
    return render_template(
        "tasks/detail.html",
        task=task,
        users=users,
        priorities=TASK_PRIORITIES,
        task_statuses=get_task_statuses(),
        participant_roles=get_participant_roles(),
        matter_grid_columns=MATTER_GRID_COLUMNS, # <--- Added
    )

@bp.route("/<int:task_id>/comments", methods=["POST"])
@login_required
def post_comment(task_id):
    task = Task.query.get(task_id) or abort(404)
    text = request.form.get("comment_text", "").strip()

    if not text:
        flash("Comment cannot be empty.", "error")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    db.session.add(
        Comment(task_id=task.id, author_id=current_user().id, comment_text=text)
    )
    log_activity(
        "Comment Posted", text, task=task, user=current_user()
    )
    db.session.commit()
    flash("Comment posted.", "success")
    return redirect(url_for("tasks.task_detail", task_id=task.id))
@bp.route("/<int:task_id>/update", methods=["POST"])
@login_required
def update(task_id):
    task = Task.query.get(task_id) or abort(404)
    
    # We can reuse the awesome _save_task helper you already built!
    if _save_task(task, request.form):
        flash("Task details updated successfully.", "success")
        
    return redirect(url_for("tasks.task_detail", task_id=task.id))


@bp.route("/<int:task_id>/participants", methods=["POST"])
@login_required
def add_participant(task_id):
    task = Task.query.get(task_id) or abort(404)
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    role = request.form.get("role", "").strip()

    if not (name and email and role):
        flash("Name, email and role are required.", "error")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    db.session.add(
        Participant(task_id=task.id, name=name, email=email, role=role)
    )
    log_activity(
        "Participant Added", f"{name} added as {role}", task=task, user=current_user()
    )
    db.session.commit()
    flash("Participant added.", "success")
    return redirect(url_for("tasks.task_detail", task_id=task.id))