from datetime import datetime

from app.extensions import db

INVOICE_STATUSES = ["Draft", "Pending Approval", "Approved", "Rejected", "Paid"]


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(60), nullable=False, unique=True, index=True)
    matter_id = db.Column(db.Integer, db.ForeignKey("matters.id"), nullable=True)
    migrated = db.Column(db.Boolean, nullable=True, default=False)
    invoice_date = db.Column(db.Date, nullable=True)
    amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    currency = db.Column(db.String(60), nullable=False, default="United States Dollar")
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="Draft")
    submitted_date = db.Column(db.Date, nullable=True)
    vendor_name = db.Column(db.String(200), nullable=True)
    migrated = db.Column(db.Boolean, nullable=True, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    matter = db.relationship("Matter", back_populates="invoices")
