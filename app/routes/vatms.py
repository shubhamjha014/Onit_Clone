from datetime import datetime
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import VendorAssignmentToMatter, Matter, Vendor, AppSetting, Comment, Participant
from app.services.auth_service import current_user, login_required
from app.services.matter_service import log_activity 

bp = Blueprint("vatms", __name__, url_prefix="/vendor-assignments")

# --- DYNAMIC GRID CONFIGURATION ---
GRID_COLUMNS = [
    # Default Visible Columns
    {"key": "id", "label": "ID", "default": True, "type": "integer"},
    {"key": "vatm_name", "label": "Assignment Name", "default": True, "type": "link_vatm"},
    {"key": "matter_name", "label": "Matter", "default": True, "type": "link_matter"},
    {"key": "vendor_name", "label": "Vendor", "default": True, "type": "link_vendor"},
    {"key": "funding_type", "label": "Funding Type", "default": True, "type": "text"},
    {"key": "vendor_role", "label": "Role", "default": True, "type": "text"},
    {"key": "fee_arrangement_value", "label": "Fee Arrangement", "default": True, "type": "text"},
    
    # Optional / Hidden Columns (Available in Select Fields)
    {"key": "division_law_firm_panel", "label": "Division Law Firm Panel", "default": False, "type": "text"},
    {"key": "default_vendor_gl_account_number", "label": "GL Account Number", "default": False, "type": "text"},
    {"key": "syndicate_fixed_fee_amount", "label": "Fixed Fee Amount", "default": False, "type": "currency"},
    {"key": "custom_international_panel", "label": "Custom Int. Panel", "default": False, "type": "boolean"},
    {"key": "panel_law_firms_only", "label": "Panel Law Firms Only", "default": False, "type": "boolean"},
    {"key": "subcontractor", "label": "Subcontractor", "default": False, "type": "boolean"},
    {"key": "migrated", "label": "Migrated Data", "default": True, "type": "boolean"},
    {"key": "created_at", "label": "Assigned On", "default": False, "type": "date"},
    {"key": "updated_at", "label": "Updated At", "default": False, "type": "date"}
]

def _get_setting(key, default_list):
    setting = AppSetting.query.filter_by(key=key).first()
    return setting.value if setting and setting.value else default_list

def get_vatm_choices():
    """Fetches all dropdown choices for the VATM form."""
    return {
        "matters": Matter.query.order_by(Matter.matter_name).all(),
        "vendors": Vendor.query.order_by(Vendor.name).all(),
        "funding_types": _get_setting("vatm_funding_types", ["Syndicate Funding Type", "Alternate Funding Type"]),
        "roles": _get_setting("vatm_roles", ["Lead Counsel", "Local Counsel"]),
        "gl_accounts": _get_setting("vatm_gl_accounts", ["GL-1000"]),
        "fee_arrangements": _get_setting("vatm_fee_arrangements", ["Fixed Fee", "Hourly"]),
    }

def _save_assignment(assignment: VendorAssignmentToMatter, form) -> bool:
    required = {
        "matter_id": "Matter",
        "vendor_id": "Panel Law Firm",
        "funding_type": "Funding Type",
        "vendor_role": "Vendor Role",
        "default_vendor_gl_account_number": "GL Account Number",
        "fee_arrangement_value": "Fee Arrangement"
    }
    
    errors = [f"{label} is required." for field, label in required.items() if not form.get(field, "").strip()]
    if errors:
        for error in errors: flash(error, "error")
        return False

    assignment.matter_id = int(form.get("matter_id"))
    assignment.vendor_id = int(form.get("vendor_id"))
    assignment.division_law_firm_panel = form.get("division_law_firm_panel", "").strip() or None
    assignment.funding_type = form.get("funding_type", "").strip()
    assignment.vendor_role = form.get("vendor_role", "").strip()
    assignment.default_vendor_gl_account_number = form.get("default_vendor_gl_account_number", "").strip()
    assignment.fee_arrangement_value = form.get("fee_arrangement_value", "").strip()
    
    fee = form.get("syndicate_fixed_fee_amount")
    assignment.syndicate_fixed_fee_amount = float(fee) if fee else None

    # Checkboxes
    assignment.custom_international_panel = form.get("custom_international_panel") == "on"
    assignment.panel_law_firms_only = form.get("panel_law_firms_only") == "on"
    assignment.subcontractor = form.get("subcontractor") == "on"

    matter = Matter.query.get(assignment.matter_id)
    vendor = Vendor.query.get(assignment.vendor_id)
    if matter and vendor:
        assignment.vatm_name = f"{vendor.name}/{matter.matter_name}"

    is_new = assignment.id is None
    try:
        db.session.add(assignment)
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        flash("The assignment could not be saved.", "error")
        return False


