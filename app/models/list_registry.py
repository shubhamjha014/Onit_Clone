from datetime import datetime
from app.extensions import db

class ListRegistry(db.Model):
    __tablename__ = "list_registry"

    id = db.Column(db.Integer, primary_key=True)
    
    # The human-readable name from the Excel sheet (e.g., "P4_codes")
    display_name = db.Column(db.String(120), nullable=False)
    
    # The sanitized, safe database table name (e.g., "list_p4_codes")
    table_name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    
    # Quick caching for the UI so we don't have to count rows on every page load
    row_count = db.Column(db.Integer, nullable=False, default=0)
    
    # Tracking who uploaded or last modified this list
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to the User model
    created_by = db.relationship("User", backref="uploaded_lists")

    def __repr__(self) -> str:
        return f"<ListRegistry {self.table_name}>"