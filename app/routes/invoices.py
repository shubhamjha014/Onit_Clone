from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import Invoice, Matter, Vendor
from app.models.invoice import INVOICE_STATUSES
from app.models.matter import CURRENCIES
from app.services.auth_service import current_user, login_required
from app.services.matter_service import log_activity, recalculate_invoice_total

bp = Blueprint("invoices", __name__, url_prefix="/invoices")

# --- DYNAMIC GRID CONFIGURATION ---
GRID_COLUMNS = [
    {"key": "id", "label": "ID", "default": False, "type": "integer"},
    {"key": "invoice_number", "label": "Invoice Number", "default": True, "type": "link"},
    {"key": "matter", "label": "Matter Number", "default": True, "type": "matter_number"},
    {"key": "matter", "label": "Matter Name", "default": True, "type": "matter_name"},
    {"key": "vendor_name", "label": "Vendor", "default": True, "type": "text"},
    {"key": "invoice_date", "label": "Invoice Date", "default": True, "type": "date"},
    {"key": "amount", "label": "Amount", "default": True, "type": "currency"},
    {"key": "currency", "label": "Currency", "default": True, "type": "text"},
    {"key": "status", "label": "Status", "default": True, "type": "badge"},
    {"key": "migrated", "label": "Migrated Data", "default": True, "type": "boolean"},
    {"key": "submitted_date", "label": "Submitted", "default": True, "type": "date"},
    {"key": "description", "label": "Description", "default": False, "type": "text"}
]

def _parse_date(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None

def _get_invoice_choices():
    return {
        "matters": Matter.query.order_by(Matter.matter_number.desc()).all(),
        "vendors": Vendor.query.order_by(Vendor.name).all(),
        "statuses": INVOICE_STATUSES,
        "currencies": CURRENCIES,
    }

def _save_invoice(invoice: Invoice, form) -> bool:
    errors = []
    if not form.get("invoice_number", "").strip():
        errors.append("Invoice Number is required.")
    if not form.get("vendor_name", "").strip():
        errors.append("Vendor is required.")
    try:
        amount = float(form.get("amount") or 0)
        if amount < 0:
            errors.append("Amount must be zero or greater.")
    except ValueError:
        errors.append("Amount must be a number.")

    if errors:
        for error in errors:
            flash(error, "error")
        return False

    invoice.invoice_number = form["invoice_number"].strip()
    invoice.matter_id = int(form["matter_id"]) if form.get("matter_id") else None
    invoice.vendor_name = form.get("vendor_name").strip()
    invoice.invoice_date = _parse_date(form.get("invoice_date", ""))
    invoice.amount = float(form.get("amount") or 0)
    invoice.currency = form.get("currency") or "United States Dollar"
    invoice.description = form.get("description", "").strip() or None
    
    is_new = invoice.id is None
    if is_new:
        invoice.status = form.get("status") or "Draft"
        invoice.submitted_date = datetime.utcnow().date()

    try:
        db.session.add(invoice)
        db.session.flush()
        if invoice.matter:
            recalculate_invoice_total(invoice.matter)
            if is_new:
                log_activity(
                    "Invoice Submitted",
                    f"Invoice {invoice.invoice_number} submitted by {invoice.vendor_name}",
                    matter=invoice.matter,
                    user=current_user(),
                )
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        flash("An invoice with that number already exists.", "error")
        return False
    except SQLAlchemyError:
        db.session.rollback()
        flash("The invoice could not be saved. Please try again.", "error")
        return False

@bp.route("/")
@login_required
def list_invoices():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    if per_page not in [10, 50, 100, 200]: per_page = 10

    query = Invoice.query.outerjoin(Matter)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Invoice.invoice_number.ilike(like),
                Invoice.vendor_name.ilike(like),
                Matter.matter_name.ilike(like),
            )
        )
    if status:
        query = query.filter(Invoice.status == status)

    pagination = query.order_by(Invoice.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "invoices/list.html",
        pagination=pagination,
        invoices=pagination.items,
        search=search,
        status=status,
        grid_columns=GRID_COLUMNS,
        form={},
        **_get_invoice_choices()
    )

@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_invoice():
    if request.method == "POST":
        invoice = Invoice()
        if _save_invoice(invoice, request.form):
            flash(f"Invoice {invoice.invoice_number} created.", "success")
            return redirect(request.referrer or url_for("invoices.list_invoices"))
        return redirect(request.referrer or url_for("invoices.list_invoices"))

    return render_template("invoices/form.html", form={}, **_get_invoice_choices())

@bp.route("/<int:invoice_id>")
@login_required
def invoice_detail(invoice_id):
    invoice = Invoice.query.get(invoice_id) or abort(404)
    return render_template("invoices/detail.html", invoice=invoice, **_get_invoice_choices())

@bp.route("/<int:invoice_id>/update", methods=["POST"])
@login_required
def update_invoice(invoice_id):
    invoice = Invoice.query.get(invoice_id) or abort(404)
    if _save_invoice(invoice, request.form):
        flash("Invoice details updated successfully.", "success")
    return redirect(url_for("invoices.invoice_detail", invoice_id=invoice.id))

@bp.route("/<int:invoice_id>/status", methods=["POST"])
@login_required
def change_status(invoice_id):
    invoice = Invoice.query.get(invoice_id) or abort(404)
    status = request.form.get("status", "")

    if status not in INVOICE_STATUSES:
        flash("Unknown invoice status.", "error")
        return redirect(url_for("invoices.invoice_detail", invoice_id=invoice.id))

    invoice.status = status
    if invoice.matter:
        recalculate_invoice_total(invoice.matter)
        log_activity(
            "Invoice Status Changed",
            f"Invoice {invoice.invoice_number} marked {status}",
            matter=invoice.matter,
            user=current_user(),
        )
    db.session.commit()
    flash(f"Invoice status updated to {status}.", "success")
    return redirect(url_for("invoices.invoice_detail", invoice_id=invoice.id))

@bp.route("/bulk-delete", methods=["POST"])
@login_required
def bulk_delete():
    try:
        data = request.get_json()
        raw_ids = data.get("ids", [])
        if not raw_ids:
            return {"success": False, "error": "No invoices selected."}, 400
            
        invoice_ids = [int(iid) for iid in raw_ids]
        invoices = Invoice.query.filter(Invoice.id.in_(invoice_ids)).all()
        
        matters_to_update = set()
        for inv in invoices:
            if inv.matter:
                matters_to_update.add(inv.matter)
            db.session.delete(inv)
            
        db.session.commit()
        
        for m in matters_to_update:
            recalculate_invoice_total(m)
        db.session.commit()
        
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}, 500