from datetime import datetime

from sqlalchemy import func

from app.extensions import db
from app.models import Activity, Matter, Task, VendorAssignmentToMatter


def generate_matter_number() -> str:
    """Matter numbers look like 2026-00042 and are unique per year."""
    year = datetime.utcnow().year
    prefix = f"{year}-"
    last = (
        Matter.query.filter(Matter.matter_number.like(f"{prefix}%"))
        .order_by(Matter.matter_number.desc())
        .first()
    )
    sequence = int(last.matter_number.split("-")[1]) + 1 if last else 1
    return f"{prefix}{sequence:05d}"


def log_activity(activity_type, description, matter=None, user=None, task=None, vendor = None,vatm_id=None):
    activity = Activity(
        matter_id=matter.id if matter else None,
        task_id=task.id if task else None,
        vendor_id=vendor.id if vendor else None,
        user_id=user.id if user else None,
        activity_type=activity_type,
        description=description,
        vatm_id=vatm_id
    )
    db.session.add(activity)
    return activity


def recalculate_invoice_total(matter: Matter) -> None:
    from app.models import Invoice

    total = (
        db.session.query(func.coalesce(func.sum(Invoice.amount), 0))
        .filter(Invoice.matter_id == matter.id, Invoice.status != "Rejected")
        .scalar()
    )
    matter.invoice_total = total
