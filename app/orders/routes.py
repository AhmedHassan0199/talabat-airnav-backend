# app/orders/routes.py

from flask import Blueprint, jsonify, request
from app import db
from app.auth.routes import get_current_user_from_request
from app.models import Store, Product, Order, OrderItem
from datetime import datetime

orders_bp = Blueprint("orders", __name__)

def serialize_order(order: Order, include_items: bool = True):
    base = {
        "id": order.id,
        "store_id": order.store_id,
        "store_name": order.store.name if order.store else None,
        "customer_id": order.customer_id,
        "customer_name": order.customer.full_name if order.customer else None,
        "status": order.status,
        "total_amount": float(order.total_amount or 0),
        "delivery_method": order.delivery_method,
        "notes": order.notes,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }
    if include_items:
        base["items"] = [
            {
                "id": it.id,
                "product_id": it.product_id,
                "product_name": it.product_name,
                "unit_price": float(it.unit_price),
                "quantity": it.quantity,
                "subtotal": float(it.subtotal),
            }
            for it in order.items
        ]
    return base


# ---------- Customer: create order ----------
@orders_bp.route("", methods=["POST"])
def create_order():
    """
    Customer creates an order.
    body:
    {
      "store_id": 1,
      "items": [{ "product_id": 10, "quantity": 2 }, ...],
      "delivery_method": "DELIVERY" | "PICKUP",
      "notes": "no onions"
    }
    """
    current_user, error = get_current_user_from_request(allowed_roles=["CUSTOMER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    data = request.get_json() or {}
    store_id = data.get("store_id")
    items_data = data.get("items") or []
    delivery_method = data.get("delivery_method") or "DELIVERY"
    notes = (data.get("notes") or "").strip() or None

    if not store_id:
        return jsonify({"message": "store_id مطلوب"}), 400

    if not items_data:
        return jsonify({"message": "قائمة المنتجات فارغة"}), 400

    store = Store.query.filter_by(id=store_id, is_active=True).first()
    if not store:
        return jsonify({"message": "المتجر غير موجود أو غير متاح"}), 404

    # Validate products & same store
    product_ids = [it.get("product_id") for it in items_data if it.get("product_id")]
    if not product_ids:
        return jsonify({"message": "قائمة المنتجات غير صالحة"}), 400

    products = Product.query.filter(
        Product.id.in_(product_ids),
        Product.store_id == store.id,
        Product.is_active == True
    ).all()

    products_by_id = {p.id: p for p in products}
    total_amount = 0

    order_items = []
    for it in items_data:
        pid = it.get("product_id")
        qty = it.get("quantity", 1)
        try:
            qty = int(qty)
        except (TypeError, ValueError):
            qty = 1
        if qty <= 0:
            qty = 1

        product = products_by_id.get(pid)
        if not product:
            return jsonify({"message": f"المنتج {pid} غير متاح"}), 400

        unit_price = float(product.price or 0)
        subtotal = unit_price * qty
        total_amount += subtotal

        order_items.append(
            {
                "product": product,
                "quantity": qty,
                "unit_price": unit_price,
                "subtotal": subtotal,
            }
        )

    order = Order(
        customer_id=current_user.id,
        store_id=store.id,
        status="PENDING",              # New / Pending Approval
        delivery_method=delivery_method,
        notes=notes,
        total_amount=total_amount,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(order)
    db.session.flush()  # to get order.id

    for oi in order_items:
        item = OrderItem(
            order_id=order.id,
            product_id=oi["product"].id,
            product_name=oi["product"].name,
            unit_price=oi["unit_price"],
            quantity=oi["quantity"],
            subtotal=oi["subtotal"],
        )
        db.session.add(item)

    db.session.commit()

    return jsonify(serialize_order(order)), 201


# ---------- Customer: list my orders ----------
@orders_bp.route("/my", methods=["GET"])
def my_orders():
    current_user, error = get_current_user_from_request(allowed_roles=["CUSTOMER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    orders = (
        Order.query.filter_by(customer_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return jsonify([serialize_order(o) for o in orders]), 200


# ---------- Seller: list store orders ----------
@orders_bp.route("/seller", methods=["GET"])
def seller_orders():
    current_user, error = get_current_user_from_request(allowed_roles=["SELLER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    store = Store.query.filter_by(owner_id=current_user.id).first()
    if not store:
        return jsonify({"message": "لم يتم إنشاء متجر بعد لهذا المستخدم"}), 404

    orders = (
        Order.query.filter_by(store_id=store.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return jsonify([serialize_order(o) for o in orders]), 200


# ---------- Seller: update order status ----------
@orders_bp.route("/<int:order_id>/status", methods=["POST"])
def update_order_status(order_id):
    """
    Seller moves order through workflow:
    PENDING -> ACCEPTED / REJECTED
    ACCEPTED -> PREPARING
    PREPARING -> ON_THE_WAY
    ON_THE_WAY -> DELIVERED
    body: { "status": "ACCEPTED", "mark_paid": true/false }
    """
    current_user, error = get_current_user_from_request(allowed_roles=["SELLER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    store = Store.query.filter_by(owner_id=current_user.id).first()
    if not store:
        return jsonify({"message": "لم يتم إنشاء متجر بعد لهذا المستخدم"}), 404

    order = Order.query.filter_by(id=order_id, store_id=store.id).first()
    if not order:
        return jsonify({"message": "الطلب غير موجود"}), 404

    data = request.get_json() or {}
    new_status = data.get("status")
    mark_paid = bool(data.get("mark_paid", False))

    if new_status not in [
        "PENDING",
        "ACCEPTED",
        "REJECTED",
        "PREPARING",
        "ON_THE_WAY",
        "DELIVERED",
        "CANCELLED",
    ]:
        return jsonify({"message": "حالة غير صالحة"}), 400

    order.status = new_status
    if mark_paid:
        # لو حابب تضيف عمود is_paid في الـ Model
        # order.is_paid = True
        pass

    order.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify(serialize_order(order)), 200
