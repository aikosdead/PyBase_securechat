from dotenv import load_dotenv
load_dotenv()  # ← reads .env into os.environ
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session , abort
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from ..services.auth_service import verify_user, add_user
from app import firebase  # Firebase setup (db, auth)
from firebase_admin import auth as firebase_admin_auth
from google.cloud import firestore  # For SERVER_TIMESTAMP
from app.firebase import db, auth


API_KEY = os.getenv("FIREBASE_WEB_API_KEY")
if not API_KEY:
    raise RuntimeError("Missing FIREBASE_WEB_API_KEY environment variable")

firebase_auth = firebase.auth

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
chat_bp = Blueprint('chat', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')
        payload  = {
            "email":             email,
            "password":          password,
            "returnSecureToken": True
        }

        # 1) Call Firebase REST API to sign in
        url      = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
        response = requests.post(url, json=payload)
        data     = response.json()

        if "idToken" in data:
            id_token = data["idToken"]

            # 2) Verify token & check email verification
            decoded = firebase_auth.verify_id_token(id_token)
            ###if not decoded.get("email_verified", False):
                ###flash("Please verify your email before logging in.", "warning")
                ###return redirect(url_for('auth.login'))

            # 3) Persist token + uid in session
            session['id_token'] = id_token
            session['user_id']  = decoded['uid']
            print("SESSION AFTER LOGIN:", dict(session))
            flash('Logged in successfully!', 'success')
            return redirect(url_for('inbox.inbox_view'))

        # Sign-in failed: show error
        error_msg = data.get('error', {}).get('message', 'Unknown error')
        flash(f"Login failed: {error_msg}", 'danger')
        print(f"Login error: {error_msg}")

    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email    = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            # 1) Create the user in Firebase Auth
            user = auth.create_user(email=email, password=password)

            # 2) Save a profile document
            profile_data = {
                'email':        email,
                'username':     username,
                'display_name': username,
                'photo_url':    '',
                'created_at':   firestore.SERVER_TIMESTAMP
            }
            db.collection('profiles').document(user.uid).set(profile_data)

            # 3) Generate a verification link
            link = firebase_auth.generate_email_verification_link(email)
            # For now, we’ll just print it — in real life you’d email this to the user
            print("EMAIL VERIFICATION LINK:", link)

            flash('Signup successful! Check your email for the verification link.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            # e.g. “email already in use”
            error = str(e)
            return render_template('signup.html', error=error)

    return render_template('signup.html')

@auth_bp.route('/logout')
def logout():
    session.pop('id_token', None)
    session.pop('user_id', None)
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
    me_id = session.get('user_id')
    convo_id = '_'.join(sorted([me_id, other_id]))
    convo_ref = db.collection('conversations').document(convo_id)
    msgs_ref = convo_ref.collection('messages')

    if request.method == 'POST':
        text = request.form['text']

        # ✅ Ensure conversation document exists
        convo_ref.set({
            'participants': [me_id, other_id],
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)

        # ✅ Add message
        msgs_ref.add({
            'sender':    me_id,
            'text':      text,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

        return redirect(url_for('auth.chat', other_id=other_id))

    # Fetch messages
    messages = [
        m.to_dict()
        for m in msgs_ref.order_by('timestamp').stream()
    ]

    # Fetch other user's profile
    profile_doc = db.collection('profiles').document(other_id).get()
    other_user = profile_doc.to_dict() if profile_doc.exists else {'display_name': 'Unknown'}

    return render_template('chat.html',
                           messages=messages,
                           other_id=other_id,
                           other_user=other_user)


@auth_bp.route('/test-session')
def test_session():
    session_data = dict(session)
    print("SESSION DATA:", session_data)
    return f"Session contents: {session_data}"

