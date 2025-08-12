from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.firebase import firebase_auth, db
from firebase_admin import firestore
from datetime import datetime

inbox_bp = Blueprint('inbox', __name__)

@inbox_bp.route('/inbox', methods=['GET', 'POST'])
def inbox_view():
    try:
        me_id = session.get('user_id')
        if not me_id:
            raise Exception("Missing user_id in session")

        result = None
        query = None

        if request.method == 'POST':
            query = request.form.get('username', '').strip().lower()
            profiles_ref = db.collection('profiles')
            results = profiles_ref.where('username', '==', query).stream()

            for doc in results:
                if doc.id != me_id:
                    data = doc.to_dict()
                    result = {
                        'uid': doc.id,
                        'username': data.get('username'),
                        'photo_url': data.get('photo_url', '')
                    }
                    break

        conversations = []
        convos_ref = db.collection('conversations').where('participants', 'array_contains', me_id)
        convo_docs = convos_ref.stream()

        for convo in convo_docs:
            data = convo.to_dict()
            participants = data.get('participants', [])
            other_id = [uid for uid in participants if uid != me_id][0]

            profile_doc = db.collection('profiles').document(other_id).get()
            profile = profile_doc.to_dict() if profile_doc.exists else {'username': 'Unknown'}

            convo_id = '_'.join(sorted([me_id, other_id]))
            messages_ref = db.collection('conversations').document(convo_id).collection('messages').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1)
            last_msg_docs = messages_ref.stream()
            last_msg = next(last_msg_docs, None)

            preview = ''
            timestamp_str = ''
            if last_msg:
                msg_data = last_msg.to_dict()
                preview = msg_data.get('text', '')
                timestamp = msg_data.get('timestamp')
                if timestamp:
                    # Convert Firestore timestamp to readable format
                    timestamp_str = timestamp.strftime('%I:%M %p')  # e.g., 11:42 PM


            conversations.append({
                'other_id': other_id,
                'other_username': profile.get('username', 'Unknown'),
                'preview': preview,
                'timestamp': timestamp_str
            })

        return render_template('inbox.html',
                               result=result,
                               query=query,
                               conversations=conversations)

    except Exception as e:
        flash("Session expired or invalid. Please log in again.")
        print(f"Inbox route error: {e}")
        return redirect(url_for('auth.login'))


