import firebase_admin
from firebase_admin import credentials, auth, db

# Initialize Firebase Admin SDK
cred = credentials.Certificate("app/firebase/serviceAccountKey.json")  # Replace with your actual path
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://chat-52691.firebaseapp.com'  # Replace with your actual database URL
})

# Expose auth and db
firebase_auth = auth
firebase_db = db
