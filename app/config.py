import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://marketplace_user:super_secret_password@marketplace_db:5432/marketplace_db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
