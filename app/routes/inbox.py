from flask import Blueprint, render_template, session, redirect, url_for, request
from app.firebase import firebase_auth, firebase_db

inbox_bp = Blueprint('inbox', __name__)

@inbox_bp.route('/inbox', methods=['GET', 'POST'])
def inbox():
    id_token = session.get('id_token')
    if not id_token:
        return redirect(url_for('auth.login'))

    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        user_email = decoded_token.get('email', 'Anonymous')

        ref = firebase_db.reference('messages')

        if request.method == 'POST':
            message = request.form.get('message')
            if message:
                ref.push({
                    "sender": user_email,
                    "text": message
                })

        messages_snapshot = ref.get()
        messages = list(messages_snapshot.values()) if messages_snapshot else []

        return render_template('inbox.html', messages=messages, user_email=user_email)

    except Exception as e:
        print(f"Token verification failed: {e}")
        return redirect(url_for('auth.login'))
