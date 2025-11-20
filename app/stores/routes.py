from flask import Blueprint, jsonify, request
from app import db
from app.auth.routes import get_current_user_from_request
from sqlalchemy import func
from app.models import Store, Product, StoreReview
from datetime import datetime

stores_bp = Blueprint("stores", __name__)

@stores_bp.route("/my", methods=["GET", "PUT"])
def my_store():
    """
    GET  -> رجّع بيانات متجر البائع الحالي
    PUT  -> حدّث بيانات متجر البائع الحالي
    """
    current_user, error = get_current_user_from_request(allowed_roles=["SELLER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    store = Store.query.filter_by(owner_id=current_user.id).first()

    # -------- GET: رجوع بيانات المتجر --------
    if request.method == "GET":
        if not store:
            return jsonify({"message": "لم يتم إنشاء متجر بعد لهذا المستخدم"}), 404

        return jsonify(
            {
                "id": store.id,
                "name": store.name,
                "description": store.description,
                "category": store.category,
                "min_order_amount": float(store.min_order_amount or 0),
                "delivery_fee": float(store.delivery_fee or 0),
                "profile_image_url": store.profile_image_url,
                "is_active": store.is_active,
            }
        ), 200

    # -------- PUT: تحديث بيانات المتجر --------
    data = request.get_json() or {}

    # لو المتجر مش موجود، ممكن:
    # - إما نرجع 404
    # - أو ننشئ متجر جديد للبائع
    # أنا هنا هختار إننا نرجع 404 عشان الأمور تبقى واضحة
    if not store:
        return jsonify({"message": "لم يتم إنشاء متجر بعد لهذا المستخدم"}), 404

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"message": "اسم المتجر مطلوب"}), 400

    store.name = name
    store.description = (data.get("description") or "").strip() or None
    store.category = data.get("category") or store.category

    min_order_amount = data.get("min_order_amount")
    delivery_fee = data.get("delivery_fee")

    try:
        store.min_order_amount = float(min_order_amount) if min_order_amount is not None else 0
        store.delivery_fee = float(delivery_fee) if delivery_fee is not None else 0
    except (TypeError, ValueError):
        return jsonify({"message": "قيمة الحد الأدنى أو مصاريف التوصيل غير صالحة"}), 400

    # صورة البروفايل (لو جت من الـ Frontend بعد الـ upload)
    if "profile_image_url" in data:
        store.profile_image_url = data.get("profile_image_url") or None

    db.session.commit()

    return jsonify(
        {
            "id": store.id,
            "name": store.name,
            "description": store.description,
            "category": store.category,
            "min_order_amount": float(store.min_order_amount or 0),
            "delivery_fee": float(store.delivery_fee or 0),
            "profile_image_url": store.profile_image_url,
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

def serialize_store_with_rating(store: Store):
    avg, count = db.session.query(
        func.coalesce(func.avg(StoreReview.rating), 0),
        func.count(StoreReview.id)
    ).filter(StoreReview.store_id == store.id).one()

    avg_value = float(avg or 0)
    return {
        "id": store.id,
        "name": store.name,
        "description": store.description,
        "category": store.category,
        "min_order_amount": float(store.min_order_amount or 0),
        "delivery_fee": float(store.delivery_fee or 0),
        "is_active": store.is_active,
        "profile_image_url": store.profile_image_url,
        "avg_rating": round(avg_value, 1),
        "reviews_count": int(count),
    }

@stores_bp.route("", methods=["GET"])
def list_active_stores():
    category = request.args.get("category")
    search = request.args.get("search")

    query = Store.query.filter_by(is_active=True)

    if category:
        query = query.filter(Store.category == category)

    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            db.or_(Store.name.ilike(like), Store.description.ilike(like))
        )

    stores = query.order_by(Store.created_at.desc()).all()
    return jsonify([serialize_store_with_rating(s) for s in stores]), 200

@stores_bp.route("/<int:store_id>", methods=["GET"])
def get_store_with_products(store_id):
    store = Store.query.filter_by(id=store_id, is_active=True).first()
    if not store:
        return jsonify({"message": "المتجر غير موجود أو غير متاح حالياً"}), 404

    products = (
        Product.query
        .filter_by(store_id=store.id, is_active=True)
        .order_by(Product.created_at.asc())
        .all()
    )

    avg, count = db.session.query(
        func.coalesce(func.avg(StoreReview.rating), 0),
        func.count(StoreReview.id)
    ).filter(StoreReview.store_id == store.id).one()

    avg_value = float(avg or 0)

    return jsonify(
        {
            "store": {
                "id": store.id,
                "name": store.name,
                "description": store.description,
                "category": store.category,
                "min_order_amount": float(store.min_order_amount or 0),
                "delivery_fee": float(store.delivery_fee or 0),
                "profile_image_url": store.profile_image_url,
                "avg_rating": round(avg_value, 1),
                "reviews_count": int(count),
            },
            "products": [
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
            ],
        }
    ), 200

@stores_bp.route("/<int:store_id>/reviews", methods=["GET"])
def list_store_reviews(store_id):
    store = Store.query.filter_by(id=store_id, is_active=True).first()
    if not store:
        return jsonify({"message": "المتجر غير موجود"}), 404

    reviews = (
        StoreReview.query
        .filter_by(store_id=store.id)
        .order_by(StoreReview.created_at.desc())
        .limit(50)
        .all()
    )

    return jsonify(
        [
            {
                "id": r.id,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at.isoformat(),
                "customer_name": r.customer.full_name,
            }
            for r in reviews
        ]
    ), 200

@stores_bp.route("/<int:store_id>/reviews", methods=["POST"])
def add_store_review(store_id):
    current_user, error = get_current_user_from_request(allowed_roles=["CUSTOMER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    store = Store.query.filter_by(id=store_id, is_active=True).first()
    if not store:
        return jsonify({"message": "المتجر غير موجود"}), 404

    data = request.get_json() or {}
    rating = data.get("rating")
    comment = (data.get("comment") or "").strip()

    try:
      rating = int(rating)
    except (TypeError, ValueError):
      return jsonify({"message": "قيمة التقييم غير صالحة"}), 400

    if rating < 1 or rating > 5:
      return jsonify({"message": "التقييم يجب أن يكون بين 1 و 5"}), 400

    # اختيارياً: السماح بتقييم واحد لكل عميل لكل متجر
    existing = StoreReview.query.filter_by(
        store_id=store.id, customer_id=current_user.id
    ).first()
    if existing:
        existing.rating = rating
        existing.comment = comment or existing.comment
        existing.created_at = datetime.utcnow()
        db.session.commit()
        review = existing
    else:
        review = StoreReview(
            store_id=store.id,
            customer_id=current_user.id,
            rating=rating,
            comment=comment or None,
        )
        db.session.add(review)
        db.session.commit()

    return jsonify(
        {
            "id": review.id,
            "rating": review.rating,
            "comment": review.comment,
            "created_at": review.created_at.isoformat(),
            "customer_name": review.customer.full_name,
        }
    ), 201

