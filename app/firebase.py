from dotenv import load_dotenv
load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore, auth
import os

# Load environment variables
private_key = os.environ.get("FIREBASE_PRIVATE_KEY")
project_id = os.environ.get("FIREBASE_PROJECT_ID")
client_email = os.environ.get("FIREBASE_CLIENT_EMAIL")

# Validate required variables
if not private_key or not project_id or not client_email:
    raise ValueError("Missing one or more required Firebase environment variables")

# Create credentials object
cred = credentials.Certificate({
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
})


# Initialize Firebase
firebase_admin.initialize_app(cred)

# Set up Firestore and Auth
db = firestore.client()
firebase_auth = auth
