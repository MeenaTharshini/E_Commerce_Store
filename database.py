from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(200))
    role = db.Column(db.String(20), default="user")  
    # roles: user | provider

class Product(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100))

    price = db.Column(db.Float)

    description = db.Column(db.String(500))

    image = db.Column(db.String(300))

    category = db.Column(db.String(100))

    quantity = db.Column(db.Integer)
    discount = db.Column(db.Integer,default=0)
    stock_status = db.Column(
        db.String(20),
        default="In Stock"
    )

    provider_email = db.Column(
        db.String(100),
        nullable=False
    )
    
class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), nullable=False)

    product_id = db.Column(db.Integer, nullable=False)

    product_name = db.Column(db.String(100), nullable=False)

    image = db.Column(db.String(255), default="default.png")   # Product image

    quantity = db.Column(db.Integer, default=1)

    price = db.Column(db.Float)  
    
    payment_method = db.Column(db.String(50))

    status = db.Column(db.String(50), default="Pending")

    order_date = db.Column(db.DateTime, default=datetime.utcnow)

    review = db.Column(db.Text)

    rating = db.Column(db.Integer)

    review_image = db.Column(db.String(255))

class Favorite(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100)
    )

    product_id = db.Column(
        db.Integer
    )

class Wishlist(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100)
    )

    product_id = db.Column(
        db.Integer
    )

class Review(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    product_id = db.Column(
        db.Integer
    )

    username = db.Column(
        db.String(100)
    )

    rating = db.Column(
        db.Integer
    )

    comment = db.Column(
        db.Text
    )

    image = db.Column(
        db.String(200)
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )