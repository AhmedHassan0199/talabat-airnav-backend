# app/models.py
from datetime import datetime
from . import db
from werkzeug.security import generate_password_hash, check_password_hash

# -------- User ---------
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(32), nullable=False, default="CUSTOMER")  # CUSTOMER / SELLER / ADMIN
    phone = db.Column(db.String(30), nullable=True)

    building = db.Column(db.String(10), nullable=True)
    floor = db.Column(db.String(10), nullable=True)
    apartment = db.Column(db.String(10), nullable=True)

    password_hash = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


# -------- Store ---------
class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)  # FOOD / DESSERT / CLOTHES / ...
    is_active = db.Column(db.Boolean, default=True)

    min_order_amount = db.Column(db.Numeric(10, 2), nullable=True)
    delivery_fee = db.Column(db.Numeric(10, 2), nullable=True)

    open_from = db.Column(db.Time, nullable=True)  # optional
    open_to = db.Column(db.Time, nullable=True)    # optional

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship("User", backref=db.backref("stores", lazy="dynamic"))

    def __repr__(self):
        return f"<Store {self.name} (owner={self.owner_id})>"


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)

    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    image_url = db.Column(db.String(255))  # Photo (هنستخدم URL في v1)
    stock = db.Column(db.Integer, nullable=False, default=0)

    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    store = db.relationship(
        "Store",
        backref=db.backref("products", lazy=True, cascade="all, delete-orphan"),
    )

# -------- Order ---------
class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)

    status = db.Column(db.String(20), nullable=False, default="PENDING")
    # PENDING / ACCEPTED / REJECTED / PREPARING / READY / ON_THE_WAY / DELIVERED / CANCELLED

    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    delivery_method = db.Column(db.String(20), nullable=False, default="DELIVERY")  # DELIVERY / PICKUP

    notes = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = db.relationship("User", backref=db.backref("orders", lazy="dynamic"))
    store = db.relationship("Store", backref=db.backref("orders", lazy="dynamic"))

    def __repr__(self):
        return f"<Order {self.id} store={self.store_id} customer={self.customer_id}>"


# -------- OrderItem ---------
class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    product_name = db.Column(db.String(120), nullable=False)  # snapshot
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)

    order = db.relationship("Order", backref=db.backref("items", lazy="dynamic"))
    product = db.relationship("Product")

    def __repr__(self):
        return f"<OrderItem order={self.order_id} product={self.product_id} qty={self.quantity}>"
