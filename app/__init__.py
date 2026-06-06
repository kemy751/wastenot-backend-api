import logging
import os
from flask import Flask, request, make_response
from flask_cors import CORS
from app.config import get_config
from app.extensions import db, jwt, migrate, mail
from app.routes import auth_bp, api_v1_bp, payment_bp
from app.events import register_event_listeners


def create_app(config_name=None):
    _upload_folder = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    )
    os.makedirs(_upload_folder, exist_ok=True)

    app = Flask(__name__,
                template_folder="templates",
                instance_relative_config=True,
                static_folder=_upload_folder,
                static_url_path='/uploads')

    if config_name:
        config = __import__("app.config", fromlist=[config_name]).config.get(
            config_name, get_config()
        )
    else:
        config = get_config()

    app.config.from_object(config)

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    frontend = app.config.get('FRONTEND_URL', 'http://localhost:5173')
    allowed_origins = ['http://localhost:5173', 'http://localhost:3000']
    if frontend not in allowed_origins:
        allowed_origins.append(frontend)

    CORS(app,
         origins=allowed_origins,
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])

    # Manually handle OPTIONS — Railway proxy sometimes blocks Flask-CORS from responding
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            origin = request.headers.get("Origin", "")
            if origin in allowed_origins:
                res = make_response("", 200)
                res.headers["Access-Control-Allow-Origin"] = origin
                res.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
                res.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
                res.headers["Access-Control-Allow-Credentials"] = "true"
                res.headers["Access-Control-Max-Age"] = "86400"
                return res

    app.register_blueprint(auth_bp, url_prefix='/api/v1')
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
    app.register_blueprint(payment_bp, url_prefix='/api/v1')

    register_event_listeners()
    setup_logging(app)

    with app.app_context():
        db.create_all()

    @app.route("/health", methods=["GET"])
    def health_check():
        return {"status": "healthy"}, 200

    @app.errorhandler(400)
    def bad_request(error):
        return {"error": "Bad Request", "status_code": 400}, 400

    @app.errorhandler(401)
    def unauthorized(error):
        return {"error": "Unauthorized", "status_code": 401}, 401

    @app.errorhandler(403)
    def forbidden(error):
        return {"error": "Forbidden", "status_code": 403}, 403

    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not Found", "status_code": 404}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {"error": "Internal Server Error", "status_code": 500}, 500

    return app


def setup_logging(app):
    if not app.debug:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)