# app/firebase.py

import os
from dotenv import load_dotenv
load_dotenv()

import firebase_admin
from firebase_admin import credentials, auth, storage
from google.cloud import firestore
from google.oauth2.service_account import Credentials as GoogleCredentials

# 🔐 Load environment variables
private_key = os.environ.get("FIREBASE_PRIVATE_KEY")
project_id = os.environ.get("FIREBASE_PROJECT_ID")
client_email = os.environ.get("FIREBASE_CLIENT_EMAIL")
storage_bucket = os.environ.get("FIREBASE_STORAGE_BUCKET")

# 🔍 Validate required variables
required_vars = [private_key, project_id, client_email, storage_bucket]
if not all(required_vars):
    raise ValueError("Missing one or more required Firebase environment variables")

# 🧾 Shared credential dict
firebase_creds_dict = {
    "type": "service_account",
    "project_id": project_id,
    "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": private_key.replace("\\n", "\n"),
    "client_email": client_email,
    "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_CERT_URL")
}

# 🚀 Initialize Firebase Admin SDK
firebase_cred = credentials.Certificate(firebase_creds_dict)
if not firebase_admin._apps:
    firebase_admin.initialize_app(firebase_cred, {
        'storageBucket': storage_bucket
    })

# ✅ Initialize Firestore with Google-auth credentials
google_cred = GoogleCredentials.from_service_account_info(firebase_creds_dict)
db = firestore.Client(credentials=google_cred, project=project_id)

# ✅ Expose Firebase services
bucket = storage.bucket()
__all__ = ['db', 'auth', 'bucket']
