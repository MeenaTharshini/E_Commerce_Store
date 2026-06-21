import os
from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import db, User, Product, Order
from datetime import datetime
from database import *

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['SECRET_KEY'] = 'minu123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ------------------------
# INIT DB + SAMPLE DATA
# ------------------------

with app.app_context():

    db.create_all()

    if Product.query.count() == 0:

        products = []

        db.session.add_all(products)
        db.session.commit()

# ------------------------
# CART (simple in-memory)
# ------------------------
cart = {}


# ------------------------
# AUTH CHECK
# ------------------------
def login_required(func):
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect("/login")
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# ------------------------
# REGISTER
# ------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        if request.form['password'] != request.form['confirm_password']:
            return "Passwords do not match"

        if User.query.filter_by(email=request.form['email']).first():
            return "Email already registered"

        user_role = request.form.get('role')  # ✅ IMPORTANT FIX

        user = User(
            fullname=request.form['fullname'],
            email=request.form['email'],
            phone=request.form['phone'],
            password=generate_password_hash(request.form['password']),
            role=request.form['role']
        )

        db.session.add(user)
        db.session.commit()

        return redirect('/login')

    return render_template('register.html')

# ------------------------
# LOGIN
# ------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        user = User.query.filter_by(email=request.form['email']).first()

        if user and check_password_hash(user.password, request.form['password']):

            session.clear()
            session['user_id'] = user.id
            session['username'] = user.fullname
            session['email'] = user.email
            session['role'] = user.role

            if user.role == "provider":
                return redirect('/provider_dashboard')

            return redirect('/user/dashboard')

        return render_template('login.html', error="Invalid email or password")

    return render_template('login.html')

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if session.get('role') != "user":
        return redirect('/login')

    products = Product.query.all()
    return render_template('products.html', products=products)

@app.route("/provider_dashboard")
@login_required
def provider_dashboard():

    if session.get("role") != "provider":
        return redirect("/login")

    # Provider's products only
    products = Product.query.filter_by(
        provider_email=session['email']
    ).all()

    # CREATE product_ids FIRST
    product_ids = [p.id for p in products]

    # Provider's orders only
    orders = Order.query.filter(
        Order.product_id.in_(product_ids)
    ).order_by(Order.id.desc()).all()

    total_products = len(products)
    total_orders = len(orders)

    total_sales = 0

    for o in orders:
        if o.status == "Delivered":
            total_sales += (o.price or 0) * o.quantity

    low_stock = sum(
        1 for p in products
        if p.stock_status == "Out of Stock"
    )

    return render_template(
        "provider_dashboard.html",
        products=products,
        orders=orders,
        total_products=total_products,
        total_orders=total_orders,
        total_sales=round(total_sales, 2),
        low_stock=low_stock
    )

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():

    if session.get('role') != "provider":
        return redirect('/login')

    if request.method == 'POST':

        image_file = request.files.get('image')

        filename = "default.png"

        if image_file and image_file.filename:

            filename = secure_filename(image_file.filename)

            image_path = os.path.join(
                app.config['UPLOAD_FOLDER'],
                filename
            )

            image_file.save(image_path)

        product = Product(
            name=request.form['name'],
            price=float(request.form['price']),
            discount=int(request.form.get("discount",0)),
            description=request.form['description'],
            provider_email=session['email'],
            image=filename,
            stock_status=request.form['stock_status']
        )

        db.session.add(product)
        db.session.commit()

        return redirect('/provider_dashboard')

    return render_template('add_product.html')

@app.route('/delete_product/<int:id>')
@login_required
def delete_product(id):

    # Only providers can delete products
    if session.get('role') != 'provider':
        return redirect('/login')

    product = Product.query.get_or_404(id)

    # Check ownership
    if product.provider_email != session.get('email'):
        return "Unauthorized", 403

    # Delete product
    db.session.delete(product)
    db.session.commit()

    return redirect('/provider_dashboard')

@app.route("/edit_product/<int:id>", methods=["GET", "POST"])
@login_required
def edit_product(id):

    product = Product.query.get_or_404(id)

    # optional security (recommended)
    if product.provider_email != session.get("email"):
        return "Unauthorized", 403

    if request.method == "POST":

        # UPDATE existing product (NOT create new one)
        product.name = request.form["name"]
        product.description = request.form["description"]
        product.price = float(request.form["price"])
        product.discount = int(request.form.get("discount", 0))
        product.stock_status = request.form["stock_status"]

        image = request.files.get("image")

        if image and image.filename:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            product.image = filename

        # IMPORTANT: no db.session.add()
        db.session.commit()

        return redirect("/provider_dashboard")

    return render_template("edit_product.html", product=product)

