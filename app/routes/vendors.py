from datetime import datetime
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Vendor, User, Comment, Participant, AppSetting, Activity
from app.services.auth_service import current_user, login_required

# Assuming log_activity handles kwargs generically. 
# If not, you may need to update matter_service.py to accept 'vendor='
from app.services.matter_service import log_activity 

bp = Blueprint("vendors", __name__, url_prefix="/vendors")

# --- DYNAMIC GRID CONFIGURATION ---
GRID_COLUMNS = [
    # Default Visible Columns
    {"key": "id", "label": "ID", "default": True, "type": "integer"},
    {"key": "name", "label": "Vendor Name", "default": True, "type": "link"},
    {"key": "vendor_type", "label": "Type", "default": True, "type": "text"},
    {"key": "currency_code", "label": "Currency", "default": True, "type": "text"},
    {"key": "status", "label": "Status", "default": True, "type": "badge"},
    
    # Optional / Hidden Columns (Available in Select Fields)
    {"key": "storm_third_party_id", "label": "STORM Third Party ID", "default": False, "type": "text"},
    {"key": "storm_engagement_id_1", "label": "STORM Engagement ID #1", "default": False, "type": "text"},
    {"key": "storm_engagement_id_2", "label": "STORM Engagement ID #2", "default": False, "type": "text"},
    {"key": "tax_status_type", "label": "Tax Status Type", "default": False, "type": "text"},
    {"key": "manual_invoices_only", "label": "Manual Invoices Only", "default": False, "type": "boolean"},
    {"key": "discounts_applicable", "label": "Discounts Applicable", "default": False, "type": "boolean"},
    {"key": "country", "label": "Country", "default": False, "type": "text"},
    {"key": "postal_code", "label": "Postal Code", "default": False, "type": "text"},
    {"key": "relationship_partner_name", "label": "Partner Name", "default": False, "type": "text"},
    {"key": "relationship_partner_email", "label": "Partner Email", "default": False, "type": "text"},
    {"key": "relationship_partner_phone", "label": "Partner Phone", "default": False, "type": "text"},
    {"key": "outside_counsel_email", "label": "Outside Counsel Email", "default": False, "type": "text"},
    {"key": "billing_contact_1_name", "label": "Billing Contact 1 Name", "default": False, "type": "text"},
    {"key": "billing_contact_1_email", "label": "Billing Contact 1 Email", "default": False, "type": "text"},
    {"key": "billing_contact_1_phone", "label": "Billing Contact 1 Phone", "default": False, "type": "text"},
    {"key": "billing_contact_2_name", "label": "Billing Contact 2 Name", "default": False, "type": "text"},
    {"key": "billing_contact_2_email", "label": "Billing Contact 2 Email", "default": False, "type": "text"},
    {"key": "billing_contact_2_phone", "label": "Billing Contact 2 Phone", "default": False, "type": "text"},
    {"key": "billing_contact_3_name", "label": "Billing Contact 3 Name", "default": False, "type": "text"},
    {"key": "billing_contact_3_email", "label": "Billing Contact 3 Email", "default": False, "type": "text"},
    {"key": "billing_contact_3_phone", "label": "Billing Contact 3 Phone", "default": False, "type": "text"},
    {"key": "migrated", "label": "Migrated Data", "default": True, "type": "boolean"},
    {"key": "created_at", "label": "Created At", "default": False, "type": "date"},
    {"key": "updated_at", "label": "Updated At", "default": False, "type": "date"}
]

def get_vendor_roles():
    setting = AppSetting.query.filter_by(key="vendor_roles").first()
    if setting and setting.value:
        return setting.value
    return ["Primary Contact", "Billing", "Account Manager"]

def get_vendor_statuses():
    setting = AppSetting.query.filter_by(key="vendor_statuses").first()
    if setting and setting.value:
        return setting.value
    return ["Active", "Pending Review", "Inactive"]

