from flask import Flask
from app.routes.auth import auth_bp
from app.routes.profile import profile_bp
from app.routes.toggle import toggle_bp
from app.routes.system import system_bp
from app.routes.upload import upload_bp
from app.routes.csrf import csrf_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = "supersecretkey"

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(toggle_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(csrf_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)