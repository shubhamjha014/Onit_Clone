from datetime import datetime
from app.extensions import db

class VendorAssignmentToMatter(db.Model):
    __tablename__ = "vendor_assignments_to_matter"

    id = db.Column(db.Integer, primary_key=True)
    vatm_name = db.Column(db.String(255))
    
    # Foreign Keys linking to Matter and Vendor apps
    matter_id = db.Column(db.Integer, db.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False) # Maps to "Panel Law Firm *"

    # Text / String Fields
    division_law_firm_panel = db.Column(db.String(255), nullable=True)
    
    # Dropdowns / Required Fields (*)
    funding_type = db.Column(db.String(100), nullable=False) # "Syndicate Funding Type" or "Alternate Funding Type"
    vendor_role = db.Column(db.String(100), nullable=False) 
    default_vendor_gl_account_number = db.Column(db.String(100), nullable=False)
    fee_arrangement_value = db.Column(db.String(100), nullable=False)
    
    # Financials
    syndicate_fixed_fee_amount = db.Column(db.Numeric(14, 2), nullable=True)

    # Toggles / Checkboxes
    custom_international_panel = db.Column(db.Boolean, nullable=False, default=False)
    panel_law_firms_only = db.Column(db.Boolean, nullable=False, default=True) # Checked by default based on UI text
    subcontractor = db.Column(db.Boolean, nullable=False, default=False)
    migrated = db.Column(db.Boolean, nullable=True, default=False)


    # Standard Application Tracking Fields
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships for back-populating
    matter = db.relationship("Matter", back_populates="vendor_assignments")
    vendor = db.relationship("Vendor", back_populates="vendor_assignments")
    participants = db.relationship("Participant", back_populates="vatm", cascade="all, delete-orphan")
    comments = db.relationship("Comment", back_populates="vatm", cascade="all, delete-orphan")
    activities = db.relationship("Activity", back_populates="vatm", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<VendorAssignmentToMatter Matter:{self.matter_id} Vendor:{self.vendor_id}>"