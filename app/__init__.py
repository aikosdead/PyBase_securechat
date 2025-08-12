from flask import Flask, render_template
from app.routes.auth import auth_bp
from app.routes.inbox import inbox_bp
from app import firebase  # Firebase setup (db, auth)
import os

def create_app():
    app = Flask(__name__)
    
    # 🔐 Secret key for sessions
    app.secret_key = os.getenv("SECRET_KEY", "fallback_key")

    # ⚙️ Session config
    app.config.update({
        'SESSION_COOKIE_SAMESITE': 'Lax',
        'SESSION_COOKIE_SECURE': False,
        'SESSION_COOKIE_HTTPONLY': True,
        'PERMANENT_SESSION_LIFETIME': 3600  # 1 hour
    })

    # 📦 Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(inbox_bp)

    # 🏠 Optional: Home route
    @app.route("/")
    def home():
        return render_template("home.html")

    return app

# 👇 This line makes Flask CLI and IDEs recognize the app instance
app = create_app()
