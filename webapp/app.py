from flask import Flask, jsonify, redirect, render_template, url_for

from webapp.exceptions import ECSTaskLogStreamDoesNotExistError
from webapp.utils import get_task_status_and_logs
from webapp.utils.aws import ECSClient


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index() -> str:
        return render_template("index.html")

    @app.route("/process-invoices")
    def process_invoices() -> str:
        return render_template("process_invoices.html")

    @app.route("/process-invoices/run/<run_type>")
    def process_invoices_run(run_type):
        ecs_client = ECSClient()
        if active_tasks := ecs_client.get_active_tasks():
            return render_template(
                "errors/error_400_cannot_run_multiple_tasks.html",
                active_tasks=active_tasks,
            )
        if run_type == "review":
            task_arn = ecs_client.execute_review_run()
        elif run_type == "final":
            task_arn = ecs_client.execute_final_run()
        task_id = task_arn.split("/")[-1]
        return redirect(url_for("process_invoices_status", task_id=task_id))

    @app.route("/process-invoices/status/<task_id>")
    def process_invoices_status(task_id):
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
    def process_invoices_status_data(task_id):
        try:
            task_status, logs = get_task_status_and_logs(task_id)
        except ECSTaskLogStreamDoesNotExistError:
            task_status = "UNKNOWN"
            logs = ["Log stream does not exist."]

        return jsonify({"status": task_status, "logs": logs})

    return app
