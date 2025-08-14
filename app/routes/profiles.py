from flask import Blueprint, render_template, abort
from firebase_admin import firestore

db = firestore.client()
profiles_bp = Blueprint('profiles', __name__)  # 👈 Blueprint name is 'profiles'

@profiles_bp.route('/<username>')  # 👈 Clean route: /profile/<username>
def profile(username):
    user_ref = db.collection('users').where('username', '==', username).limit(1).get()
    if not user_ref:
        abort(404)

    user_data = user_ref[0].to_dict()
    return render_template('profiles.html', user=user_data)  # 👈 Correct template name