@bp.route("/")
@login_required
def list_assignments():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    if per_page not in [10, 50, 100, 200]: per_page = 10

    query = VendorAssignmentToMatter.query
    pagination = query.order_by(VendorAssignmentToMatter.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "vatms/list.html",
        pagination=pagination,
        assignments=pagination.items,
        grid_columns=GRID_COLUMNS,
        **get_vatm_choices()
    )

@bp.route("/new", methods=["POST"])
@login_required
def new_assignment():
    assignment = VendorAssignmentToMatter()
    if _save_assignment(assignment, request.form):
        flash("Vendor assigned successfully.", "success")
    # Smart redirect: Goes back to the Matter or Vendor page if launched from there!
    return redirect(request.referrer or url_for("vatms.list_assignments"))

@bp.route("/<int:assignment_id>")
@login_required
def assignment_detail(assignment_id):
    from app.routes.matters import GRID_COLUMNS as MATTER_GRID_COLUMNS
    from app.routes.vendors import GRID_COLUMNS as VENDOR_GRID_COLUMNS
    from app.routes.invoices import GRID_COLUMNS as INVOICE_GRID_COLUMNS
    from app.routes.invoices import _get_invoice_choices
    
    assignment = VendorAssignmentToMatter.query.get(assignment_id) or abort(404)
    
    # Extract invoices belonging exclusively to this assignment's Matter + Vendor
    vatm_invoices = [inv for inv in assignment.matter.invoices if inv.vendor_name == assignment.vendor.name] if assignment.matter else []
        
    return render_template(
        "vatms/detail.html", 
        assignment=assignment, 
        participant_roles=get_participant_roles(),
        matter_grid_columns=MATTER_GRID_COLUMNS,
        vendor_grid_columns=VENDOR_GRID_COLUMNS,
        invoice_grid_columns=INVOICE_GRID_COLUMNS,
        vatm_invoices=vatm_invoices,
        **get_vatm_choices(),
        invoice_choices = _get_invoice_choices()
    )

@bp.route("/<int:assignment_id>/update", methods=["POST"])
@login_required
def update_assignment(assignment_id):
    assignment = VendorAssignmentToMatter.query.get(assignment_id) or abort(404)
    if _save_assignment(assignment, request.form):
        flash("Assignment updated successfully.", "success")
    return redirect(url_for("vatms.assignment_detail", assignment_id=assignment.id))

@bp.route("/bulk-delete", methods=["POST"])
@login_required
def bulk_delete():
    try:
        data = request.get_json()
        raw_ids = data.get("ids", [])
        if not raw_ids:
            return {"success": False, "error": "No records selected."}, 400
            
        VendorAssignmentToMatter.query.filter(VendorAssignmentToMatter.id.in_([int(aid) for aid in raw_ids])).delete(synchronize_session=False)
        db.session.commit()
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}, 500

# --- SIDEBAR & STANDARD APP ROUTES ---

def get_participant_roles():
    """Helper to get standard participant roles for the sidebar."""
    return _get_setting("participant_roles", ["General Participant", "Reviewer", "Approver"])

@bp.route("/<int:assignment_id>/participant", methods=["POST"])
@login_required
def add_participant(assignment_id):
    assignment = VendorAssignmentToMatter.query.get(assignment_id) or abort(404)
    name = request.form.get("name")
    email = request.form.get("email")
    role = request.form.get("role")
    
    if name and email and role:
        participant = Participant(name=name, email=email, role=role, vatm_id=assignment.id)
        db.session.add(participant)
        
        log_activity(
            activity_type="Participant Added",
            description=f"Added participant {name} as {role}",
            user=current_user(),
            vatm_id=assignment.id
        )
            
        db.session.commit()
        flash("Participant added successfully.", "success")
    else:
        flash("All fields are required to add a participant.", "error")
        
    return redirect(url_for("vatms.assignment_detail", assignment_id=assignment.id))

@bp.route("/<int:assignment_id>/comment", methods=["POST"])
@login_required
def post_comment(assignment_id):
    assignment = VendorAssignmentToMatter.query.get(assignment_id) or abort(404)
    comment_text = request.form.get("comment_text")
    
    if comment_text:
        comment = Comment(comment_text=comment_text, author_id=current_user().id, vatm_id=assignment.id)
        db.session.add(comment)
        
        log_activity(
            activity_type="Comment", 
            description=comment_text, 
            user=current_user(), 
            vatm_id=assignment.id
        )
            
        db.session.commit()
        flash("Comment posted.", "success")
        
    return redirect(url_for("vatms.assignment_detail", assignment_id=assignment.id))