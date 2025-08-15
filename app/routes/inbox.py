from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.firebase import auth, db
from firebase_admin import firestore
from datetime import datetime
import pytz

inbox_bp = Blueprint('inbox', __name__)

def format_timestamp(ts, tz='Asia/Manila'):
    try:
        local_tz = pytz.timezone(tz)
        local_dt = ts.astimezone(local_tz)
        return local_dt.strftime('%b %d, %I:%M %p')  # e.g., Aug 14, 11:42 PM
    except Exception as e:
        print('Timestamp formatting failed:', ts, e)
        return 'Invalid time'

@inbox_bp.route('/inbox', methods=['GET', 'POST'])
def inbox_view():
    try:
        me_id = session.get('user_id')
        if not me_id:
            raise Exception("Missing user_id in session")

        result = None
        query = None

        # 🔍 Handle search
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

        # 📥 Build inbox previews
        conversations = []
        convos_ref = db.collection('conversations').where('participants', 'array_contains', me_id)
        convo_docs = convos_ref.stream()

        for convo in convo_docs:
            data = convo.to_dict()
            participants = data.get('participants', [])
            other_id = next((uid for uid in participants if uid != me_id), None)
            if not other_id:
                continue

            # 🔍 Get other user's profile
            profile_doc = db.collection('profiles').document(other_id).get()
            profile = profile_doc.to_dict() if profile_doc.exists else {}
            other_username = profile.get('display_name') or profile.get('username') or 'Unknown'

            # 🔐 Get last message
            convo_id = '_'.join(sorted([me_id, other_id]))
            messages_ref = db.collection('conversations').document(convo_id).collection('messages') \
                             .order_by('created_at', direction=firestore.Query.DESCENDING).limit(1)
            last_msg_docs = messages_ref.stream()
            last_msg = next(last_msg_docs, None)

            preview = '[Redacted]'
            timestamp = None
            timestamp_str = ''
            if last_msg:
                msg_data = last_msg.to_dict()
                timestamp = msg_data.get('created_at')
                if timestamp:
                    timestamp_str = format_timestamp(timestamp)

            conversations.append({
                'other_id': other_id,
                'other_username': other_username,
                'preview': preview,
                'timestamp': timestamp,
                'timestamp_str': timestamp_str,
                'photo_url': profile.get('photo_url', '')
            })

        # 🗂️ Sort conversations by timestamp (most recent first)
        conversations.sort(key=lambda x: x['timestamp'], reverse=True)

        return render_template('inbox.html',
                               result=result,
                               query=query,
                               conversations=conversations)

    except Exception as e:
        flash("Session expired or invalid. Please log in again.")
        print(f"Inbox route error: {e}")
        return redirect(url_for('auth.login'))
