from datetime import datetime
from app.extensions import db

class Vendor(db.Model):
    __tablename__ = "vendors"

    id = db.Column(db.Integer, primary_key=True)
    
    # Core Vendor Details
    name = db.Column(db.String(200), nullable=False)  # Maps to "Vendor *"
    vendor_type = db.Column(db.String(100), nullable=False)  # Maps to "Vendor Type *"
    
    # Financials & Identifiers
    storm_third_party_id = db.Column(db.String(100), nullable=True)
    storm_engagement_id_1 = db.Column(db.String(100), nullable=True)
    storm_engagement_id_2 = db.Column(db.String(100), nullable=True)
    tax_status_type = db.Column(db.String(100), nullable=True)
    currency_code = db.Column(db.String(50), nullable=True, default="United States Dollar")
    
    # Toggles / Checkboxes
    manual_invoices_only = db.Column(db.Boolean, nullable=False, default=False)
    discounts_applicable = db.Column(db.Boolean, nullable=False, default=False)
    
    # Location
    country = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    
    # Relationship Partner
    relationship_partner_name = db.Column(db.String(150), nullable=True)
    relationship_partner_email = db.Column(db.String(255), nullable=True)
    relationship_partner_phone = db.Column(db.String(50), nullable=True)
    
    # Outside Counsel
    outside_counsel_email = db.Column(db.String(255), nullable=True)
    
    # Billing Contact 1 (Required fields based on UI asterisks)
    billing_contact_1_name = db.Column(db.String(150), nullable=False)
    billing_contact_1_email = db.Column(db.String(255), nullable=False)
    billing_contact_1_phone = db.Column(db.String(50), nullable=True)
    
    # Billing Contact 2
    billing_contact_2_name = db.Column(db.String(150), nullable=True)
    billing_contact_2_email = db.Column(db.String(255), nullable=True)
    billing_contact_2_phone = db.Column(db.String(50), nullable=True)
    
    # Billing Contact 3
    billing_contact_3_name = db.Column(db.String(150), nullable=True)
    billing_contact_3_email = db.Column(db.String(255), nullable=True)
    billing_contact_3_phone = db.Column(db.String(50), nullable=True)

    # Standard Application Tracking Fields
    status = db.Column(db.String(50), nullable=False, default="Active")
    migrated = db.Column(db.Boolean, nullable=True, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    participants = db.relationship(
        "Participant", back_populates="vendor", cascade="all, delete-orphan"
    )
    comments = db.relationship(
        "Comment", back_populates="vendor", cascade="all, delete-orphan"
    )
    activities = db.relationship(
        "Activity", back_populates="vendor", cascade="all, delete-orphan"
    )
    vendor_assignments = db.relationship(
        "VendorAssignmentToMatter", back_populates="vendor", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Vendor {self.name}>"