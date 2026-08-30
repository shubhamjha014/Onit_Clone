import pandas as pd
from datetime import datetime
from sqlalchemy.exc import IntegrityError

# Adjust this import based on your app factory
from app import create_app
from app.extensions import db

# Import your models
from app.models.user import User
from app.models.vendor import Vendor
from app.models.matter import Matter
from app.models.task import Task
from app.models.vatm import VendorAssignmentToMatter
from app.models.invoice import Invoice
from app.models.activity import Participant, Activity

def load_excel_data():
    app = create_app()
    with app.app_context():
        print("📥 Reading Excel File: Legal_App_Data_Validation.xlsx...")
        
        # Load the file
        xls = pd.ExcelFile("Legal_App_Data_Validation.xlsx")
        
        # 1. Read the sheets into DataFrames
        df_users = pd.read_excel(xls, "Users")
        df_vendors = pd.read_excel(xls, "Vendors")
        df_matters = pd.read_excel(xls, "Matters")
        df_tasks = pd.read_excel(xls, "Tasks")
        df_invoices = pd.read_excel(xls, "Invoices")

        # 2. Safely replace Pandas NaN values with Python None so SQLAlchemy can insert NULLs
        df_users = df_users.where(pd.notna(df_users), None)
        df_vendors = df_vendors.where(pd.notna(df_vendors), None)
        df_matters = df_matters.where(pd.notna(df_matters), None)
        df_tasks = df_tasks.where(pd.notna(df_tasks), None)
        df_invoices = df_invoices.where(pd.notna(df_invoices), None)

        # Dictionaries to map Excel IDs to actual Database IDs to preserve relationships
        user_map = {}
        vendor_map = {}
        matter_map = {}
        
        # Set to track VATMs created on the fly
        created_vatms = set()

        try:
            # ==========================================
            # 1. Ingest Users
            # ==========================================
            print(f"👥 Integrating {len(df_users)} Users...")
            for _, row in df_users.iterrows():
                user = User(
                    name=row["name"],
                    email=row["email"],
                    migrated=True
                )
                user.set_password("Password123!")
                db.session.add(user)
                db.session.flush() # Get DB ID immediately
                user_map[row["id"]] = user.id

            # ==========================================
            # 2. Ingest Vendors
            # ==========================================
            print(f"🏢 Integrating {len(df_vendors)} Vendors...")
            for _, row in df_vendors.iterrows():
                vendor = Vendor(
                    name=row["name"],
                    vendor_type=row["vendor_type"],
                    billing_contact_1_name=row["billing_contact_name"],
                    billing_contact_1_email=row["billing_contact_email"],
                    currency_code=row["currency_code"],
                    status=row["status"],
                    migrated=True
                )
                db.session.add(vendor)
                db.session.flush()
                vendor_map[row["id"]] = vendor.id

            # ==========================================
            # 3. Ingest Matters & Core Dependencies
            # ==========================================
            print(f"📁 Integrating {len(df_matters)} Matters with Participants & Logs...")
            for _, row in df_matters.iterrows():
                db_manager_id = user_map[row["matter_manager_id"]]
                
                matter = Matter(
                    matter_number=row["matter_number"],
                    matter_name=row["matter_name"],
                    matter_manager_id=db_manager_id,
                    opened_on=row["opened_on"].date() if pd.notna(row["opened_on"]) else None,
                    brief_description=row["brief_description"],
                    market=row["market"],
                    area_of_law=row["area_of_law"],
                    region=row["region"],
                    matter_type=row["matter_type"],
                    legal_entity=row["legal_entity"],
                    primary_line_of_business=row["primary_line_of_business"],
                    currency=row["currency"],
                    payment_method=row["payment_method"],
                    total_budget=row["total_budget"],
                    status=row["status"],
                    migrated=True
                )
                db.session.add(matter)
                db.session.flush()
                matter_map[row["id"]] = matter.id

                # Find the manager's name from our DataFrame for the Participant record
                manager_name = df_users.loc[df_users["id"] == row["matter_manager_id"], "name"].values[0]
                manager_email = df_users.loc[df_users["id"] == row["matter_manager_id"], "email"].values[0]

                # Automatically add Participants
                db.session.add(Participant(
                    matter_id=matter.id,
                    name=manager_name,
                    email=manager_email,
                    role="Matter Manager"
                ))

                # Automatically log activity
                db.session.add(Activity(
                    matter_id=matter.id,
                    activity_type="Data Integration",
                    description=f"Matter migrated from legacy dataset via Excel."
                ))

            # ==========================================
            # 4. Ingest Tasks
            # ==========================================
            print(f"✅ Integrating {len(df_tasks)} Tasks...")
            for _, row in df_tasks.iterrows():
                task = Task(
                    title=row["title"],
                    matter_id=matter_map[row["matter_id"]],
                    assignee_id=user_map[row["assignee_id"]],
                    description=row["description"],
                    due_date=row["due_date"].date() if pd.notna(row["due_date"]) else None,
                    priority=row["priority"],
                    status=row["status"],
                    migrated=True
                )
                db.session.add(task)

            # ==========================================
            # 5. Ingest Invoices & Auto-Generate VATMs
            # ==========================================
            print(f"💰 Integrating {len(df_invoices)} Invoices & Assigning Vendors...")
            for _, row in df_invoices.iterrows():
                db_matter_id = matter_map[row["matter_id"]]
                db_vendor_id = vendor_map[row["vendor_id"]]
                vatm_key = (db_matter_id, db_vendor_id)

                # Ensure a VATM exists for this vendor-matter relationship
                if vatm_key not in created_vatms:
                    vatm = VendorAssignmentToMatter(
                        vatm_name=f"Counsel Assignment - {row['vendor_name']}",
                        matter_id=db_matter_id,
                        vendor_id=db_vendor_id,
                        funding_type="Syndicate Funding Type",
                        vendor_role="Primary Counsel",
                        default_vendor_gl_account_number="GL-77492-01",
                        fee_arrangement_value="Hourly Rate",
                        migrated=True
                    )
                    db.session.add(vatm)
                    created_vatms.add(vatm_key)

                # Add the Invoice
                invoice = Invoice(
                    invoice_number=row["invoice_number"],
                    matter_id=db_matter_id,
                    vendor_name=row["vendor_name"],
                    invoice_date=row["invoice_date"].date() if pd.notna(row["invoice_date"]) else None,
                    amount=row["amount"],
                    currency=row["currency"],
                    description=row["description"],
                    status=row["status"],
                    migrated=True
                )
                db.session.add(invoice)

            # ==========================================
            # 6. Commit All Data
            # ==========================================
            print("💾 Committing all records to the database...")
            db.session.commit()
            print("🚀 Success! Data integration complete.")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during ingestion. Transaction rolled back.\nDetails: {str(e)}")

if __name__ == "__main__":
    load_excel_data()