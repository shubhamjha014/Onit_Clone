from datetime import datetime

from app.extensions import db

PARTICIPANT_ROLES = [
    "Requester",
    "Matter Manager",
    "Attorney",
    "Paralegal",
    "Business Owner",
    "External Counsel",
]


class Participant(db.Model):
    __tablename__ = "participants"

    id = db.Column(db.Integer, primary_key=True)
    matter_id = db.Column(
        db.Integer, db.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    matter = db.relationship("Matter", back_populates="participants")


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
        db.Integer, db.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False
    )
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    comment_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    matter = db.relationship("Matter", back_populates="comments")
    author = db.relationship("User")


class Activity(db.Model):
    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    matter_id = db.Column(
        db.Integer, db.ForeignKey("matters.id", ondelete="CASCADE"), nullable=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    activity_type = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(400), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    matter = db.relationship("Matter", back_populates="activities")
    user = db.relationship("User")
