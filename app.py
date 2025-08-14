# app/app.py
from dotenv import load_dotenv
load_dotenv()
import os

import cloudinary
import cloudinary.uploader

from flask import Flask
from flask_cors import CORS

# 🔧 Cloudinary config
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

    # 🔐 CORS: allow only trusted frontend origins
    CORS(
        app,
        resources={r"/auth/*": {"origins": [
            "https://your-frontend.example.com",
            "http://localhost:3000"
        ]}},
        supports_credentials=True
    )

    # ✅ Firebase init
    from app import firebase

    # ✅ Register blueprints
    from app.routes.auth import auth_bp, inbox_bp
    from app.routes.profiles import profiles_bp
    from app.routes.friends import friends_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(inbox_bp)
    app.register_blueprint(profiles_bp, url_prefix='/profile')
    app.register_blueprint(friends_bp)

    @app.route('/')
    def home():
        return "Welcome to SecureChat!"

    return app

# 🏁 Local run
app = create_app()

if __name__ == '__main__':
    app.run(debug=False)
