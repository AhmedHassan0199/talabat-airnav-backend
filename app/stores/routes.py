from flask import Blueprint, jsonify, request
from app import db
from app.models import Store
from app.auth.routes import get_current_user_from_request

stores_bp = Blueprint("stores", __name__)

@stores_bp.route("/my", methods=["GET"])
def get_my_store():
    """
    يرجّع المتجر الخاص بصاحب الحساب (SELLER).
    لو مفيش متجر بيرجع 404 برسالة واضحة.
    """
    current_user, error = get_current_user_from_request(allowed_roles=["SELLER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    store = Store.query.filter_by(owner_id=current_user.id).first()
    if not store:
        return jsonify({"message": "لم يتم إنشاء متجر بعد"}), 404

    return jsonify(
        {
            "id": store.id,
            "name": store.name,
            "description": store.description,
            "category": store.category,
            "min_order_amount": float(store.min_order_amount or 0),
            "delivery_fee": float(store.delivery_fee or 0),
            "is_active": store.is_active,
        }
    ), 200


@stores_bp.route("/my", methods=["POST"])
def create_or_update_my_store():
    """
    إنشاء أو تعديل المتجر الخاص بصاحب الحساب.
    - لو مفيش store يعمل create
    - لو فيه يعمل update
    """
    current_user, error = get_current_user_from_request(allowed_roles=["SELLER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    description = data.get("description")
    category = data.get("category") or "FOOD"
    min_order_amount = data.get("min_order_amount") or 0
    delivery_fee = data.get("delivery_fee") or 0

    if not name:
        return jsonify({"message": "اسم المتجر مطلوب"}), 400

    store = Store.query.filter_by(owner_id=current_user.id).first()

    if not store:
        # create
        store = Store(
            owner_id=current_user.id,
            name=name,
            description=description,
            category=category,
            min_order_amount=min_order_amount,
            delivery_fee=delivery_fee,
            is_active=True,
        )
        db.session.add(store)
    else:
        # update
        store.name = name
        store.description = description
        store.category = category
        store.min_order_amount = min_order_amount
        store.delivery_fee = delivery_fee

    db.session.commit()

    return jsonify(
        {
            "message": "تم حفظ بيانات المتجر",
            "id": store.id,
            "name": store.name,
            "description": store.description,
            "category": store.category,
            "min_order_amount": float(store.min_order_amount or 0),
            "delivery_fee": float(store.delivery_fee or 0),
            "is_active": store.is_active,
        }
    ), 200
