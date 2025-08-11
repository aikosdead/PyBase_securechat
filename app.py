# app.py (in root folder)

from flask import Flask
from app.routes.auth import auth_bp

app = Flask(__name__)
app.register_blueprint(auth_bp)

@app.route('/')
def home():
    return "Welcome to SecureChat!"

if __name__ == '__main__':
    app.run(debug=True)
