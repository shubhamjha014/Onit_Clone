from datetime import datetime

from app.extensions import db

TASK_STATUSES = ["Open", "In Progress", "Completed", "Cancelled"]
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
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    matter = db.relationship("Matter", back_populates="tasks")
    assignee = db.relationship("User")
