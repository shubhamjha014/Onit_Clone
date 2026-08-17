# Legal Management Portal

A Flask + PostgreSQL prototype of an enterprise legal-management platform. The left sidebar hosts four
applications — Matter Management, Invoices, Contacts and Tasks — plus a dashboard home page. Every screen
is backed by real database records; nothing is mocked.

## Stack

Flask, SQLAlchemy (Flask-SQLAlchemy), Flask-Migrate/Alembic, PostgreSQL, Jinja2, vanilla CSS/JS.

## Project structure

```text
app/
    __init__.py            application factory, blueprint registration, error handlers
    config.py              environment-driven configuration
    extensions.py          db + migrate instances
    models/                user, matter, activity (participant/allocation/comment/activity), invoice, contact, task
    routes/                auth, home, matters, invoices, contacts, tasks blueprints
    services/              auth_service (session + password hashing), matter_service (numbering, activity log)
    templates/
        base.html, home.html, auth/, matters/, invoices/, contacts/, tasks/, errors/
        components/        sidebar, topbar, flash_messages, status_badge, pagination
    static/css/app.css, static/js/app.js
migrations/                Alembic migrations
seed.py                    demo data
run.py                     entry point
```

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create the database:

```sql
CREATE USER legal WITH PASSWORD 'legal';
CREATE DATABASE legal_management OWNER legal;
```

Copy `.env.example` to `.env` and adjust the credentials:

```bash
cp .env.example .env
```

Apply migrations and load demo data:

```bash
export FLASK_APP=run.py        # Windows: set FLASK_APP=run.py
flask db upgrade
python seed.py
```

`seed.py` recreates the schema and inserts demo users, matters, participants, allocations, comments,
activities, invoices, contacts and tasks.

Run the application:

```bash
python run.py                  # http://127.0.0.1:5000
```

## Demo user

`demo@example.com` / `demo1234` (passwords are stored as Werkzeug hashes). The seed script creates a
handful of demo accounts that all share this password; change them before exposing the app anywhere.
Set `SECRET_KEY` in `.env` — without it a random key is generated per process and sessions are dropped
on restart. All state-changing forms are CSRF-protected via Flask-WTF.

## The four applications

- **Matter Management** — searchable, filterable, paginated matter grid; a create form that validates
  required fields, generates a unique matter number (`YYYY-00001`) and redirects to the new matter; a
  detail page with summary header, allocations, linked invoices, comments, and a right-hand action panel
  for status changes, participants, allocations and comments. Every action writes an activity record.
- **Invoices** — invoice grid with search/status filters, create form optionally linked to a matter, and a
  detail page with a status dropdown. Linked invoices roll up into the matter's invoice total and budget
  remaining, and appear on the matter detail page.
- **Contacts** — grid with search and contact-type filter, plus create, view and edit.
- **Tasks** — grid with search, status and priority filters, plus create and edit; tasks can be linked to a
  matter and an assignee.

The home dashboard counts (pending tasks, pending approvals, open matters, pending invoices), newest
matters and recent activity are all queried live from PostgreSQL.

## Assumptions

- Authentication is a simple session-based demo login rather than a full enterprise identity integration;
  `login_required` guards every application route so real auth can be swapped in later.
- Matter numbers are unique per calendar year and generated from the highest existing number.
- An invoice contributes to a matter's invoice total unless its status is `Rejected`.
- Reference data (markets, areas of law, matter types, legal entities, currencies) lives in module-level
  constants rather than lookup tables, to keep the prototype simple.


You can now log in with:

demo@example.com
demo1234