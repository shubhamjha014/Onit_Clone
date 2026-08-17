"""Populate the database with demo data for every application module."""

from datetime import date, datetime, timedelta
from random import choice, randint

from app import create_app
from app.extensions import db
from app.models import (
    Activity,
    Allocation,
    Comment,
    Contact,
    Invoice,
    Matter,
    Participant,
    Task,
    User,
)
from app.models.contact import CONTACT_TYPES
from app.models.invoice import INVOICE_STATUSES
from app.models.matter import (
    AREAS_OF_LAW,
    CURRENCIES,
    LEGAL_ENTITIES,
    MARKETS,
    MATTER_STATUSES,
    MATTER_TYPES,
    PAYMENT_METHODS,
    REGIONS,
)
from app.models.task import TASK_PRIORITIES, TASK_STATUSES

DEMO_USERS = [
    ("Demo User", "demo@example.com"),
    ("Sarah Cole", "sarah.cole@example.com"),
    ("Martin Allison", "martin.allison@example.com"),
    ("Priya Nair", "priya.nair@example.com"),
]

VENDORS = ["Harper & Vance LLP", "Bracken Legal", "Ridgeway Counsel", "Kestrel Advisory"]


def reset_database():
    db.drop_all()
    db.create_all()


def seed():
    users = []
    for name, email in DEMO_USERS:
        user = User(name=name, email=email)
        user.set_password("demo1234")
        db.session.add(user)
        users.append(user)
    db.session.flush()

    demo_user = users[0]

    matters = []
    for index in range(1, 13):
        matter = Matter(
            matter_number=f"{datetime.utcnow().year}-{index:05d}",
            matter_name=f"{choice(['Vendor', 'Franchise', 'Trademark', 'Lease', 'Employment'])} Matter {index}",
            matter_manager_id=(demo_user if index % 2 else choice(users)).id,
            opened_on=date.today() - timedelta(days=randint(1, 240)),
            brief_description="Demo matter created by the seed script.",
            market=choice(MARKETS),
            area_of_law=choice(AREAS_OF_LAW),
            region=choice(REGIONS),
            matter_type=choice(MATTER_TYPES),
            legal_entity=choice(LEGAL_ENTITIES),
            currency=choice(CURRENCIES),
            payment_method=choice(PAYMENT_METHODS),
            total_budget=randint(10, 200) * 1000,
            status=choice(MATTER_STATUSES),
        )
        db.session.add(matter)
        matters.append(matter)
    db.session.flush()

    for matter in matters:
        db.session.add_all(
            [
                Participant(
                    matter_id=matter.id,
                    name=demo_user.name,
                    email=demo_user.email,
                    role="Requester",
                ),
                Participant(
                    matter_id=matter.id,
                    name="Sarah Cole",
                    email="sarah.cole@example.com",
                    role="Matter Manager",
                ),
                Allocation(
                    matter_id=matter.id,
                    department="Legal Operations",
                    percentage=100,
                    amount=matter.total_budget,
                    notes="Full allocation to legal operations.",
                ),
                Comment(
                    matter_id=matter.id,
                    author_id=demo_user.id,
                    comment_text="Kick-off completed with the business stakeholders.",
                ),
                Activity(
                    matter_id=matter.id,
                    user_id=demo_user.id,
                    activity_type="Matter Created",
                    description=f"Matter {matter.matter_number} created",
                ),
            ]
        )

    for index, matter in enumerate(matters[:8], start=1):
        invoice = Invoice(
            invoice_number=f"INV-{1000 + index}",
            matter_id=matter.id,
            vendor_name=choice(VENDORS),
            invoice_date=date.today() - timedelta(days=randint(1, 60)),
            amount=randint(1, 40) * 500,
            currency=matter.currency,
            description="Professional services rendered.",
            status=choice(INVOICE_STATUSES),
            submitted_date=date.today() - timedelta(days=randint(1, 30)),
        )
        db.session.add(invoice)
        if invoice.status != "Rejected":
            matter.invoice_total = (matter.invoice_total or 0) + invoice.amount

    for index in range(1, 11):
        db.session.add(
            Contact(
                name=f"Contact Person {index}",
                email=f"contact{index}@example.com",
                phone=f"+1 555 010{index:02d}",
                organization=choice(VENDORS),
                role=choice(["Partner", "Associate", "Billing Manager", "Analyst"]),
                contact_type=choice(CONTACT_TYPES),
            )
        )

    for index in range(1, 13):
        db.session.add(
            Task(
                title=f"Review deliverable {index}",
                matter_id=choice(matters).id,
                assignee_id=(demo_user if index % 2 else choice(users)).id,
                description="Demo task created by the seed script.",
                due_date=date.today() + timedelta(days=randint(-5, 30)),
                priority=choice(TASK_PRIORITIES),
                status=choice(TASK_STATUSES),
            )
        )

    db.session.commit()


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        reset_database()
        seed()
        print("Seed data created. Sign in with demo@example.com / demo1234")
