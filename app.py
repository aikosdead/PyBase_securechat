# app.py (in root folder)

from flask import Flask
from app.routes.auth import auth_bp
import firebase_admin
from firebase_admin import credentials
import os

cred = credentials.Certificate({
    "type": "service_account",
    "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
    "private_key": os.environ.get("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.environ.get("firebase-adminsdk-fbsvc@chat-52691.iam.gserviceaccount.com"),
    "token_uri": "https://oauth2.googleapis.com/token"
})

firebase_admin.initialize_app(cred)

app = Flask(__name__)
app.register_blueprint(auth_bp)

@app.route('/')
def home():
    return "Welcome to SecureChat!"

if __name__ == '__main__':
    app.run(debug=True)
