"""
Pytest test suite for authentication endpoints and services.
"""

import pytest
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import User, UserRole, UserStatus, RefreshToken


@pytest.fixture
def app():
    """Create and configure a test Flask app."""
    app = create_app("testing")
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def admin_user(app):
    """Create an admin user."""
    from app.services import AuthService
    
    with app.app_context():
        user = User(
            name="Admin User",
            email="admin@test.com",
            password=AuthService.hash_password("password123"),
            role=UserRole.ADMIN.value,
            status=UserStatus.ACTIVE.value,
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def active_user(app):
    """Create an active regular user."""
    from app.services import AuthService
    
    with app.app_context():
        user = User(
            name="Regular User",
            email="user@test.com",
            password=AuthService.hash_password("password123"),
            role=UserRole.BUYER.value,
            status=UserStatus.ACTIVE.value,
        )
        db.session.add(user)
        db.session.commit()
        return user


class TestUserRegistration:
    """Tests for user registration endpoint."""
    
    def test_register_valid_user(self, client):
        """Test successful user registration."""
        response = client.post("/auth/register", json={
            "name": "John Doe",
            "email": "john@test.com",
            "password": "password123",
        })
        
        assert response.status_code == 201
        assert response.json["data"]["email"] == "john@test.com"
        assert response.json["data"]["role"] == UserRole.BUYER.value
    
    def test_register_duplicate_email(self, client, active_user):
        """Test registration with duplicate email."""
        response = client.post("/auth/register", json={
            "name": "Another User",
            "email": "user@test.com",
            "password": "password123",
        })
        
        assert response.status_code == 400
        assert "already registered" in response.json["error"]
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post("/auth/register", json={
            "name": "John Doe",
            "email": "invalid-email",
            "password": "password123",
        })
        
        assert response.status_code == 400
    
    def test_register_weak_password(self, client):
        """Test registration with weak password (no digits)."""
        response = client.post("/auth/register", json={
            "name": "John Doe",
            "email": "john@test.com",
            "password": "password",
        })
        
        assert response.status_code == 400
        assert "digit" in response.json["error"].lower()


class TestUserLogin:
    """Tests for user login endpoint."""
    
    def test_login_valid_credentials(self, client, active_user):
        """Test successful login."""
        response = client.post("/auth/login", json={
            "email": "user@test.com",
            "password": "password123",
        })
        
        assert response.status_code == 200
        assert "accessToken" in response.json["data"]
        assert "refreshToken" in response.json["data"]
        assert response.json["data"]["role"] == UserRole.BUYER.value
    
    def test_login_invalid_email(self, client):
        """Test login with non-existent email."""
        response = client.post("/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "password123",
        })
        
        assert response.status_code == 401
    
    def test_login_invalid_password(self, client, active_user):
        """Test login with wrong password."""
        response = client.post("/auth/login", json={
            "email": "user@test.com",
            "password": "wrongpassword",
        })
        
        assert response.status_code == 401
    
    def test_login_suspended_user(self, client, app):
        """Test login with suspended user."""
        from app.services import AuthService
        
        with app.app_context():
            user = User(
                name="Suspended User",
                email="suspended@test.com",
                password=AuthService.hash_password("password123"),
                role=UserRole.BUYER.value,
                status=UserStatus.SUSPENDED.value,
            )
            db.session.add(user)
            db.session.commit()
        
        response = client.post("/auth/login", json={
            "email": "suspended@test.com",
            "password": "password123",
        })
        
        assert response.status_code == 401
        assert "suspended" in response.json["error"].lower()
    
    def test_login_pending_approval_user(self, client, app):
        """Test login with pending approval user."""
        from app.services import AuthService
        
        with app.app_context():
            user = User(
                name="Pending User",
                email="pending@test.com",
                password=AuthService.hash_password("password123"),
                role=UserRole.SELLER.value,
                status=UserStatus.PENDING_APPROVAL.value,
            )
            db.session.add(user)
            db.session.commit()
        
        response = client.post("/auth/login", json={
            "email": "pending@test.com",
            "password": "password123",
        })
        
        assert response.status_code == 401
        assert "pending" in response.json["error"].lower()


class TestProfileEndpoint:
    """Tests for profile endpoint."""
    
    def test_get_profile_with_valid_token(self, client, active_user, app):
        """Test getting profile with valid JWT token."""
        from flask_jwt_extended import create_access_token
        
        with app.app_context():
            access_token = create_access_token(identity=active_user.id)
        
        response = client.get(
            "/auth/profile",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        assert response.json["data"]["email"] == "user@test.com"
    
    def test_get_profile_without_token(self, client):
        """Test getting profile without JWT token."""
        response = client.get("/auth/profile")
        
        assert response.status_code == 401


class TestChangePassword:
    """Tests for change password endpoint."""
    
    def test_change_password_valid(self, client, active_user, app):
        """Test successful password change."""
        from flask_jwt_extended import create_access_token
        
        with app.app_context():
            access_token = create_access_token(identity=active_user.id)
        
        response = client.put(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "old_password": "password123",
                "new_password": "newpassword123",
            }
        )
        
        assert response.status_code == 200
    
    def test_change_password_wrong_old_password(self, client, active_user, app):
        """Test password change with wrong old password."""
        from flask_jwt_extended import create_access_token
        
        with app.app_context():
            access_token = create_access_token(identity=active_user.id)
        
        response = client.put(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "old_password": "wrongpassword",
                "new_password": "newpassword123",
            }
        )
        
        assert response.status_code == 400


class TestAdminEndpoints:
    """Tests for admin-only endpoints."""
    
    def test_get_all_users_as_admin(self, client, admin_user, app):
        """Test getting all users as admin."""
        from flask_jwt_extended import create_access_token
        
        with app.app_context():
            access_token = create_access_token(identity=admin_user.id)
        
        response = client.get(
            "/auth/all-users",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        assert isinstance(response.json["data"], list)
    
    def test_get_all_users_as_regular_user(self, client, active_user, app):
        """Test getting all users as regular user (should fail)."""
        from flask_jwt_extended import create_access_token
        
        with app.app_context():
            access_token = create_access_token(identity=active_user.id)
        
        response = client.get(
            "/auth/all-users",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 403
    
    def test_update_user_status_as_admin(self, client, admin_user, active_user, app):
        """Test updating user status as admin."""
        from flask_jwt_extended import create_access_token
        
        with app.app_context():
            access_token = create_access_token(identity=admin_user.id)
        
        response = client.put(
            "/auth/update-status",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "email": "user@test.com",
                "status": UserStatus.SUSPENDED.value,
            }
        )
        
        assert response.status_code == 200
        assert response.json["data"]["status"] == UserStatus.SUSPENDED.value


class TestForgotPassword:
    """Tests for forgot password endpoint."""
    
    def test_forgot_password_existing_email(self, client, active_user):
        """Test forgot password with existing email."""
        response = client.post("/auth/forgot-password", json={
            "email": "user@test.com"
        })
        
        assert response.status_code == 200
        # Message should be same regardless of whether email exists
        assert "email" in response.json["message"].lower()
    
    def test_forgot_password_nonexistent_email(self, client):
        """Test forgot password with non-existent email."""
        response = client.post("/auth/forgot-password", json={
            "email": "nonexistent@test.com"
        })
        
        assert response.status_code == 200
        # Should return same message for security


class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json["status"] == "healthy"
