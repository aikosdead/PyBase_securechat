from dotenv import load_dotenv
load_dotenv()

import os, secrets, json
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, jsonify
from google.cloud import firestore
from werkzeug.utils import secure_filename
import requests
import cloudinary
import cloudinary.uploader

from app import firebase
from app.firebase import db, auth
from ..services.auth_service import verify_user, add_user

# 🔐 Cloudinary config
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

API_KEY = os.getenv("FIREBASE_WEB_API_KEY")
if not API_KEY:
    raise RuntimeError("Missing FIREBASE_WEB_API_KEY")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
db_client = db

# 🔐 CSRF utilities
def require_login():
    user_id = session.get('user_id')
    if not user_id:
        abort(403)
    return user_id

def get_or_create_csrf():
    token = session.get('csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['csrf_token'] = token
    return token

def verify_csrf():
    header = request.headers.get('X-CSRF-Token', '')
    token = session.get('csrf_token', '')
    if not token or header != token:
        abort(403, description="CSRF check failed")

# 🔐 Signup with public key
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html', csrf_token=get_or_create_csrf())

    email      = request.form.get('email')
    username   = request.form.get('username')
    password   = request.form.get('password')
    avatar     = request.files.get('avatar')
    public_key = request.form.get('public_key')

    if not (email and username and password and public_key):
        flash('Missing fields', 'error')
        return redirect(url_for('auth.signup'))

    try:
        user = auth.create_user(email=email, password=password)

        photo_url = ''
        if avatar and allowed_file(avatar.filename):
            safe_filename = secure_filename(avatar.filename)
            public_id = f"{user.uid}_{safe_filename.rsplit('.', 1)[0]}"
            upload_result = cloudinary.uploader.upload(
                avatar,
                folder="avatars",
                public_id=public_id,
                transformation={"width": 128, "height": 128, "crop": "fill"}
            )
            photo_url = upload_result.get("secure_url", "")

        profile_data = {
            'email': email,
            'username': username,
            'display_name': username,
            'photo_url': photo_url,
            'public_key': public_key,
            'public_key_format': 'curve25519_base64',
            'created_at': firestore.SERVER_TIMESTAMP
        }
        db.collection('profiles').document(user.uid).set(profile_data)

        try:
            link = firebase.auth.generate_email_verification_link(email)
            print("📧 EMAIL VERIFICATION LINK:", link)
        except Exception as link_error:
            print("⚠️ Email verification link error:", link_error)

        flash('Signup successful! Check your email for the verification link.', 'success')
        return redirect(url_for('auth.login'))

    except Exception as e:
        error = str(e)
        print("❌ Signup error:", error)
        return render_template('signup.html', error=error)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', csrf_token=get_or_create_csrf())

    email    = request.form.get('email')
    password = request.form.get('password')
    payload  = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    response = requests.post(url, json=payload)
    data = response.json()

    if "idToken" in data:
        id_token = data["idToken"]
        decoded = firebase.auth.verify_id_token(id_token, clock_skew_seconds=5)
        session['id_token'] = id_token
        session['user_id'] = decoded['uid']
        get_or_create_csrf()
        flash('Logged in successfully!', 'success')
        return redirect(url_for('inbox.inbox_view'))

    error_msg = data.get('error', {}).get('message', 'Unknown error')
    flash(f"Login failed: {error_msg}", 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile/<user_id>')
def profile(user_id):
    doc = db.collection('profiles').document(user_id).get()
    if not doc.exists:
        abort(404)
    profile = doc.to_dict()
    return render_template('profile.html', profile=profile)

@auth_bp.route('/chat/<other_id>', methods=['GET', 'POST'])
def chat(other_id):
    me_id = require_login()
    csrf_token = get_or_create_csrf()

    # 🔍 Get other user's profile
    other_doc = db.collection('profiles').document(other_id).get()
    if not other_doc.exists:
        abort(404)
    other = other_doc.to_dict()
    other['uid'] = other_doc.id
    other['username'] = other.get('display_name') or other.get('username') or 'Unknown'
    other['photo_url'] = other.get('photo_url', '')

    recipient_pub = other.get('public_key', '')
    recipient_format = other.get('public_key_format', '')

    # 🔐 Ensure conversation exists
    convo_id = '_'.join(sorted([me_id, other_id]))
    convo_ref = db.collection('conversations').document(convo_id)
    if not convo_ref.get().exists:
        convo_ref.set({
            'participants': [me_id, other_id],
            'created_at': firestore.SERVER_TIMESTAMP
        })

    msgs_ref = convo_ref.collection('messages')

    # 📨 Handle message send
    if request.method == 'POST':
        verify_csrf()
        try:
            data = request.get_json(force=True)
        except Exception:
            abort(400, description="Invalid JSON")

        required = ('ciphertext', 'nonce', 'sender_pub', 'scheme')
        if not all(k in data for k in required):
            abort(400, description="Missing fields")

        msg_doc = {
            'from': me_id,
            'to': other_id,
            'ciphertext': data['ciphertext'],
            'nonce': data['nonce'],
            'sender_pub': data['sender_pub'],
            'scheme': data.get('scheme', 'nacl-secretbox-x25519'),
            'created_at': firestore.SERVER_TIMESTAMP
        }
        msgs_ref.add(msg_doc)
        return jsonify({'status': 'ok'})

    # 📜 Serialize messages
    raw_messages = msgs_ref.order_by('created_at').stream()
    messages = []
    for doc in raw_messages:
        msg = doc.to_dict()
        msg['id'] = doc.id
        ts = msg.get('created_at')
        msg['timestamp'] = ts.strftime('%Y-%m-%dT%H:%M:%SZ') if ts else ''
        messages.append(msg)

    firebase_config = {
        "apiKey": os.getenv("FIREBASE_WEB_API_KEY"),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
        "projectId": os.getenv("FIREBASE_PROJECT_ID"),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
        "appId": os.getenv("FIREBASE_APP_ID")
    }

    return render_template(
        'chat.html',
        convo_id=convo_id,
        current_user_id=me_id,
        other_id=other_id,
        other_user=other,
        recipient_public_key=recipient_pub,
        recipient_public_key_format=recipient_format,
        csrf_token=csrf_token,
        messages=messages,
        firebase_config=firebase_config
    )