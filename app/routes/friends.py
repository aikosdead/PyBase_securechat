from flask import Blueprint, request, session, redirect, url_for, abort
from google.cloud import firestore

db = firestore.Client()
friends_bp = Blueprint('friends', __name__)

@friends_bp.route('/add_friend/<username>', methods=['POST'])
def add_friend(username):
    current_user = session.get('username')
    if not current_user:
        abort(403)

    db.collection('friendships').add({
        'from': current_user,
        'to': username,
        'timestamp': firestore.SERVER_TIMESTAMP
    })

    return redirect(url_for('profiles', username=username))
