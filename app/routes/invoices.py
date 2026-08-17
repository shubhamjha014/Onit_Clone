from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import Invoice, Matter
from app.models.invoice import INVOICE_STATUSES
from app.models.matter import CURRENCIES
from app.services.auth_service import current_user, login_required
from app.services.matter_service import log_activity, recalculate_invoice_total

bp = Blueprint("invoices", __name__, url_prefix="/invoices")

PAGE_SIZE = 10


def _parse_date(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@bp.route("/")
@login_required
def list_invoices():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    page = request.args.get("page", 1, type=int)

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

    pagination = query.order_by(Invoice.created_at.desc()).paginate(
        page=page, per_page=PAGE_SIZE, error_out=False
    )

    return render_template(
        "invoices/list.html",
        pagination=pagination,
        invoices=pagination.items,
        search=search,
        status=status,
        statuses=INVOICE_STATUSES,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_invoice():
    matters = Matter.query.order_by(Matter.matter_number.desc()).all()

    if request.method == "POST":
        form = request.form
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
            return render_template(
                "invoices/form.html",
                form=form,
                matters=matters,
                statuses=INVOICE_STATUSES,
                currencies=CURRENCIES,
            ), 400

        invoice = Invoice(
            invoice_number=form["invoice_number"].strip(),
            matter_id=int(form["matter_id"]) if form.get("matter_id") else None,
            vendor_name=form["vendor_name"].strip(),
            invoice_date=_parse_date(form.get("invoice_date", "")),
            amount=form.get("amount") or 0,
            currency=form.get("currency") or "United States Dollar",
            description=form.get("description", "").strip() or None,
            status=form.get("status") or "Draft",
            submitted_date=datetime.utcnow().date(),
        )

        try:
            db.session.add(invoice)
            db.session.flush()
            if invoice.matter:
                recalculate_invoice_total(invoice.matter)
                log_activity(
                    "Invoice Submitted",
                    f"Invoice {invoice.invoice_number} submitted by {invoice.vendor_name}",
                    matter=invoice.matter,
                    user=current_user(),
                )
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("An invoice with that number already exists.", "error")
            return render_template(
                "invoices/form.html",
                form=form,
                matters=matters,
                statuses=INVOICE_STATUSES,
                currencies=CURRENCIES,
            ), 400
        except SQLAlchemyError:
            db.session.rollback()
            flash("The invoice could not be saved. Please try again.", "error")
            return render_template(
                "invoices/form.html",
                form=form,
                matters=matters,
                statuses=INVOICE_STATUSES,
                currencies=CURRENCIES,
            ), 500

        flash(f"Invoice {invoice.invoice_number} created.", "success")
        return redirect(url_for("invoices.invoice_detail", invoice_id=invoice.id))

    return render_template(
        "invoices/form.html",
        form={},
        matters=matters,
        statuses=INVOICE_STATUSES,
        currencies=CURRENCIES,
    )


@bp.route("/<int:invoice_id>")
@login_required
def invoice_detail(invoice_id):
    invoice = Invoice.query.get(invoice_id) or abort(404)
    return render_template(
        "invoices/detail.html", invoice=invoice, statuses=INVOICE_STATUSES
    )


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
