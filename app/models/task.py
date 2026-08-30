from datetime import datetime

from app.extensions import db

TASK_PRIORITIES = ["Low", "Medium", "High", "Critical"]


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    matter_id = db.Column(db.Integer, db.ForeignKey("matters.id"), nullable=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    priority = db.Column(db.String(20), nullable=False, default="Medium")
    status = db.Column(db.String(20), nullable=False, default="Open")
    migrated = db.Column(db.Boolean, nullable=True, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    matter = db.relationship("Matter", back_populates="tasks")
    assignee = db.relationship("User")
    participants = db.relationship(
        "Participant", back_populates="task", cascade="all, delete-orphan"
    )
    comments = db.relationship(
            "Comment", back_populates="task", cascade="all, delete-orphan"
        )
    activities = db.relationship(
            "Activity", back_populates="task", cascade="all, delete-orphan"
        )
