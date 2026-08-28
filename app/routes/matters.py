from datetime import datetime

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_, text # <--- Add text here

from app.extensions import db
from app.models import Allocation, Comment, Matter, Participant, User, Task
from app.models.matter import (
    CURRENCIES,
    LEGAL_ENTITIES,
    MARKETS,
    MATTER_TYPES,
    PAYMENT_METHODS,
    REGIONS,
)
from app.models.task import TASK_PRIORITIES
from app.models.app_setting import AppSetting

from app.routes.tasks import get_task_statuses
from app.services.auth_service import current_user, login_required
from app.services.matter_service import generate_matter_number, log_activity

bp = Blueprint("matters", __name__, url_prefix="/matters")

# --- DYNAMIC GRID CONFIGURATION ---
# Add new database fields here and they will automatically appear in the UI, Filters, and Modal!
GRID_COLUMNS = [
    {"key": "matter_number", "label": "Matter Number", "default": True, "type": "link"},
    {"key": "matter_name", "label": "Matter Name", "default": True, "type": "text"},
    {"key": "market", "label": "Market", "default": True, "type": "text"},
    {"key": "area_of_law", "label": "Area of Law", "default": True, "type": "text"},
    {"key": "matter_type", "label": "Matter Type", "default": True, "type": "text"},
    {"key": "manager", "label": "Matter Manager", "default": True, "type": "manager"},
    {"key": "legal_entity", "label": "Legal Entity", "default": True, "type": "text"},
    {"key": "currency", "label": "Currency", "default": True, "type": "text"},
    {"key": "status", "label": "Status", "default": True, "type": "badge"},
    {"key": "opened_on", "label": "Opened On", "default": True, "type": "date"},
    {"key": "brief_description", "label": "Brief Description", "default": False, "type": "text"},
    {"key": "region", "label": "Region", "default": False, "type": "text"},
    {"key": "payment_method", "label": "Payment Method", "default": False, "type": "text"},
    {"key": "invoice_total", "label": "Invoice Total", "default": False, "type": "currency"},
    {"key": "total_budget", "label": "Total Budget", "default": False, "type": "currency"},
    {"key": "created_at", "label": "Created At", "default": False, "type": "date"},
    {"key": "updated_at", "label": "Updated At", "default": False, "type": "date"}
]

def get_participant_roles():
    """Fetches the latest participant roles directly from the JSON database column."""
    setting = AppSetting.query.filter_by(key="matter_roles").first()
    # Returns the dynamic list, or a safe fallback if the database is empty
    if setting and setting.value:
        return setting.value
    return ["Requester", "Matter Manager", "Attorney", "Paralegal"]

def get_matter_statuses():
    """Fetches the latest matter statuses directly from the JSON database column."""
    setting = AppSetting.query.filter_by(key="matter_statuses").first()
    if setting and setting.value:
        return setting.value
    return ["Pending Allocation", "In Progress", "Closed"]

def get_areas_of_law():
    """Fetches areas of law dynamically from the uploaded list_area_of_law table."""
    try:
        with db.engine.connect() as conn:
            # Query the dynamic table. We assume the Excel column header was "Area of Law", 
            # which the backend sanitized to 'area_of_law'.
            result = conn.execute(text("SELECT area_of_law FROM list_area_of_law"))
            
            # Extract the values from the first column of the results
            areas = [row[0] for row in result if row[0]]
            
            if areas:
                return areas
    except Exception:
        # Failsafe fallback: If the user hasn't uploaded the Excel file yet, 
        # or the table was deleted, provide these defaults so the app doesn't crash.
        pass
        
    return ["Corporate Legal", "Employment", "Litigation", "Real Estate"]


def _parse_date(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _form_choices():
    return {
        "managers": User.query.order_by(User.name).all(),
        "markets": MARKETS,
        "areas_of_law": get_areas_of_law(),
        "regions": REGIONS,
        "matter_types": MATTER_TYPES,
        "legal_entities": LEGAL_ENTITIES,
        "currencies": CURRENCIES,
        "statuses": get_matter_statuses(),
        "payment_methods": PAYMENT_METHODS,
    }


@bp.route("/")
@login_required
def list_matters():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    area = request.args.get("area_of_law", "")
    
    # 1. Grab page and per_page dynamically (Defaulting to 10 rows)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    
    # Safely restrict dropdown values to prevent UI tampering
    if per_page not in [10, 50, 100, 200]:
        per_page = 10

    query = Matter.query
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Matter.matter_name.ilike(like), Matter.matter_number.ilike(like))
        )
    if status:
        query = query.filter_by(status=status)
    if area:
        query = query.filter_by(area_of_law=area)

    # 2. Pass per_page directly into the standard SQLAlchemy query
    pagination = query.order_by(Matter.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        "matters/list.html",
        pagination=pagination, # Passes the native object seamlessly!
        matters=pagination.items,
        search=search,
        status=status,
        area=area,
        statuses=get_matter_statuses(),
        areas_of_law=get_areas_of_law(),
        grid_columns=GRID_COLUMNS,
    )