def _save_vendor(vendor: Vendor, form) -> bool:
    # Validate required fields
    required = {
        "name": "Vendor Name",
        "vendor_type": "Vendor Type",
        "billing_contact_1_name": "Billing Contact 1 Name",
        "billing_contact_1_email": "Billing Contact 1 Email"
    }
    
    errors = [f"{label} is required." for field, label in required.items() if not form.get(field, "").strip()]
    if errors:
        for error in errors:
            flash(error, "error")
        return False

    # Core
    vendor.name = form.get("name").strip()
    vendor.vendor_type = form.get("vendor_type").strip()
    
    # Financials
    vendor.storm_third_party_id = form.get("storm_third_party_id", "").strip() or None
    vendor.storm_engagement_id_1 = form.get("storm_engagement_id_1", "").strip() or None
    vendor.storm_engagement_id_2 = form.get("storm_engagement_id_2", "").strip() or None
    vendor.tax_status_type = form.get("tax_status_type", "").strip() or None
    vendor.currency_code = form.get("currency_code", "United States Dollar").strip()
    
    # Toggles (Checkboxes send "on" if checked, missing if unchecked)
    vendor.manual_invoices_only = form.get("manual_invoices_only") == "on"
    vendor.discounts_applicable = form.get("discounts_applicable") == "on"
    
    # Location
    vendor.country = form.get("country", "").strip() or None
    vendor.postal_code = form.get("postal_code", "").strip() or None
    
    # Relationship Partner
    vendor.relationship_partner_name = form.get("relationship_partner_name", "").strip() or None
    vendor.relationship_partner_email = form.get("relationship_partner_email", "").strip() or None
    vendor.relationship_partner_phone = form.get("relationship_partner_phone", "").strip() or None
    
    # Outside Counsel
    vendor.outside_counsel_email = form.get("outside_counsel_email", "").strip() or None
    
    # Billing Contacts
    vendor.billing_contact_1_name = form.get("billing_contact_1_name", "").strip()
    vendor.billing_contact_1_email = form.get("billing_contact_1_email", "").strip()
    vendor.billing_contact_1_phone = form.get("billing_contact_1_phone", "").strip() or None
    
    vendor.billing_contact_2_name = form.get("billing_contact_2_name", "").strip() or None
    vendor.billing_contact_2_email = form.get("billing_contact_2_email", "").strip() or None
    vendor.billing_contact_2_phone = form.get("billing_contact_2_phone", "").strip() or None
    
    vendor.billing_contact_3_name = form.get("billing_contact_3_name", "").strip() or None
    vendor.billing_contact_3_email = form.get("billing_contact_3_email", "").strip() or None
    vendor.billing_contact_3_phone = form.get("billing_contact_3_phone", "").strip() or None

    is_new = vendor.id is None
    if not is_new and form.get("status"):
        vendor.status = form.get("status")

    try:
        db.session.add(vendor)
        db.session.flush()
        log_activity(
            "Vendor Created" if is_new else "Vendor Updated",
            f"Vendor '{vendor.name}' details saved",
            vendor=vendor,
            user=current_user()
        )
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        flash("The vendor could not be saved. Please try again.", "error")
        return False


@bp.route("/")
@login_required
def list_vendors():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    if per_page not in [10, 50, 100, 200]: per_page = 10

    query = Vendor.query
    if search:
        query = query.filter(Vendor.name.ilike(f"%{search}%"))
    if status:
        query = query.filter_by(status=status)

    pagination = query.order_by(Vendor.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "vendors/list.html",
        pagination=pagination,
        vendors=pagination.items,
        search=search,
        status=status,
        statuses=get_vendor_statuses(),
        grid_columns=GRID_COLUMNS,
    )

@bp.route("/new", methods=["POST"])
@login_required
def new_vendor():
    vendor = Vendor(status="Active")
    if _save_vendor(vendor, request.form):
        flash(f"Vendor '{vendor.name}' created successfully.", "success")
        return redirect(url_for("vendors.vendor_detail", vendor_id=vendor.id))
    return redirect(url_for("vendors.list_vendors"))

