from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()
with app.app_context():
    email = 'test_user@example.com'
    existing = User.query.filter_by(email=email).first()
    if existing:
        print('User already exists:', existing.email)
    else:
        user = User(name='Test User', email=email, migrated=True)
        user.set_password('Password123!')
        db.session.add(user)
        db.session.commit()
        print('Created user', email)
