# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from .config import Config


db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # CORS – نفس اللي عاملُه في الأبليكيشن الأول
    CORS(
        app,
        origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://airnav-compound-frontend.vercel.app",
            "http://95.179.181.72:3000",
            "http://airnav-compound.work.gd",
            "http://market.airnav-compound.work.gd",
        ],
        supports_credentials=True,
    )

    db.init_app(app)
    migrate.init_app(app, db)

    # مهم علشان models تتسجل
    from . import models  # noqa: F401

    # Blueprints
    from .routes import main_bp
    from .auth.routes import auth_bp
    from .stores.routes import stores_bp
    from .uploads.routes import uploads_bp
    from app.orders.routes import orders_bp
    from app.reviews.routes import profile_bp


    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(stores_bp, url_prefix="/api/stores")
    app.register_blueprint(uploads_bp, url_prefix="/api/uploads")
    app.register_blueprint(orders_bp, url_prefix="/api/orders")
    app.register_blueprint(profile_bp, url_prefix="/api/profile")

    # بعدين هنزود:
    # from .seller_routes import seller_bp
    # from .customer_routes import customer_bp
    # app.register_blueprint(seller_bp, url_prefix="/api/seller")
    # app.register_blueprint(customer_bp, url_prefix="/api/customer")

    return app
