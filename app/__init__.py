from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import os

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)

    # Config from env
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://marketadmin:Market123@market-db:5432/marketdb",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # CORS: allow your new domain
    CORS(
        app,
        origins=[
            "https://market-airnav-compound.work.gd",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        supports_credentials=True,
    )

    db.init_app(app)
    migrate.init_app(app, db)

    from . import models  # noqa: F401

    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app
