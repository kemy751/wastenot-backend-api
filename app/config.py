import os
from datetime import timedelta

from dotenv import load_dotenv
from sqlalchemy.engine import URL


load_dotenv()


def get_database_uri():
    """Build the database URI.

    SQLite is the safe default for local development. Set USE_POSTGRES=true
    to opt into PostgreSQL with the POSTGRES_* environment variables.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    use_postgres = os.getenv("USE_POSTGRES", "false").lower() in {"1", "true", "yes"}
    if not use_postgres:
        return "sqlite:///wastenot.db"

    username = os.getenv("POSTGRES_USERNAME")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DATABASE", "wastenot")
    

    return URL.create(
        "postgresql+psycopg2",
        username=username,
        password=password,
        host=host,
        port=int(port),
        database=database,
    )





class Config:

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Database
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=10)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=3)
    JWT_ALGORITHM = "HS256"
    
    # Email Configuration
    MAIL_SERVER = os.getenv("EMAIL_HOST", "localhost")
    MAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("EMAIL_USER", "")
    MAIL_PASSWORD = os.getenv("EMAIL_PASS", "")
    MAIL_DEFAULT_SENDER = os.getenv("EMAIL_USER", "noreply@wastenot.com")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@wastenot.com")
    
    # Frontend
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Bcrypt
    BCRYPT_LOG_ROUNDS = 10
    
    # Reset Token Expiry (in seconds)
    RESET_TOKEN_EXPIRY = 3600  # 1 hour


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config():
    """Get configuration based on Flask environment."""
    env = os.getenv("FLASK_ENV", "development")
    return config.get(env, DevelopmentConfig)
