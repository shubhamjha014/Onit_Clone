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

from app.extensions import db
from app.models import Allocation, Comment, Matter, Participant, User
from app.models.activity import PARTICIPANT_ROLES
from app.models.matter import (
    AREAS_OF_LAW,
    CURRENCIES,
    LEGAL_ENTITIES,
    MARKETS,
    MATTER_STATUSES,
    MATTER_TYPES,
    PAYMENT_METHODS,
    REGIONS,
)
from app.services.auth_service import current_user, login_required
from app.services.matter_service import generate_matter_number, log_activity

bp = Blueprint("matters", __name__, url_prefix="/matters")

PAGE_SIZE = 10


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
        "areas_of_law": AREAS_OF_LAW,
        "regions": REGIONS,
        "matter_types": MATTER_TYPES,
        "legal_entities": LEGAL_ENTITIES,
        "currencies": CURRENCIES,
        "statuses": MATTER_STATUSES,
        "payment_methods": PAYMENT_METHODS,
    }


@bp.route("/")
@login_required
def list_matters():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    area = request.args.get("area_of_law", "")
    page = request.args.get("page", 1, type=int)

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

    pagination = query.order_by(Matter.created_at.desc()).paginate(
        page=page, per_page=PAGE_SIZE, error_out=False
    )

    return render_template(
        "matters/list.html",
        pagination=pagination,
        matters=pagination.items,
        search=search,
        status=status,
        area=area,
        statuses=MATTER_STATUSES,
        areas_of_law=AREAS_OF_LAW,
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
    return render_template(
        "matters/detail.html",
        matter=matter,
        statuses=MATTER_STATUSES,
        participant_roles=PARTICIPANT_ROLES,
        activities=sorted(matter.activities, key=lambda a: a.created_at, reverse=True),
        comments=sorted(matter.comments, key=lambda c: c.created_at, reverse=True),
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
    log_activity(
        "Allocation Added",
        f"Allocation added for {department}",
        matter=matter,
        user=current_user(),
    )
    db.session.commit()
    flash("Allocation added.", "success")
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
        "Comment Posted", "New comment posted", matter=matter, user=current_user()
    )
    db.session.commit()
    flash("Comment posted.", "success")
    return redirect(url_for("matters.matter_detail", matter_id=matter.id))


@bp.route("/<int:matter_id>/status", methods=["POST"])
@login_required
def change_status(matter_id):
    matter = Matter.query.get(matter_id) or abort(404)
    status = request.form.get("status", "")

    if status not in MATTER_STATUSES:
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
