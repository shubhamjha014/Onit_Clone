import random
import string
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

# Adjust this import based on your exact app factory structure (e.g., from app import create_app)
from app import create_app
from app.extensions import db

# Import your models
from app.models.user import User
from app.models.vendor import Vendor
from app.models.matter import Matter
from app.models.task import Task
from app.models.vatm import VendorAssignmentToMatter
from app.models.invoice import Invoice
from app.models.activity import Activity, Participant


def generate_unique_id(prefix, length=6):
    """Generates a random string to prevent unique constraint crashes."""
    chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return f"{prefix}-{chars}"


def run_seeder():
    app = create_app()
    with app.app_context():
        print("Starting Data Integration...")

        try:
            # ==========================================
            # PHASE 1: The Independents (Users & Vendors)
            # ==========================================
            print("1. Creating Matter Managers and Vendors...")
            
            managers = []
            for i in range(1, 4):
                user = User(
                    name=f"AI Test Manager {i}",
                    email=f"ai_manager_{i}_{random.randint(1000,9999)}@example.com",
                    migrated=True
                )
                user.set_password("Password123!")
                db.session.add(user)
                managers.append(user)
            
            db.session.flush()

            # Create an Independent Vendor
            vendor = Vendor(
                name=f"Global AI Legal Partners {random.randint(100, 999)}",
                vendor_type="Law Firm",
                billing_contact_1_name="Jane Doe",
                billing_contact_1_email="jane.billing@globalailegal.com",
                currency_code="United States Dollar",
                status="Active",
                migrated=True
            )
            db.session.add(vendor)
            db.session.flush()

            # ==========================================
            # PHASE 2: The Core Object (Matters)
            # ==========================================
            print("2. Generating 5 Matters with Tasks, Participants, VATMs, and Invoices...")
            
            for i in range(1, 6):
                assigned_manager = random.choice(managers)
                
                matter = Matter(
                    matter_number=generate_unique_id("MAT"),
                    matter_name=f"AI Integrated Dispute Resolution {i}",
                    matter_manager_id=assigned_manager.id,
                    opened_on=datetime.now(timezone.utc).date(),  # FIXED DATETIME
                    brief_description="Dummy matter created for AI chat bot context analysis.",
                    market="Corporate",
                    area_of_law="Litigation",
                    matter_type="Business disputes",
                    legal_entity="101 - Northwind Holdings",
                    currency="United States Dollar",
                    status="In Progress",
                    migrated=True
                )
                db.session.add(matter)
                db.session.flush()

                # ==========================================
                # PHASE 3: Level 1 Dependencies (Tasks & Participants)
                # ==========================================
                db.session.add(Participant(
                    matter_id=matter.id,
                    name=assigned_manager.name,
                    email=assigned_manager.email,
                    role="Matter Manager"
                ))
                db.session.add(Participant(
                    matter_id=matter.id,
                    name="AI Bot Requester",
                    email="requester@example.com",
                    role="Requester"
                ))
                
                for t in range(1, 4):
                    task = Task(
                        title=f"Initial Review & Briefing Phase {t}",
                        matter_id=matter.id,
                        assignee_id=assigned_manager.id,
                        description="Analyze the attached documentation for the chatbot validation.",
                        priority=random.choice(["Medium", "High", "Critical"]),
                        status=random.choice(["Open", "In Progress"]),
                        migrated=True
                    )
                    db.session.add(task)

                # ==========================================
                # PHASE 4: Level 2 Dependency (Vendor Assignment)
                # ==========================================
                vatm = VendorAssignmentToMatter(
                    vatm_name=f"Legal Counsel Assignment - {vendor.name}",
                    matter_id=matter.id,
                    vendor_id=vendor.id,
                    funding_type="Syndicate Funding Type",
                    vendor_role="Primary Counsel",
                    default_vendor_gl_account_number="GL-77492-01",
                    fee_arrangement_value="Hourly Rate",
                    syndicate_fixed_fee_amount=15000.00,
                    migrated=True
                )
                db.session.add(vatm)
                db.session.flush()

                # ==========================================
                # PHASE 5: Level 3 Dependency (Invoices)
                # ==========================================
                invoice = Invoice(
                    invoice_number=generate_unique_id("INV", 8),
                    matter_id=matter.id,
                    vendor_name=vendor.name, 
                    amount=random.uniform(5000.00, 25000.00),
                    currency="United States Dollar",
                    description="Professional services rendered for document discovery.",
                    status="Pending Approval",
                    migrated=True
                )
                db.session.add(invoice)

                # ==========================================
                # FIXED: Added activity_type to Activity Model
                # ==========================================
                db.session.add(Activity(
                    matter_id=matter.id,
                    activity_type="Data Integration", 
                    description="Matter populated via AI Data Integration script."
                ))

            # ==========================================
            # PHASE 6: Commit Transaction
            # ==========================================
            db.session.commit()
            print("✅ Success! Dummy data has been integrated seamlessly.")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during seeding. Transaction rolled back.\nDetails: {str(e)}")

if __name__ == "__main__":
    run_seeder()