# seed_admins.py
import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User, UserRole, UserStatus
from app.services.auth_service import AuthService

def seed_admins():
    app = create_app()
    with app.app_context():
        admins = [
            {"name": "Admin One", "email": "admin1@wastenot.com", "password": "Admin123!", "phone": "1234567890"},
            {"name": "Admin Two", "email": "admin2@wastenot.com", "password": "Admin123!", "phone": "0987654321"},
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
                print(f"Created admin: {admin_data['email']}")
            else:
                print(f"Admin already exists: {admin_data['email']}")
        db.session.commit()
        print("Admin seeding completed.")

if __name__ == "__main__":
    seed_admins()