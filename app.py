from flask import Flask, render_template, flash, redirect, url_for
from config import Config
from database import db
from models import User
from flask_login import LoginManager, current_user
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(id):
        return db.session.get(User, int(id))

    # Register blueprints
    from routes.auth import auth_bp
    from routes.shop import shop_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shop_bp, url_prefix='/shop')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.route('/')
    @app.route('/index')
    def index():
        return render_template('index.html', title='Home')

    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)