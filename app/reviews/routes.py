from flask import Blueprint, jsonify
from app.auth.routes import get_current_user_from_request
from app.models import StoreReview

profile_bp = Blueprint("profile", __name__)

@profile_bp.route("/my-reviews", methods=["GET"])
def my_reviews():
    current_user, error = get_current_user_from_request(allowed_roles=["CUSTOMER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    reviews = (
        StoreReview.query
        .filter_by(customer_id=current_user.id)
        .order_by(StoreReview.created_at.desc())
        .limit(20)
        .all()
    )

    return jsonify(
        [
            {
                "id": r.id,
                "store_id": r.store_id,
                "store_name": r.store.name,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at.isoformat(),
            }
            for r in reviews
        ]
    ), 200
