from flask import Flask

from app.config import Config
from app.routes.auth import bp as auth_bp


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    app.register_blueprint(auth_bp)

    return app
