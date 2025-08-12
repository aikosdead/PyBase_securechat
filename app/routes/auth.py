from dotenv import load_dotenv
load_dotenv()  # ← reads .env into os.environ
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session 
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from app.services.auth_service import verify_user, add_user
from app import firebase  # Firebase setup (db, auth)
from firebase_admin import auth as firebase_auth
from google.cloud import firestore  # For SERVER_TIMESTAMP
from app.firebase import db, auth

API_KEY = os.getenv("FIREBASE_WEB_API_KEY")
if not API_KEY:
    raise RuntimeError("Missing FIREBASE_WEB_API_KEY environment variable")

firebase_auth = firebase.auth

inbox_bp = Blueprint('inbox', __name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# 📬 Inbox route
@inbox_bp.route('/inbox')
def inbox():
    id_token = session.get('id_token')
    if not id_token:
        flash("Please log in to access your inbox.")
        return redirect(url_for('auth.login'))
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        user_id = decoded_token['uid']
        return render_template('inbox.html', user_id=user_id)
    except Exception as e:
        flash("Session expired or invalid. Please log in again.")
        print(f"Token verification failed: {e}")
        return redirect(url_for('auth.login'))

# 🔐 Login route
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        api_key = API_KEY
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        response = requests.post(url, json=payload)
        data = response.json()

        if "idToken" in data:
            session['id_token'] = data['idToken']
            flash('Logged in successfully!')
            return redirect(url_for('inbox.inbox'))  # ✅ This now matches your route
        else:
            error_msg = data.get('error', {}).get('message', 'Unknown error')
            flash(f"Login failed: {error_msg}")
            print(f"Login error: {error_msg}")

    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            user = auth.create_user(email=email, password=password)
            db.collection('users').document(user.uid).set({
                'email': email,
                'username': username,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            flash('Signup successful!', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            error = str(e)
            return render_template('signup.html', error=error)

    return render_template('signup.html')


@auth_bp.route('/logout')
def logout():
    session.pop('id_token', None)
    flash('Logged out successfully!')
    return redirect(url_for('auth.login'))

