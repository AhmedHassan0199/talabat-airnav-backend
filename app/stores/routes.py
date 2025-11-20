from flask import Blueprint, jsonify, request
from app import db
from app.models import Store, Product
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

@stores_bp.route("/my/products", methods=["GET"])
def list_my_products():
    current_user, error = get_current_user_from_request(allowed_roles=["SELLER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    store = Store.query.filter_by(owner_id=current_user.id).first()
    if not store:
        return jsonify({"message": "لم يتم إنشاء متجر بعد"}), 404

    products = (
        Product.query.filter_by(store_id=store.id)
        .order_by(Product.created_at.desc())
        .all()
    )

    return jsonify(
        [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": float(p.price),
                "image_url": p.image_url,
                "stock": p.stock,
                "is_active": p.is_active,
            }
            for p in products
        ]
    ), 200

@stores_bp.route("/my/products", methods=["POST"])
def create_product():
    current_user, error = get_current_user_from_request(allowed_roles=["SELLER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    store = Store.query.filter_by(owner_id=current_user.id).first()
    if not store:
        return jsonify({"message": "لم يتم إنشاء متجر بعد"}), 404

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    description = data.get("description")
    price = data.get("price")
    image_url = data.get("image_url")
    stock = data.get("stock", 0)
    is_active = data.get("is_active", True)

    if not name:
        return jsonify({"message": "اسم المنتج مطلوب"}), 400

    try:
        price_value = float(price)
    except (TypeError, ValueError):
        return jsonify({"message": "سعر المنتج غير صالح"}), 400

    try:
        stock_value = int(stock)
    except (TypeError, ValueError):
        stock_value = 0

    product = Product(
        store_id=store.id,
        name=name,
        description=description,
        price=price_value,
        image_url=image_url,
        stock=stock_value,
        is_active=bool(is_active),
    )

    db.session.add(product)
    db.session.commit()

    return jsonify(
        {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "image_url": product.image_url,
            "stock": product.stock,
            "is_active": product.is_active,
        }
    ), 201

@stores_bp.route("/my/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    current_user, error = get_current_user_from_request(allowed_roles=["SELLER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    store = Store.query.filter_by(owner_id=current_user.id).first()
    if not store:
        return jsonify({"message": "لم يتم إنشاء متجر بعد"}), 404

    product = Product.query.filter_by(id=product_id, store_id=store.id).first()
    if not product:
        return jsonify({"message": "المنتج غير موجود"}), 404

    data = request.get_json() or {}

    name = data.get("name")
    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({"message": "اسم المنتج لا يمكن أن يكون فارغاً"}), 400
        product.name = name

    if "description" in data:
        product.description = data.get("description")

    if "price" in data:
        try:
            product.price = float(data.get("price"))
        except (TypeError, ValueError):
            return jsonify({"message": "سعر المنتج غير صالح"}), 400

    if "image_url" in data:
        product.image_url = data.get("image_url")

    if "stock" in data:
        try:
            product.stock = int(data.get("stock"))
        except (TypeError, ValueError):
            product.stock = 0

    if "is_active" in data:
        product.is_active = bool(data.get("is_active"))

    db.session.commit()

    return jsonify(
        {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "image_url": product.image_url,
            "stock": product.stock,
            "is_active": product.is_active,
        }
    ), 200

@stores_bp.route("/my/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    current_user, error = get_current_user_from_request(allowed_roles=["SELLER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    store = Store.query.filter_by(owner_id=current_user.id).first()
    if not store:
        return jsonify({"message": "لم يتم إنشاء متجر بعد"}), 404

    product = Product.query.filter_by(id=product_id, store_id=store.id).first()
    if not product:
        return jsonify({"message": "المنتج غير موجود"}), 404

    db.session.delete(product)
    db.session.commit()

    return jsonify({"message": "تم حذف المنتج"}), 200

