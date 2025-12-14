from flask import Blueprint, render_template, redirect, url_for, flash, request
from models import Product, CartItem, Order, OrderItem
from database import db
from flask_login import current_user, login_required
from forms import AddToCartForm, CheckoutForm
from flask import jsonify
from chatbot_integration.chatbot_service import get_chatbot_response

print(">>> SHOP.PY LOADED <<<")

shop_bp = Blueprint('shop', __name__, template_folder='../templates')

def get_products_from_db():
    """
    Fetches all products from the database and formats them into a simple string for the LLM.
    """
    try:
        products = Product.query.all()
        if not products:
            return "There are currently no products available in the shop."
        
        product_list_str = "Here is a list of available products:\n"
        for p in products:
            product_list_str += f"- Name: {p.name}, Price: ${p.price:.2f}, Stock: {p.stock}\n"
        
        return product_list_str
    except Exception as e:
        print(f"Error fetching products from DB: {e}")
        return "I was unable to access the product catalog."

@shop_bp.route('/')
def product_list():
    products = Product.query.all()
    return render_template('shop/product_list.html', title='Shop', products=products)

@shop_bp.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    form = AddToCartForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('You need to log in to add items to your cart.', 'info')
            return redirect(url_for('auth.login', next=request.url))

        quantity = form.quantity.data
        if quantity <= 0:
            flash('Quantity must be at least 1.', 'danger')
            return redirect(url_for('shop.product_detail', product_id=product.id))

        if product.stock < quantity:
            flash(f'Insufficient stock. Only {product.stock} left.', 'danger')
            return redirect(url_for('shop.product_detail', product_id=product.id))

        cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(user_id=current_user.id, product_id=product.id, quantity=quantity)
        
        db.session.add(cart_item)
        db.session.commit()
        flash(f'{quantity} x {product.name} added to your cart!', 'success')
        return redirect(url_for('shop.cart'))
    
    return render_template('shop/product_detail.html', title=product.name, product=product, form=form)

@shop_bp.route('/cart')
@login_required
def cart():
    cart_items = current_user.cart_items.all()
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', title='Your Cart', cart_items=cart_items, total_price=total_price)

@shop_bp.route('/cart/remove/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        flash('You are not authorized to remove this item.', 'danger')
        return redirect(url_for('shop.cart'))
    
    db.session.delete(cart_item)
    db.session.commit()
    flash('Item removed from cart.', 'success')
    return redirect(url_for('shop.cart'))

@shop_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = current_user.cart_items.all()
    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('shop.product_list'))

    total_amount = sum(item.product.price * item.quantity for item in cart_items)
    checkout_form = CheckoutForm()

    if checkout_form.validate_on_submit():
        new_order = Order(user_id=current_user.id, total_amount=total_amount, status='Processing')
        db.session.add(new_order)
        db.session.flush()

        for item in cart_items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price
            )
            product = Product.query.get(item.product_id)
            if product.stock < item.quantity:
                db.session.rollback()
                flash(f'Not enough stock for {product.name}. Please adjust your cart.', 'danger')
                return redirect(url_for('shop.cart'))
            product.stock -= item.quantity
            db.session.add(order_item)
            db.session.delete(item)
        
        db.session.commit()
        flash('Your order has been placed successfully!', 'success')
        return redirect(url_for('shop.purchase_history'))
    
    return render_template('checkout.html', title='Checkout', cart_items=cart_items, total_amount=total_amount, form=checkout_form)

@shop_bp.route('/purchase_history')
@login_required
def purchase_history():
    orders = current_user.orders.order_by(Order.order_date.desc()).all()
    return render_template('purchase_history.html', title='Purchase History', orders=orders)

@shop_bp.route('/chatbot', methods=['POST'])
def chatbot():
    print(">>> CHATBOT ENDPOINT HIT <<<")
    data = request.get_json()

    user_message = data.get('message', '')
    history = data.get('history', [])

    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    # ✅ IEGŪSTAM PRODUKTUS NO DATUBĀZES
    products = Product.query.all()
    formatted_products = []
    for p in products:
        formatted_products.append({
            "name": p.name,
            "price": p.price
        })
    
    print(f">>> Sending to chatbot: '{user_message[:50]}...' with {len(products)} products")

    # ✅ PADODAM PRODUKTUS FUNKCIJAI
    reply = get_chatbot_response(user_message, history, formatted_products)

    return jsonify({'reply': reply})