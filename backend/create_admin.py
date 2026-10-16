
from getpass import getpass

from app import app
from models import db, User
from werkzeug.security import generate_password_hash


name = input("Enter admin name: ").strip()
email = input("Enter admin email: ").strip().lower()
password = getpass("Enter admin password (minimum 8 characters): ")

if not name or not email or len(password) < 8:
    print("Enter a name, a valid email, and a password of at least 8 characters.")
else:
    with app.app_context():
        admin = User.query.filter_by(email=email).first()

        if admin:
            admin.name = name
            admin.password_hash = generate_password_hash(password)
            admin.role = "admin"
            print("Existing account updated to admin.")
        else:
            admin = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role="admin",
            )
            db.session.add(admin)
            print("New admin account created.")

        db.session.commit()
        print("Admin setup successful!")