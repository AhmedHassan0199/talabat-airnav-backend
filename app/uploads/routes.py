import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from app.auth.routes import get_current_user_from_request

uploads_bp = Blueprint("uploads", __name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@uploads_bp.route("/product-image", methods=["POST"])
def upload_product_image():
    # لازم يكون SELLER
    current_user, error = get_current_user_from_request(allowed_roles=["SELLER"])
    if error:
        msg, status = error
        return jsonify({"message": msg}), status

    if "file" not in request.files:
        return jsonify({"message": "لم يتم إرسال أي ملف"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"message": "اسم الملف فارغ"}), 400

    if not allowed_file(file.filename):
        return jsonify({"message": "نوع الملف غير مدعوم"}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[1].lower()

    # اسم فريد
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    media_root = current_app.config["MEDIA_ROOT"]
    product_dir = os.path.join(media_root, "products")
    os.makedirs(product_dir, exist_ok=True)

    save_path = os.path.join(product_dir, unique_name)
    file.save(save_path)

    # URL اللي الـ frontend هيستخدمه
    media_url_path = current_app.config.get("MEDIA_URL_PATH", "/media")
    public_url = f"{media_url_path}/products/{unique_name}"

    return jsonify({"url": public_url}), 201
