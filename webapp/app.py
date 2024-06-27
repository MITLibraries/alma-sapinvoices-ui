from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def hello_world() -> str:
        return "Hello, World!"

    @app.route("/about")
    def about() -> str:
        return "This is the About page!"

    return app
