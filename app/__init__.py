"""
Flask application factory and initialization.
"""

import logging
import os
from flask import Flask, app, request
from flask_cors import CORS
from app.config import get_config
from app.extensions import db, jwt, migrate, mail
# Import your new master v1 blueprint containing products, listings, and interests
from app.routes import auth_bp, api_v1_bp, payment_bp 
from app.events import register_event_listeners


def create_app(config_name=None):
    """
    Create and configure Flask application.
    
    Args:
        config_name: Configuration name (development, testing, production)
                     If None, uses FLASK_ENV environment variable
    
    Returns:
        Configured Flask app instance
    """
    # Resolve uploads/ at project root (one level above app/ package)
    _upload_folder = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    )
    os.makedirs(_upload_folder, exist_ok=True)

    # Create Flask app — static_folder MUST be passed here, not set afterwards
    app = Flask(__name__,
                template_folder="templates",
                instance_relative_config=True,
                static_folder=_upload_folder,
                static_url_path='/uploads')
    
    # Get and apply configuration
    if config_name:
        config = __import__("app.config", fromlist=[config_name]).config.get(
            config_name, get_config()
        )
    else:
        config = get_config()
    
    app.config.from_object(config)
    # ==============================================
    
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            return "", 200
        
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # Enable CORS for auth routes (adjust origin to your React dev server)
    frontend = app.config.get('FRONTEND_URL', 'http://localhost:5173')
    CORS(app, resources={r"/*": {"origins": frontend}}, supports_credentials=True)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/v1')
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
    app.register_blueprint(payment_bp, url_prefix='/api/v1')
    
    # Register event listeners
    register_event_listeners()
    
    # Setup logging
    setup_logging(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Health check endpoint
    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}, 200
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request."""
        return {
            "error": "Bad Request",
            "status_code": 400
        }, 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized."""
        return {
            "error": "Unauthorized",
            "status_code": 401
        }, 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden."""
        return {
            "error": "Forbidden",
            "status_code": 403
        }, 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found."""
        return {
            "error": "Not Found",
            "status_code": 404
        }, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error."""
        return {
            "error": "Internal Server Error",
            "status_code": 500
        }, 500
    
    return app


def setup_logging(app):
    """
    Setup application logging.
    
    Args:
        app: Flask application instance
    """
    if not app.debug:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)