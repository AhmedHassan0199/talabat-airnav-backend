from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from .config import Config
from .database import db
from .auth_routes import auth_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    JWTManager(app)

    # CORS – allow your NextJS origin
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},  # in prod, restrict this to your domain
        supports_credentials=True,
    )

    # Blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    # Create tables (for now, simple create_all; later use Alembic)
    with app.app_context():
        db.create_all()

    return app
