from flask import Blueprint, render_template, session, redirect, url_for, request
from app.firebase import firebase_auth, db  # Removed firebase_db
from firebase_admin import firestore  

inbox_bp = Blueprint('inbox', __name__)

@inbox_bp.route('/inbox', methods=['GET', 'POST'])
def inbox():
    id_token = session.get('id_token')
    if not id_token:
        return redirect(url_for('auth.login'))

    try:
        # 🔐 Verify user
        decoded_token = firebase_auth.verify_id_token(id_token)
        user_email = decoded_token.get('email', 'Anonymous')

        # 📝 Handle new message
        if request.method == 'POST':
            message = request.form.get('message')
            if message:
                db.collection('messages').add({
                    "sender": user_email,
                    "text": message,
                    "timestamp": firestore.SERVER_TIMESTAMP
                })

        # 📥 Fetch messages
        messages_ref = db.collection('messages').order_by('timestamp')
        messages_docs = messages_ref.stream()
        messages = [
            {
                "sender": doc.to_dict().get("sender", "Unknown"),
                "text": doc.to_dict().get("text", ""),
                "timestamp": doc.to_dict().get("timestamp")
            }
            for doc in messages_docs
        ]

        return render_template('inbox.html', messages=messages, user_email=user_email)

    except Exception as e:
        print(f"Token verification failed: {e}")
        return redirect(url_for('auth.login'))
