from datetime import datetime

from app.extensions import db


class Participant(db.Model):
    __tablename__ = "participants"

    id = db.Column(db.Integer, primary_key=True)
    matter_id = db.Column(
        db.Integer, db.ForeignKey("matters.id", ondelete="CASCADE"), nullable=True
    )
    task_id = db.Column(
        db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=True)
    vatm_id = db.Column(db.Integer, db.ForeignKey('vendor_assignments_to_matter.id'), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    matter = db.relationship("Matter", back_populates="participants")
    task = db.relationship("Task", back_populates="participants")
    vendor = db.relationship("Vendor", back_populates="participants")
    vatm = db.relationship("VendorAssignmentToMatter", back_populates="participants")

class Allocation(db.Model):
    __tablename__ = "allocations"

    id = db.Column(db.Integer, primary_key=True)
    matter_id = db.Column(
        db.Integer, db.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False
    )
    department = db.Column(db.String(120), nullable=False)
    percentage = db.Column(db.Numeric(5, 2), nullable=True)
    amount = db.Column(db.Numeric(14, 2), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    matter = db.relationship("Matter", back_populates="allocations")


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    matter_id = db.Column(
        db.Integer, db.ForeignKey("matters.id", ondelete="CASCADE"), nullable=True
    )
    task_id = db.Column(
        db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    vatm_id = db.Column(db.Integer, db.ForeignKey('vendor_assignments_to_matter.id'), nullable=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    comment_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    matter = db.relationship("Matter", back_populates="comments")
    task = db.relationship("Task", back_populates="comments")
    vendor = db.relationship("Vendor", back_populates="comments")
    vatm = db.relationship("VendorAssignmentToMatter", back_populates="comments")
    author = db.relationship("User")


class Activity(db.Model):
    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    matter_id = db.Column(
        db.Integer, db.ForeignKey("matters.id", ondelete="CASCADE"), nullable=True
    )
    task_id = db.Column(
        db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    vatm_id = db.Column(db.Integer, db.ForeignKey('vendor_assignments_to_matter.id'), nullable=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    activity_type = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(400), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    task = db.relationship("Task", back_populates="activities")
    matter = db.relationship("Matter", back_populates="activities")
    vendor = db.relationship("Vendor", back_populates="activities")
    vatm = db.relationship("VendorAssignmentToMatter", back_populates="activities")
    user = db.relationship("User")
