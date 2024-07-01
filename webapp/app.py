from flask import Flask

from webapp.config import Config

CONFIG = Config()


def create_app() -> Flask:
    app = Flask(__name__)
    CONFIG.check_required_env_vars()
    app.config.from_object(CONFIG)

    @app.route("/")
    def hello_world() -> str:
        return f"Hello, World! WORKSPACE={app.config['WORKSPACE']}"

    @app.route("/about")
    def about() -> str:
        return "This is the About page!"

    return app
