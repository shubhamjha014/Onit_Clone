from app.extensions import db

class AppSetting(db.Model):
    __tablename__ = "app_settings"

    id = db.Column(db.Integer, primary_key=True)
    
    # E.g., 'Matters', 'Invoices', 'Tasks'
    app_name = db.Column(db.String(50), nullable=False, index=True) 
    
    # E.g., 'matter_statuses', 'matter_roles'
    key = db.Column(db.String(50), nullable=False, unique=True, index=True) 
    
    # Stores the Python list natively!
    value = db.Column(db.JSON, nullable=False, default=list) 

    def __repr__(self) -> str:
        return f"<AppSetting {self.app_name}: {self.key}>"