from datetime import datetime

from app.extensions import db

CONTACT_TYPES = ["Internal", "External Counsel", "Vendor", "Business Contact"]


class Contact(db.Model):
    __tablename__ = "contacts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(60), nullable=True)
    organization = db.Column(db.String(160), nullable=True)
    role = db.Column(db.String(120), nullable=True)
    contact_type = db.Column(db.String(60), nullable=False, default="Internal")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