@bp.route("/<int:vendor_id>")
@login_required
def vendor_detail(vendor_id):
    # Local imports to prevent circular dependencies
    from app.routes.matters import GRID_COLUMNS as MATTER_GRID_COLUMNS
    from app.routes.vatms import GRID_COLUMNS as VATM_GRID_COLUMNS
    
    vendor = Vendor.query.get(vendor_id) or abort(404)
    
    # Extract unique matters linked to this vendor via their assignments
    vendor_matters = []
    if hasattr(vendor, 'vendor_assignments'):
        # Use a dictionary to keep matters unique in case multiple assignments link to the same matter
        unique_matters = {vatm.matter.id: vatm.matter for vatm in vendor.vendor_assignments if vatm.matter}
        vendor_matters = list(unique_matters.values())
        
    return render_template(
        "vendors/detail.html",
        vendor=vendor,
        vendor_statuses=get_vendor_statuses(),
        participant_roles=get_vendor_roles(),
        vatm_grid_columns=VATM_GRID_COLUMNS,
        matter_grid_columns=MATTER_GRID_COLUMNS,
        vendor_matters=vendor_matters
    )

@bp.route("/<int:vendor_id>/update", methods=["POST"])
@login_required
def update(vendor_id):
    vendor = Vendor.query.get(vendor_id) or abort(404)
    if _save_vendor(vendor, request.form):
        flash("Vendor details updated successfully.", "success")
    return redirect(url_for("vendors.vendor_detail", vendor_id=vendor.id))

@bp.route("/<int:vendor_id>/status", methods=["POST"])
@login_required
def change_status(vendor_id):
    vendor = Vendor.query.get(vendor_id) or abort(404)
    status = request.form.get("status", "")

    if status not in get_vendor_statuses():
        flash("Unknown vendor status.", "error")
        return redirect(url_for("vendors.vendor_detail", vendor_id=vendor.id))

    previous, vendor.status = vendor.status, status
    log_activity("Status Changed", f"Status changed from {previous} to {status}", vendor=vendor, user=current_user())
    db.session.commit()
    flash(f"Vendor status updated to {status}.", "success")
    return redirect(url_for("vendors.vendor_detail", vendor_id=vendor.id))

@bp.route("/<int:vendor_id>/comments", methods=["POST"])
@login_required
def post_comment(vendor_id):
    vendor = Vendor.query.get(vendor_id) or abort(404)
    text = request.form.get("comment_text", "").strip()
    if not text:
        flash("Comment cannot be empty.", "error")
        return redirect(url_for("vendors.vendor_detail", vendor_id=vendor.id))

    db.session.add(Comment(vendor_id=vendor.id, author_id=current_user().id, comment_text=text))
    log_activity("Comment Posted", text, vendor=vendor, user=current_user())
    db.session.commit()
    flash("Comment posted.", "success")
    return redirect(url_for("vendors.vendor_detail", vendor_id=vendor.id))

@bp.route("/<int:vendor_id>/participants", methods=["POST"])
@login_required
def add_participant(vendor_id):
    vendor = Vendor.query.get(vendor_id) or abort(404)
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    role = request.form.get("role", "").strip()

    if not (name and email and role):
        flash("Name, email and role are required.", "error")
        return redirect(url_for("vendors.vendor_detail", vendor_id=vendor.id))

    db.session.add(Participant(vendor_id=vendor.id, name=name, email=email, role=role))
    log_activity("Participant Added", f"{name} added as {role}", vendor=vendor, user=current_user())
    db.session.commit()
    flash("Participant added.", "success")
    return redirect(url_for("vendors.vendor_detail", vendor_id=vendor.id))

@bp.route("/bulk-delete", methods=["POST"])
@login_required
def bulk_delete():
    try:
        data = request.get_json()
        raw_ids = data.get("ids", [])
        if not raw_ids:
            return {"success": False, "error": "No vendors selected."}, 400
            
        vendor_ids = [int(vid) for vid in raw_ids]
        vendors_to_delete = Vendor.query.filter(Vendor.id.in_(vendor_ids)).all()
        
        for vendor in vendors_to_delete:
            # Drop child records safely
            for participant in vendor.participants: db.session.delete(participant)
            for comment in vendor.comments: db.session.delete(comment)
            for activity in vendor.activities: db.session.delete(activity)
            db.session.delete(vendor)
            
        db.session.commit()
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}, 500