from datetime import datetime

from app.extensions import db

MARKETS = ["Corporate", "Americas", "Europe", "Asia Pacific", "Australia"]
MATTER_TYPES = [
    "Board of Directors",
    "Business disputes",
    "Franchise disputes",
    "Government investigations / regulatory",
    "Insurance",
    "IP / Marketing",
    "Other",
]
LEGAL_ENTITIES = [
    "101 - Northwind Holdings",
    "204 - Northwind Operations",
    "310 - Northwind International",
]
CURRENCIES = ["United States Dollar", "British Pound", "Euro", "Australian Dollar"]
REGIONS = ["North", "South", "East", "West", "Global"]
PAYMENT_METHODS = ["Bank Transfer", "Corporate Card", "Check"]


class Matter(db.Model):
    __tablename__ = "matters"

    id = db.Column(db.Integer, primary_key=True)
    matter_number = db.Column(db.String(40), nullable=False, unique=True, index=True)
    matter_name = db.Column(db.String(200), nullable=False)
    matter_manager_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    opened_on = db.Column(db.Date, nullable=True)
    brief_description = db.Column(db.Text, nullable=True)
    market = db.Column(db.String(80), nullable=False)
    area_of_law = db.Column(db.String(80), nullable=False)
    region = db.Column(db.String(80), nullable=True)
    matter_type = db.Column(db.String(120), nullable=False)
    legal_entity = db.Column(db.String(120), nullable=False)
    currency = db.Column(db.String(60), nullable=False)
    payment_method = db.Column(db.String(60), nullable=True)
    invoice_total = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    total_budget = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    status = db.Column(db.String(40), nullable=False, default="Draft")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    manager = db.relationship("User", backref="managed_matters")
    participants = db.relationship(
        "Participant", back_populates="matter", cascade="all, delete-orphan"
    )
    allocations = db.relationship(
        "Allocation", back_populates="matter", cascade="all, delete-orphan"
    )
    comments = db.relationship(
        "Comment", back_populates="matter", cascade="all, delete-orphan"
    )
    activities = db.relationship(
        "Activity", back_populates="matter", cascade="all, delete-orphan"
    )
    invoices = db.relationship("Invoice", back_populates="matter", cascade="all, delete-orphan")
    tasks = db.relationship("Task", back_populates="matter", cascade="all, delete-orphan")

    @property
    def matter_email(self) -> str:
        return f"{self.matter_number}@legal-portal.example.com"

    @property
    def budget_remaining(self):
        return (self.total_budget or 0) - (self.invoice_total or 0)

    def __repr__(self) -> str:
        return f"<Matter {self.matter_number}>"