@app.route('/change_stock/<int:id>')
@login_required
def change_stock(id):

    product = Product.query.get_or_404(id)

    if product.stock_status == "In Stock":
        product.stock_status = "Out of Stock"
    else:
        product.stock_status = "In Stock"

    db.session.commit()

    return redirect('/provider_dashboard')

# ------------------------
# PRODUCTS
# ------------------------
@app.route('/products')
@login_required
def products():
    return render_template('products.html', products=Product.query.all())

@app.route('/product/<int:id>')
@login_required
def product_detail(id):

    product = Product.query.get_or_404(id)

    related_products = Product.query.filter(
        Product.id != product.id
    ).limit(4).all()

    return render_template(
        'product_detail.html',
        product=product,
        related_products=related_products
    )

@app.route("/api/search")
@login_required
def api_search():
    query = request.args.get("q", "").lower().strip()

    if not query:
        return {"results": []}

    products = Product.query.filter_by(
        provider_email=session["email"]
    ).all()
    results = []

    for p in products:
        name = p.name.lower()
        desc = (p.description or "").lower()

        score = 0

        if query in name:
            score += 80
        if query == name:
            score += 100
        if query in desc:
            score += 30

        # word match boost
        for w in query.split():
            if w in name:
                score += 25

        if score > 0:
            results.append({
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "image": p.image,
                "score": score
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    return {"results": results[:8]}

@app.route('/favorite/<int:id>')
@login_required
def favorite(id):

    fav = Favorite(
        username=session['username'],
        product_id=id
    )

    db.session.add(fav)
    db.session.commit()

    return redirect(f'/product/{id}')
# ------------------------
# CART ACTIONS
# ------------------------
@app.route('/addcart/<int:id>')
@login_required
def addcart(id):

    product = Product.query.get_or_404(id)

    cart = get_cart()

    key = str(id)

    selling_price = product.price - (
        product.price * product.discount / 100
    )

    if key in cart:

        cart[key]["quantity"] += 1

    else:

        cart[key] = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "discount": product.discount,
            "selling_price": round(selling_price, 2),
            "image": product.image,
            "description": product.description,
            "quantity": 1
        }

    save_cart(cart)

    return redirect('/cart')

@app.route('/cart')
@login_required
def viewcart():

    cart = get_cart()

    for item in cart.values():

        item.setdefault("discount", 0)

        item.setdefault(
            "selling_price",
            item["price"]
        )

        item.setdefault(
            "description",
            ""
        )

        item.setdefault(
            "image",
            "default.png"
        )

    save_cart(cart)

    total = sum(
        item["selling_price"] *
        item["quantity"]
        for item in cart.values()
    )

    return render_template(
        "cart.html",
        cart_items=cart,
        total=round(total,2)
    )

@app.route('/increase/<int:id>')
@login_required
def increase(id):
    cart = get_cart()
    key = str(id)

    if key in cart:
        cart[key]["quantity"] += 1

    save_cart(cart)
    return redirect('/cart')


@app.route('/decrease/<int:id>')
@login_required
def decrease(id):
    cart = get_cart()
    key = str(id)

    if key in cart:
        cart[key]["quantity"] -= 1
        if cart[key]["quantity"] <= 0:
            del cart[key]

    save_cart(cart)
    return redirect('/cart')


@app.route('/remove/<int:id>')
@login_required
def remove(id):
    cart = get_cart()
    cart.pop(str(id), None)
    save_cart(cart)
    return redirect('/cart')

# ------------------------
# CHECKOUT (ONLY SUMMARY)
# ------------------------
@app.route('/checkout')
@login_required
def checkout():
    cart = get_cart()

    if not cart:
        return redirect('/cart')
    total = sum(
        item["selling_price"] * item["quantity"]
        for item in cart.values()
    )
    return render_template('checkout.html', total=total)
# ------------------------
# PAYMENT (FINAL ORDER CREATION)
# ------------------------
@app.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    cart = get_cart()

    if not cart:
        return redirect('/cart')

    total = 0

    for item in cart.values():

        selling_price = item["price"] - (item["price"] * item["discount"] / 100)

        total += selling_price * item["quantity"]

    if request.method == 'POST':

        method = request.form.get("payment_method")

        for item in cart.values():

            selling_price = item["price"] - (item["price"] * item["discount"] / 100)

            product = Product.query.get(item["id"])

            db.session.add(Order(
                user_id=session['user_id'],   
                username=session['username'],
                product_id=product.id,
                product_name=product.name,
                image=product.image,
                quantity=item["quantity"],
                price=selling_price,   # ✅ NOW VALID (after DB fix)
                payment_method=method,
                status="Paid" if method == "online" else "COD"
            ))

        db.session.commit()
        save_cart({})
        return redirect('/success')

    return render_template('payment.html', total=total)

from flask import url_for

@app.route("/update_status/<int:order_id>/<status>")
@login_required
def update_status(order_id, status):

    if session.get("role") != "provider":
        return redirect("/login")

    order = Order.query.get_or_404(order_id)

    order.status = status

    db.session.commit()

    flash("Order status updated successfully!", "success")

    return redirect(url_for("provider_orders"))
# ------------------------
# SUCCESS
# ------------------------
@app.route('/success')
@login_required
def success():
    return render_template('success.html')


# ------------------------
# ORDERS
# ------------------------
@app.route('/orders')
@login_required
def orders():

    orders = Order.query.filter_by(
        user_id=session["user_id"]
    ).all()

    for order in orders:

        product = Product.query.filter_by(
            name=order.product_name
        ).first()

        if product:
            order.product_image = product.image
        else:
            order.product_image = "default.png"

    return render_template(
        'orders.html',
        orders=orders
    )
@app.route('/add_review/<int:order_id>')
@login_required
def add_review(order_id):

    order = Order.query.get_or_404(order_id)

    product = Product.query.get(order.product_id)

    return render_template(
        'add_review.html',
        order=order,
        product=product
    )
@app.route("/my_reviews")
@login_required
def my_reviews():

    reviews = Review.query.filter_by(
        username=session['username']
    ).order_by(
        Review.created_at.desc()
    ).all()

    for review in reviews:

        product = Product.query.get(
            review.product_id
        )

        if product:
            review.product_name = product.name
            review.product_image = product.image
        else:
            review.product_name = "Product Deleted"
            review.product_image = None

    return render_template(
        "my_reviews.html",
        reviews=reviews
    )

@app.route('/return_order/<int:order_id>')
@login_required
def return_order(order_id):

    order = Order.query.get(order_id)

    if order and order.username == session['username']:

        if order.status == "Delivered":
            order.status = "Return Requested"
            db.session.commit()

    return redirect('/orders')

@app.route('/review/<int:order_id>', methods=['POST'])
@login_required
def review(order_id):

    order = Order.query.get_or_404(order_id)

    image = request.files.get('review_image')

    filename = None

    if image and image.filename:

        filename = secure_filename(image.filename)

        os.makedirs("static/reviews", exist_ok=True)

        image.save(
            os.path.join(
                "static/reviews",
                filename
            )
        )

    review = Review(
        product_id=order.product_id,
        username=session['username'],
        rating=int(request.form['rating']),
        comment=request.form['review'],
        image=filename
    )

    db.session.add(review)

    db.session.commit()

    return redirect('/orders')

@app.route('/profile')
@login_required
def profile():

    user = User.query.get(session['user_id'])

    total_orders = Order.query.filter_by(
        user_id=session['user_id']
    ).count()

    total_reviews = Review.query.filter_by(
        username=session['username']
    ).count()

    favorites_count = Favorite.query.filter_by(
        username=session['username']
    ).count()

    return render_template(
        'profile.html',
        user=user,
        total_orders=total_orders,
        total_reviews=total_reviews,
        favorites_count=favorites_count
    )
@app.route('/provider_profile')
@login_required
def provider_profile():

    if session.get('role') != "provider":
        return redirect('/login')

    user = User.query.filter_by(email=session['email']).first()

    provider_products = Product.query.filter_by(
        provider_email=session['email']
    ).all()

    product_ids = [p.id for p in provider_products]

    total_products = len(provider_products)

    total_orders = Order.query.filter(
        Order.product_id.in_(product_ids)
    ).count()

    return render_template(
        "provider_profile.html",
        user=user,
        total_products=total_products,
        total_orders=total_orders
    )

@app.route("/provider_orders")
@login_required
def provider_orders():

    if session.get("role") != "provider":
        return redirect("/login")

    products = Product.query.filter_by(
        provider_email=session["email"]
    ).all()

    product_ids = [p.id for p in products]

    orders = Order.query.filter(
        Order.product_id.in_(product_ids)
    ).order_by(Order.id.desc()).all()

    return render_template(
        "provider_orders.html",
        orders=orders
    )

@app.route('/analytics')
@login_required
def analytics():

    if session.get("role") != "provider":
        return redirect("/login")

    # STEP 1: get only THIS provider's products
    products = Product.query.filter_by(
        provider_email=session['email']
    ).all()

    product_ids = [p.id for p in products]

    # STEP 2: orders for THIS provider only
    orders = Order.query.filter(
        Order.product_id.in_(product_ids)
    ).all()

    total_products = len(products)
    total_orders = len(orders)

    total_sales = 0
    confirmed = shipped = delivered = returned = 0

    ratings = []

    for o in orders:

        if o.status == "Confirmed":
            confirmed += 1
        elif o.status == "Shipped":
            shipped += 1
        elif o.status == "Delivered":
            delivered += 1
        elif o.status == "Returned":
            returned += 1

        if o.status == "Delivered":
            total_sales += (o.price or 0) * o.quantity

        if o.rating:
            ratings.append(o.rating)

    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0

    recent_reviews = Review.query.filter(
        Review.product_id.in_(product_ids)
    ).order_by(
        Review.created_at.desc()
    ).limit(5).all()
    products = Product.query.filter_by(
        provider_email=session['email']
    ).all()

    product_ids = [p.id for p in products]

    orders = Order.query.filter(
        Order.product_id.in_(product_ids)
    ).order_by(Order.id.desc()).all()

    return render_template(
        "analytics.html",
        total_products=total_products,
        total_orders=total_orders,
        total_sales=round(total_sales, 2),
        avg_rating=avg_rating,
        recent_reviews=recent_reviews,
        confirmed_orders=confirmed,
        shipped_orders=shipped,
        delivered_orders=delivered,
        returned_orders=returned,
        top_products=[]
    )

@app.route("/reviews")
@login_required
def reviews():

    # Provider can only see reviews for their products
    if session.get("role") == "provider":

        provider_products = Product.query.filter_by(
            provider_email=session["email"]
        ).all()

        product_ids = [p.id for p in provider_products]

        reviews = Review.query.filter(
            Review.product_id.in_(product_ids)
        ).order_by(
            Review.created_at.desc()
        ).all()

    else:
        # User sees only their own reviews
        reviews = Review.query.filter_by(
            username=session["username"]
        ).order_by(
            Review.created_at.desc()
        ).all()

    return render_template(
        "reviews.html",
        reviews=reviews
    )
@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route('/buynow/<int:id>')
@login_required
def buynow(id):
    product = Product.query.get(id)

    if not product:
        return redirect('/products')

    # store single product in session
    session['buy_now'] = {
        "product_id": product.id,
        "quantity": 1
    }

    return redirect('/checkout_single')
@app.route('/checkout_single', methods=['GET'])
@login_required
def checkout_single():
    data = session.get('buy_now')

    if not data:
        return redirect('/products')

    product = Product.query.get(data["product_id"])
    selling_price = product.price - (product.price * product.discount / 100)
    total = selling_price * data["quantity"]

    return render_template(
        'checkout_single.html',
        product=product,
        total=total
    )
@app.route('/payment_single', methods=['POST'])
@login_required
def payment_single():

    data = session.get('buy_now')

    if not data:
        return redirect('/products')

    product = Product.query.get(data["product_id"])
    method = request.form.get("payment_method")

    # ✅ FIX: calculate selling price here
    selling_price = product.price - (product.price * product.discount / 100)

    status = "Placed (COD)" if method == "cod" else "Paid (Online)"

    db.session.add(Order(
        user_id=session['user_id'],   # IMPORTANT
        username=session['username'],
        product_id=product.id,
        product_name=product.name,
        image=product.image,
        quantity=data["quantity"],
        price=selling_price,
        payment_method=method,
        status=status
    ))

    db.session.commit()
    session.pop('buy_now', None)

    return redirect('/success')

# ------------------------
# LOGOUT
# ------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ------------------------
# HOME
# ------------------------
@app.route('/')
def home():
    return redirect('/register')

# =========================
# CART SYSTEM (SESSION)
# =========================

def get_cart():
    return session.get("cart", {})

def save_cart(cart):
    session["cart"] = cart
    session.modified = True
# ------------------------
# RUN
# ------------------------
if __name__ == '__main__':
    app.run(debug=True)