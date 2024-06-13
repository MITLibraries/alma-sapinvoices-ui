from flask import Flask

from . import views


def create_app():
    app = Flask(__name__)
    app.config.from_prefixed_env()
    app.register_blueprint(views.bp)
    return app
