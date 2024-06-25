from flask import Flask

from webapp.config import Config


def create_app(config: Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)

    @app.route("/")
    def hello_world() -> str:
        return f"Hello, World! WORKSPACE={app.config['WORKSPACE']}"

    @app.route("/about")
    def about() -> str:
        return "This is the About page!"

    return app
