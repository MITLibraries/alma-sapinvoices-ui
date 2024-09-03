from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flask import (
    Flask,
    Request,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_required,
    logout_user,
)

if TYPE_CHECKING:
    from werkzeug.wrappers.response import Response

from webapp.config import Config
from webapp.exceptions import ECSTaskLogStreamDoesNotExistError
from webapp.utils import get_task_status_and_logs, log_activity, parse_oidc_data
from webapp.utils.aws import ECSClient

logger = logging.getLogger(__name__)

CONFIG = Config()


class User(UserMixin):
    """Class representing users of the app.

    This class stores credentials (MIT ID, name, and email)
    about logged in users.
    """

    def __init__(self, mit_id: str, name: str, email: str | None = None) -> None:
        self.mit_id = mit_id
        self.name = name
        self.email = email

    def get_id(self) -> str:
        return str(self.mit_id)

    @classmethod
    def from_session_data(cls) -> User | None:
        oidc_data = session.get("oidc_data")
        if oidc_data is None:
            return None
        return cls(
            mit_id=oidc_data["mit_id"],
            name=oidc_data["name"],
            email=oidc_data["preferred_username"],
        )


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(LOGIN_DISABLED=CONFIG.LOGIN_DISABLED, SECRET_KEY=CONFIG.SECRET_KEY)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.request_loader
    def load_user_from_request(request: Request) -> User | None:
        """Callback to login users using data from request headers.

        For this application, login is the process of identifying the user
        by decoding data provided in the request headers. This method
        will:

        * Retrieve OpenID Connect (OIDC) access tokens and user data from request headers.
           * If access tokens or user data are missing from the request headers,
             user cannot login.
        * Stores active access tokens and user data in the Flask session.
        * Create or refresh a User instance with parsed user data from OIDC.

        An expired access token is marked by a mismatch between the OIDC
        access token retrieved from the request header and the access token
        currently stored in the Flask session. If there is a mismatch,
        the method will parse the updated OIDC data in the request header
        and refresh the User instance with the updated user data.
        """
        oidc_access_token = request.headers.get("x-amzn-oidc-accesstoken")
        oidc_jwt_data = request.headers.get("x-amzn-oidc-data")

        if oidc_access_token is None:
            logger.error(
                "Access token ('x-amzn-oidc-accesstoken') is missing "
                "from the request headers."
            )
            return None

        if oidc_jwt_data is None:
            logger.error(
                "User data ('x-amzn-oidc-data') is missing from the request headers."
            )
            return None

        # get user data if new session or refresh user data when access token expires
        if oidc_access_token != session.get("oidc_access_token"):
            oidc_data = parse_oidc_data(oidc_jwt_data, options={"verify_exp": False})
            session.update(
                {"oidc_access_token": oidc_access_token, "oidc_data": oidc_data}
            )
        return User.from_session_data()

    @app.route("/")
    @login_required
    def index() -> str:
        return render_template("index.html")

    @app.route("/process-invoices")
    @login_required
    def process_invoices() -> str:
        return render_template("process_invoices.html")

    @app.route("/process-invoices/run/<run_type>")
    @login_required
    def process_invoices_run(run_type: str) -> str | Response:
        if run_type == "review":
            # [TODO] Add error page for invalid run types.
            return redirect(url_for("process_invoices_run_execute", run_type=run_type))
        elif run_type == "final":  # noqa: RET505
            return redirect(url_for("process_invoices_confirm_final_run"))
        return abort(400, description=f"Invalid run type: '{run_type}'")

    @app.route("/process-invoices/run/final/confirm")
    @login_required
    def process_invoices_confirm_final_run() -> str:
        return render_template("process_invoices_confirm_final_run.html")

    @app.route("/process-invoices/run/<run_type>/execute")
    @login_required
    def process_invoices_run_execute(run_type: str) -> str | Response:
        ecs_client = ECSClient()
        if active_tasks := ecs_client.get_active_tasks():
            return render_template(
                "errors/error_400_cannot_run_multiple_tasks.html",
                active_tasks=active_tasks,
            )

        if run_type == "review":
            task_arn = ecs_client.execute_review_run()
        elif run_type == "final":
            if request.referrer and request.referrer.endswith(
                "process-invoices/run/final/confirm"
            ):
                task_arn = ecs_client.execute_final_run()
            else:
                return abort(
                    400, description="Unable to confirm execution of 'final' run."
                )
        else:
            return abort(400, description=f"Invalid run type: '{run_type}'")
        task_id = task_arn.split("/")[-1]  # type: ignore[union-attr]
        log_activity(f"executed a '{run_type}' run (task ID = '{task_id}').")
        return redirect(url_for("process_invoices_status", task_id=task_id))

    @app.route("/process-invoices/status/<task_id>")
    @login_required
    def process_invoices_status(task_id: str) -> str:
        log_activity(f"checked the status for task '{task_id}'.")
        try:
            _, logs = get_task_status_and_logs(task_id)
        except ECSTaskLogStreamDoesNotExistError as exception:
            return render_template(
                "errors/error_404_object_not_found.html", error=exception
            )

        return render_template(
            "process_invoices_status.html",
            logs=logs,
            task_id=task_id,
        )

    @app.route("/process-invoices/status/<task_id>/data")
    @login_required
    def process_invoices_status_data(task_id: str) -> Response:
        try:
            task_status, logs = get_task_status_and_logs(task_id)
        except ECSTaskLogStreamDoesNotExistError:
            task_status = "UNKNOWN"
            logs = ["Log stream does not exist."]

        return jsonify({"status": task_status, "logs": logs})

    @app.route("/logout")
    @login_required
    def logout() -> str:
        """Removes parsed OIDC data and user ID from the Flask session.

        When Flask-Login's logout_user command is invoked, the logged in
        user's ID is removed from the Flask session and logged in
        user for the request context is reset to an AnonymousUserMixin
        instance.

        Note: This doesn't log the user out of ALB or Touchstone.
        """
        log_activity("logged out.")
        # clear parsed OIDC data from the session
        session.pop("oidc_access_token", None)
        session.pop("user", None)

        # Flask-Login's command for logging out a user
        logout_user()

        return render_template("logout.html")

    return app
