# seed_admins.py
# Run this on Railway console: python3 seed_admins.py
import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User, UserRole, UserStatus
from app.services.auth_service import AuthService

def seed_admins():
    app = create_app()
    with app.app_context():
        admins = [
            {
                "name": "GreenTag Admin",
                "email": "admin@greentag.com",
                "password": "admin123",
                "phone": "+256700000000",
            },
            {
                "name": "Admin One",
                "email": "admin1@greentag.com",
                "password": "Admin123!",
                "phone": "+256700000001",
            },
            {
                "name": "Admin Two",
                "email": "admin2@greentag.com",
                "password": "Admin123!",
                "phone": "+256700000002",
            },
        ]

        for admin_data in admins:
            existing = User.query.filter_by(email=admin_data["email"]).first()
            if not existing:
                hashed_pw = AuthService.hash_password(admin_data["password"])
                admin = User(
                    name=admin_data["name"],
                    email=admin_data["email"],
                    password=hashed_pw,
                    role=UserRole.ADMIN.value,
                    status=UserStatus.ACTIVE.value,
                    phone=admin_data["phone"],
                )
                db.session.add(admin)
                print(f"✅ Created admin: {admin_data['email']} / {admin_data['password']}")
            else:
                print(f"ℹ️  Already exists: {admin_data['email']}")

        db.session.commit()
        print("\nDone. Admin accounts ready.")
        print("\nLogin at: https://greentag.vercel.app/login")
        print("Primary admin: admin@greentag.com / admin123")

if __name__ == "__main__":
    seed_admins()