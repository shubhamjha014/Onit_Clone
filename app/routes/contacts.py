from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Contact
from app.models.contact import CONTACT_TYPES
from app.services.auth_service import login_required

bp = Blueprint("contacts", __name__, url_prefix="/contacts")

# --- DYNAMIC GRID CONFIGURATION ---
GRID_COLUMNS = [
    {"key": "id", "label": "ID", "default": False, "type": "integer"},
    {"key": "name", "label": "Contact Name", "default": True, "type": "link"},
    {"key": "email", "label": "Email", "default": True, "type": "text"},
    {"key": "phone", "label": "Phone", "default": True, "type": "text"},
    {"key": "organization", "label": "Organization", "default": True, "type": "text"},
    {"key": "role", "label": "Role", "default": True, "type": "text"},
    {"key": "contact_type", "label": "Contact Type", "default": True, "type": "text"},
    {"key": "created_at", "label": "Created At", "default": True, "type": "date"},
    {"key": "updated_at", "label": "Updated At", "default": False, "type": "date"}
]

@bp.route("/")
@login_required
def list_contacts():
    search = request.args.get("q", "").strip()
    contact_type = request.args.get("contact_type", "")
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    if per_page not in [10, 50, 100, 200]: per_page = 10

    query = Contact.query
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Contact.name.ilike(like),
                Contact.email.ilike(like),
                Contact.organization.ilike(like),
            )
        )
    if contact_type:
        query = query.filter_by(contact_type=contact_type)

    pagination = query.order_by(Contact.name).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "contacts/list.html",
        pagination=pagination,
        contacts=pagination.items,
        search=search,
        contact_type=contact_type,
        contact_types=CONTACT_TYPES,
        grid_columns=GRID_COLUMNS,
        form={}
    )

def _save_contact(contact: Contact, form) -> bool:
    errors = []
    if not form.get("name", "").strip():
        errors.append("Contact Name is required.")
    if not form.get("email", "").strip():
        errors.append("Email is required.")

    if errors:
        for error in errors:
            flash(error, "error")
        return False

    contact.name = form["name"].strip()
    contact.email = form["email"].strip()
    contact.phone = form.get("phone", "").strip() or None
    contact.organization = form.get("organization", "").strip() or None
    contact.role = form.get("role", "").strip() or None
    contact.contact_type = form.get("contact_type") or "Internal"

    try:
        db.session.add(contact)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash("The contact could not be saved. Please try again.", "error")
        return False
    return True

@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_contact():
    if request.method == "POST":
        contact = Contact()
        if _save_contact(contact, request.form):
            flash("Contact created successfully.", "success")
            return redirect(request.referrer or url_for("contacts.list_contacts"))
        return redirect(request.referrer or url_for("contacts.list_contacts"))
        
    # Legacy GET support
    return render_template("contacts/form.html", form={}, contact_types=CONTACT_TYPES, contact=None)

@bp.route("/<int:contact_id>")
@login_required
def contact_detail(contact_id):
    contact = Contact.query.get(contact_id) or abort(404)
    return render_template(
        "contacts/detail.html", 
        contact=contact,
        contact_types=CONTACT_TYPES
    )

@bp.route("/<int:contact_id>/update", methods=["POST"])
@login_required
def update_contact(contact_id):
    contact = Contact.query.get(contact_id) or abort(404)
    if _save_contact(contact, request.form):
        flash("Contact details updated successfully.", "success")
    return redirect(url_for("contacts.contact_detail", contact_id=contact.id))

# Legacy edit route
@bp.route("/<int:contact_id>/edit", methods=["GET", "POST"])
@login_required
def edit_contact(contact_id):
    contact = Contact.query.get(contact_id) or abort(404)
    if request.method == "POST":
        if _save_contact(contact, request.form):
            flash("Contact updated.", "success")
            return redirect(url_for("contacts.contact_detail", contact_id=contact.id))
    return render_template("contacts/form.html", form=contact.__dict__, contact_types=CONTACT_TYPES, contact=contact)

@bp.route("/bulk-delete", methods=["POST"])
@login_required
def bulk_delete():
    try:
        data = request.get_json()
        raw_ids = data.get("ids", [])
        if not raw_ids:
            return {"success": False, "error": "No contacts selected."}, 400
            
        contact_ids = [int(cid) for cid in raw_ids]
        Contact.query.filter(Contact.id.in_(contact_ids)).delete(synchronize_session=False)
        db.session.commit()
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}, 500