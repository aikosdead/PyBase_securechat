from flask import Flask, render_template
from app.routes.auth import auth_bp
from app.routes.inbox import inbox_bp
from app import firebase  # Firebase setup (db, auth)
import os

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "fallback_key")

    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(inbox_bp)  # ← This was missing

    # Optional: Home route
    @app.route("/")
    def home():
        return render_template("home.html")

    return app
