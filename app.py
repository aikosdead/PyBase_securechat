from dotenv import load_dotenv
load_dotenv()
import os

import cloudinary
import cloudinary.uploader

cloudinary.config(
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
  api_key = os.getenv("CLOUDINARY_API_KEY"),
  api_secret = os.getenv("CLOUDINARY_API_SECRET")
)

from flask import Flask

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

# ✅ Firebase is initialized inside app/firebase.py
from app import firebase

# ✅ Import blueprints
from app.routes.auth import auth_bp, inbox_bp

# ✅ Register routes
app.register_blueprint(auth_bp)
app.register_blueprint(inbox_bp)

@app.route('/')
def home():
    return "Welcome to SecureChat!"

if __name__ == '__main__':
    app.run(debug=True)