@bp.route("/new", methods=["POST"])
@login_required
def new_matter():
    form = request.form
    required = {
        "matter_manager_id": "Matter Manager",
        "matter_name": "Matter Name",
        "market": "Market",
        "area_of_law": "Area of Law",
        "matter_type": "Matter Type",
        "legal_entity": "Legal Entity",
        "currency": "Matter Currency",
    }
    errors = [
        f"{label} is required."
        for field, label in required.items()
        if not form.get(field, "").strip()
    ]

    referrer = request.referrer or url_for("matters.list_matters")

    if errors:
        for error in errors:
            flash(error, "error")
        return redirect(referrer)

    matter = Matter(
        matter_number=generate_matter_number(),
        matter_name=form["matter_name"].strip(),
        matter_manager_id=int(form["matter_manager_id"]),
        opened_on=_parse_date(form.get("opened_on", "")) or datetime.utcnow().date(),
        brief_description=form.get("brief_description", "").strip() or None,
        market=form["market"],
        area_of_law=form["area_of_law"],
        region=form.get("region") or None,
        matter_type=form["matter_type"],
        legal_entity=form["legal_entity"],
        currency=form["currency"],
        payment_method=form.get("payment_method") or None,
        total_budget=form.get("total_budget") or 0,
        status="Pending Allocation",
    )

    try:
        db.session.add(matter)
        db.session.flush()
        db.session.add(
            Participant(
                matter_id=matter.id,
                name=current_user().name,
                email=current_user().email,
                role="Requester",
            )
        )
        log_activity(
            "Matter Created",
            f"Matter {matter.matter_number} created",
            matter=matter,
            user=current_user(),
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash("The matter could not be saved. Please try again.", "error")
        return redirect(referrer)

    flash(f"Matter {matter.matter_number} created successfully.", "success")
    return redirect(url_for("matters.matter_detail", matter_id=matter.id))

@bp.route("/<int:matter_id>")
@login_required
def matter_detail(matter_id):
    matter = Matter.query.get(matter_id) or abort(404)
    # This ensures the Assignee dropdown populates!
    users = User.query.order_by(User.name).all()
    return render_template(
        "matters/detail.html",
        matter=matter,
        statuses=get_matter_statuses(),
        participant_roles=get_participant_roles(),
        areas_of_law=get_areas_of_law(),
        activities=sorted(matter.activities, key=lambda a: a.created_at, reverse=True),
        comments=sorted(matter.comments, key=lambda c: c.created_at, reverse=True),
        users=users,
        priorities=TASK_PRIORITIES,
        task_statuses=get_task_statuses(),
    )


@bp.route("/<int:matter_id>/participants", methods=["POST"])
@login_required
def add_participant(matter_id):
    matter = Matter.query.get(matter_id) or abort(404)
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    role = request.form.get("role", "").strip()

    if not (name and email and role):
        flash("Name, email and role are required to add a participant.", "error")
        return redirect(url_for("matters.matter_detail", matter_id=matter.id))

    db.session.add(
        Participant(matter_id=matter.id, name=name, email=email, role=role)
    )
    log_activity(
        "Participant Added",
        f"{name} added as {role}",
        matter=matter,
        user=current_user(),
    )
    db.session.commit()
    flash("Participant added.", "success")
    return redirect(url_for("matters.matter_detail", matter_id=matter.id))


@bp.route("/<int:matter_id>/allocations", methods=["POST"])
@login_required
def add_allocation(matter_id):
    matter = Matter.query.get(matter_id) or abort(404)
    
    department = request.form.get("department", "").strip()

    if not department:
        flash("Department is required to add an allocation.", "error")
        return redirect(url_for("matters.matter_detail", matter_id=matter.id))

    db.session.add(
        Allocation(
            matter_id=matter.id,
            department=department,
            percentage=request.form.get("percentage") or None,
            amount=request.form.get("amount") or None,
            notes=request.form.get("notes", "").strip() or None,
        )
    )
    log_activity("Allocation Added", f"Allocation added for {department}", matter=matter, user=current_user())
    db.session.commit()
    flash("Allocation added.", "success")
    
    return redirect(url_for("matters.matter_detail", matter_id=matter.id))

# FIXED: We added "/task" and methods=["POST"] here!
@bp.route("/<int:matter_id>/task", methods=["POST"])
@login_required
def add_task(matter_id):
    matter = Matter.query.get(matter_id) or abort(404)
    title = request.form.get("title", "").strip()

    if not title:
        flash("Task title is required.", "error")
        return redirect(url_for("matters.matter_detail", matter_id=matter.id))

    assignee_id_raw = request.form.get("assignee_id")
    assignee_id = int(assignee_id_raw) if assignee_id_raw else None
    
    due_date_raw = request.form.get("due_date")
    due_date = _parse_date(due_date_raw) if due_date_raw else None

    new_task = Task(
        title=title,
        matter_id=matter.id,
        assignee_id=assignee_id,
        description=request.form.get("description", "").strip() or None,
        due_date=due_date,
        priority=request.form.get("priority") or "Medium",
        status=request.form.get("status") or "Open"
    )
    
    db.session.add(new_task)
    log_activity("Task Added", f"Task created: {title}", matter=matter, user=current_user())
    db.session.commit()
    
    flash("Task added successfully.", "success")
    return redirect(url_for("matters.matter_detail", matter_id=matter.id))

@bp.route("/<int:matter_id>/comments", methods=["POST"])
@login_required
def post_comment(matter_id):
    matter = Matter.query.get(matter_id) or abort(404)
    text = request.form.get("comment_text", "").strip()

    if not text:
        flash("Comment cannot be empty.", "error")
        return redirect(url_for("matters.matter_detail", matter_id=matter.id))

    db.session.add(
        Comment(matter_id=matter.id, author_id=current_user().id, comment_text=text)
    )
    log_activity(
        "Comment Posted", text, matter=matter, user=current_user()
    )
    db.session.commit()
    flash("Comment posted.", "success")
    return redirect(url_for("matters.matter_detail", matter_id=matter.id))


@bp.route("/<int:matter_id>/status", methods=["POST"])
@login_required
def change_status(matter_id):
    matter = Matter.query.get(matter_id) or abort(404)
    status = request.form.get("status", "")

    if status not in get_matter_statuses():
        flash("Unknown matter status.", "error")
        return redirect(url_for("matters.matter_detail", matter_id=matter.id))

    previous, matter.status = matter.status, status
    log_activity(
        "Status Changed",
        f"Status changed from {previous} to {status}",
        matter=matter,
        user=current_user(),
    )
    db.session.commit()
    flash(f"Matter status updated to {status}.", "success")
    return redirect(url_for("matters.matter_detail", matter_id=matter.id))

@bp.route("/<int:matter_id>/update", methods=["POST"])
@login_required
def update(matter_id):
    matter = Matter.query.get(matter_id) or abort(404)

    market = request.form.get("market", "").strip()
    region = request.form.get("region", "").strip()
    currency = request.form.get("currency", "").strip()

    # Update the matter
    matter.market = market
    matter.region = region or None
    matter.currency = currency

    try:
        log_activity(
            "Matter Updated",
            f"Matter {matter.matter_number} details updated",
            matter=matter,
            user=current_user(),
        )

        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()
        flash("The matter could not be updated. Please try again.", "error")
        return redirect(
            url_for("matters.matter_detail", matter_id=matter.id)
        )

    flash("Matter details updated successfully.", "success")

    return redirect(
        url_for("matters.matter_detail", matter_id=matter.id)
    )

@bp.route("/bulk_delete", methods=["POST"])
@login_required
def bulk_delete():
    data = request.get_json()
    raw_ids = data.get("ids", [])
    
    if not raw_ids:
        return {"error": "No records selected"}, 400

    # Convert the string IDs from the frontend into integers for strict databases (PostgreSQL)
    matter_ids = [int(mid) for mid in raw_ids]

    try:
        matters_to_delete = Matter.query.filter(Matter.id.in_(matter_ids)).all()
        
        for matter in matters_to_delete:
            # Manually delete all attached child records first to bypass DB schema locks
            for participant in matter.participants:
                db.session.delete(participant)
            for allocation in matter.allocations:
                db.session.delete(allocation)
            for comment in matter.comments:
                db.session.delete(comment)
            for activity in matter.activities:
                db.session.delete(activity)
            for invoice in matter.invoices:
                db.session.delete(invoice)
            for task in matter.tasks:
                db.session.delete(task)
                
            # Now that the matter is completely isolated, delete the matter itself
            db.session.delete(matter)
            
        # Log the bulk action
        log_activity(
            "Bulk Delete",
            f"Deleted {len(matters_to_delete)} matters",
            user=current_user(),
        )
        
        db.session.commit()
        return {"success": True, "message": f"{len(matter_ids)} records deleted successfully."}
    
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"\n--- DATABASE ERROR ---\n{str(e)}\n----------------------\n") 
        return {"error": "Failed to delete records due to attached data constraints or a database error."}, 500