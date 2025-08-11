from werkzeug.security import check_password_hash

# Temporary user store
users = {}

def verify_user(username, password):
    if username in users:
        return check_password_hash(users[username], password)
    return False

def add_user(username, hashed_password):
    if username in users:
        return False  # Username already exists
    users[username] = hashed_password
    return True
