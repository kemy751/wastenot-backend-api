"""
Flask extensions initialization.
Centralizes instantiation of all Flask extensions used throughout the application.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_mail import Mail
from blinker import Namespace

# Database instance
db = SQLAlchemy()

# JWT extension
jwt = JWTManager()

# Database migrations
migrate = Migrate()

# Email service
mail = Mail()

# Signal namespace for blinker
events = Namespace()
