import pandas as pd
import random
from faker import Faker
from datetime import timedelta

# pip install faker pandas openpyxl
# Initialize Faker
fake = Faker()

# Model Definitions (From your backend config)
MARKETS = ["Corporate", "Americas", "Europe", "Asia Pacific", "Australia"]
MATTER_TYPES = ["Board of Directors", "Business disputes", "Franchise disputes", "Government investigations / regulatory", "Insurance", "IP / Marketing", "Other"]
LEGAL_ENTITIES = ["101 - Northwind Holdings", "204 - Northwind Operations", "310 - Northwind International"]
CURRENCIES = ["United States Dollar", "British Pound", "Euro", "Australian Dollar"]
REGIONS = ["North", "South", "East", "West", "Global"]
PAYMENT_METHODS = ["Bank Transfer", "Corporate Card", "Check"]
AREAS_OF_LAW = ["Corporate Legal", "Employment", "Litigation", "Real Estate","Intellectual Property","Compliance"]
LINES_OF_BUSINESS = ["CB - Global Receivables & Trade Finance", "IB - Investment Banking", "WM - Wealth Management", "AM - Asset Management", "CB - Commercial Real Estate", "RB - Retail Banking", "CIB - Corporate & Institutional Banking", "Treasury & Markets"]
MATTER_STATUSES = ["Pending Allocation", "Open", "On Hold", "Closed"]
TASK_PRIORITIES = ["Low", "Medium", "High", "Critical"]
TASK_STATUSES = ["Not Started", "In Progress", "Completed"]
INVOICE_STATUSES = ["Draft", "Pending Approval", "Approved", "Rejected", "Paid"]
VENDOR_TYPES = ["Law Firm", "Courier Service", "Court Reporter Service", "Deposition Witness/Service", "Document Research Service", "Expert Consultant", "Expert Witness", "External Other"]

def generate_realistic_data():
    print("Generating 20 Users...")
    users = []
    for i in range(1, 21):
        users.append({
            "id": i,
            "name": fake.name(),
            "email": fake.company_email(),
            "role": "Matter Manager"
        })

    print("Generating 50 Vendors...")
    vendors = []
    for i in range(1, 51):
        company_name = fake.company()
        vendor_suffix = random.choice([" LLP", " Legal Partners", " Law Group", " Associates", " Consulting"])
        vendors.append({
            "id": i,
            "name": company_name + vendor_suffix,
            "vendor_type": random.choice(VENDOR_TYPES),
            "billing_contact_name": fake.name(),
            "billing_contact_email": fake.company_email(),
            "currency_code": random.choice(CURRENCIES),
            "status": "Active"
        })

    print("Generating 1000 Matters...")
    matters = []
    for i in range(1, 1001):
        opened_date = fake.date_between(start_date='-3y', end_date='today')
        budget = round(random.uniform(10000.0, 500000.0), 2)
        
        # Generate realistic legal matter names
        matter_name_templates = [
            f"{fake.company()} - Merger & Acquisition",
            f"Employment Dispute: {fake.last_name()} v. {fake.company()}",
            f"{fake.company()} Regulatory Filing {opened_date.year}",
            f"IP Trademark Registration - {fake.catch_phrase().title()}",
            f"Real Estate Lease Agreement - {fake.city()} Office"
        ]
        
        matters.append({
            "id": i,
            "matter_number": f"MAT-{fake.bothify(text='????-####').upper()}",
            "matter_name": random.choice(matter_name_templates),
            "matter_manager_id": random.choice(users)["id"],
            "opened_on": opened_date,
            "brief_description": fake.paragraph(nb_sentences=2),
            "market": random.choice(MARKETS),
            "area_of_law": random.choice(AREAS_OF_LAW),
            "region": random.choice(REGIONS),
            "matter_type": random.choice(MATTER_TYPES),
            "legal_entity": random.choice(LEGAL_ENTITIES),
            "primary_line_of_business": random.choice(LINES_OF_BUSINESS),
            "currency": random.choice(CURRENCIES),
            "payment_method": random.choice(PAYMENT_METHODS),
            "total_budget": budget,
            "status": random.choice(MATTER_STATUSES)
        })

    print("Generating ~3000 Tasks...")
    tasks = []
    task_id = 1
    task_titles = ["Draft Initial Subpoena", "Review Q3 Compliance Docs", "Client Discovery Meeting", "File Trademark Application", "Review Vendor NDA", "Prepare Deposition Questions", "Finalize Settlement Agreement"]
    for matter in matters:
        # 2 to 4 tasks per matter
        num_tasks = random.randint(2, 4)
        for _ in range(num_tasks):
            due_date = matter["opened_on"] + timedelta(days=random.randint(5, 90))
            tasks.append({
                "id": task_id,
                "matter_id": matter["id"],
                "assignee_id": matter["matter_manager_id"],
                "title": random.choice(task_titles),
                "description": fake.sentence(),
                "due_date": due_date,
                "priority": random.choice(TASK_PRIORITIES),
                "status": random.choice(TASK_STATUSES)
            })
            task_id += 1

    print("Generating ~1500 Invoices...")
    invoices = []
    invoice_id = 1
    for matter in matters:
        # 1 to 2 invoices per matter
        num_invoices = random.randint(1, 2)
        for _ in range(num_invoices):
            inv_date = matter["opened_on"] + timedelta(days=random.randint(15, 120))
            vendor = random.choice(vendors)
            invoices.append({
                "id": invoice_id,
                "invoice_number": f"INV-{fake.bothify(text='######').upper()}",
                "matter_id": matter["id"],
                "vendor_id": vendor["id"],
                "vendor_name": vendor["name"],
                "invoice_date": inv_date,
                "amount": round(random.uniform(500.0, float(matter["total_budget"]) / 2), 2),
                "currency": matter["currency"],
                "description": f"Professional services rendered for {matter['matter_name']}",
                "status": random.choice(INVOICE_STATUSES)
            })
            invoice_id += 1

    print("Exporting to Excel...")
    with pd.ExcelWriter("Legal_App_Data_Validation.xlsx") as writer:
        pd.DataFrame(users).to_excel(writer, sheet_name="Users", index=False)
        pd.DataFrame(vendors).to_excel(writer, sheet_name="Vendors", index=False)
        pd.DataFrame(matters).to_excel(writer, sheet_name="Matters", index=False)
        pd.DataFrame(tasks).to_excel(writer, sheet_name="Tasks", index=False)
        pd.DataFrame(invoices).to_excel(writer, sheet_name="Invoices", index=False)
    
    print("✅ Complete! Open 'Legal_App_Data_Validation.xlsx' to review your data.")

if __name__ == "__main__":
    generate_realistic_data()