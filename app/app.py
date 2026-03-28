from flask import Flask
from app.routes.auth import auth_bp
from app.routes.profile import profile_bp
from app.routes.toggle import toggle_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = "supersecretkey"

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(toggle_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)