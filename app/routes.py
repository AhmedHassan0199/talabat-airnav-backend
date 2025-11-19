from flask import Blueprint, jsonify

main_bp = Blueprint("main", __name__)


@main_bp.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "market-backend"}), 200
