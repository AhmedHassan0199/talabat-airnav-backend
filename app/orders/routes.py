from flask import Blueprint, jsonify
from app.auth.routes import get_current_user_from_request
from app.models import Order

orders_bp = Blueprint("orders", __name__)

@orders_bp.route("/my", methods=["GET"])
def my_orders():
    current_user, error = get_current_user_from_request(allowed_roles=["CUSTOMER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    orders = (
        Order.query
        .filter_by(customer_id=current_user.id)
        .order_by(Order.created_at.desc())
        .limit(10)
        .all()
    )

    return jsonify(
        [
            {
                "id": o.id,
                "store_id": o.store_id,
                "store_name": o.store.name,
                "status": o.status,
                "total_amount": float(o.total_amount or 0),
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ]
    ), 200
