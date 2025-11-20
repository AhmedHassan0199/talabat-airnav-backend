from datetime import datetime, timedelta

import jwt
from flask import Blueprint, request, jsonify, current_app

from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)

VALID_ROLES = {"CUSTOMER", "SELLER"}
DEFAULT_ROLE = "CUSTOMER"


def generate_token(user: User) -> str:
    """
    Generate a signed JWT for the given user.
    """
    secret = current_app.config.get("JWT_SECRET")
    if not secret:
        # fallback على SECRET_KEY لو JWT_SECRET مش مطلوب
        secret = current_app.config.get("SECRET_KEY", "dev-jwt-secret")

    payload = {
        "sub": str(user.id),          # نخليها string عشان نبقى متوافقين مع PyJWT 2
        "role": user.role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=30),
    }

    token = jwt.encode(payload, secret, algorithm="HS256")

    # PyJWT 1.x بيرجع bytes – 2.x بيرجع str
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def get_current_user_from_request(allowed_roles=None):
    """
    - تقرأ Authorization: Bearer <token>
    - تفك JWT بنفس JWT_SECRET
    - تجيب الـ User من الـ DB
    - لو allowed_roles متحديد، تتأكد إن role فيهم
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, ("Missing or invalid Authorization header", 401)

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None, ("Missing or invalid Authorization header", 401)

    secret = current_app.config.get("JWT_SECRET")
    if not secret:
        secret = current_app.config.get("SECRET_KEY", "dev-jwt-secret")

    try:
        data = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None, ("Token expired, please login again", 401)
    except jwt.InvalidTokenError:
        return None, ("Invalid token", 401)

    user_id = data.get("sub")
    role = data.get("role")

    if not user_id:
        return None, ("Invalid token payload", 401)

    # user_id string → int
    try:
        user_id_int = int(user_id)
    except ValueError:
        return None, ("Invalid token payload", 401)

    user = User.query.get(user_id_int)
    if not user:
        return None, ("User not found", 404)

    if allowed_roles is not None and role not in allowed_roles:
        return None, ("Not allowed", 403)

    return user, None


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    username = data.get("username", "").strip()
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    phone = data.get("phone")
    building = data.get("building")
    floor = data.get("floor")
    apartment = data.get("apartment")

    # NEW: role coming from frontend (desired_role)
    desired_role = (data.get("desired_role") or "").strip().upper()

    if not username or not full_name or not email or not password:
        return jsonify({"message": "برجاء إدخال كل البيانات المطلوبة"}), 400

    # unique checks
    if User.query.filter_by(username=username).first():
        return jsonify({"message": "اسم المستخدم مستخدم بالفعل"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "هذا البريد مستخدم بالفعل"}), 400

    # ✅ determine final role
    role = desired_role if desired_role in VALID_ROLES else DEFAULT_ROLE

    user = User(
        username=username,
        full_name=full_name,
        email=email,
        role=role,        # 👈 مهم
        phone=phone,
        building=building,
        floor=floor,
        apartment=apartment,
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    token = generate_token(user)

    return jsonify(
        {
            "message": "تم إنشاء الحساب بنجاح",
            "access_token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "building": user.building,
                "floor": user.floor,
                "apartment": user.apartment,
                "phone": user.phone,
            },
        }
    ), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username_or_email = data.get("username_or_email", "").strip()
    password = data.get("password", "").strip()

    if not username_or_email or not password:
        return jsonify({"message": "برجاء إدخال اسم المستخدم/البريد وكلمة المرور"}), 400

    user = (
        User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email.lower())
        )
        .first()
    )

    if not user or not user.check_password(password):
        return jsonify({"message": "بيانات الدخول غير صحيحة"}), 401

    token = generate_token(user)

    return jsonify(
        {
            "access_token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
            },
        }
    ), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    user, error = get_current_user_from_request()
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    return jsonify(
        {
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "building": user.building,
                "floor": user.floor,
                "apartment": user.apartment,
            }
        }
    ), 200
