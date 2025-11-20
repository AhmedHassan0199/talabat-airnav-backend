# app/auth/routes.py
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import jwt

from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)

VALID_ROLES = {"CUSTOMER", "SELLER"}
DEFAULT_ROLE = "CUSTOMER"


def generate_token(user: User):
    payload = {
        "sub": user.id,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(days=30),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def get_current_user_from_request(allowed_roles=None):
    """
    نفس الفكرة الموجودة عندك:
    - تقرأ Authorization: Bearer <token>
    - تفك الـ JWT
    - ترجّع (user, None) لو تمام
    - أو (None, (message, status_code)) لو في مشكلة
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, ("Missing or invalid Authorization header", 401)

    token = auth_header.split(" ", 1)[1].strip()
    try:
        data = jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None, ("Token expired, please login again", 401)
    except jwt.InvalidTokenError:
        return None, ("Invalid token", 401)

    user_id = data.get("sub")
    role = data.get("role")

    user = User.query.get(user_id)
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
