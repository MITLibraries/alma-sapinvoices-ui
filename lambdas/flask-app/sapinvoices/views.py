"""sapinvoices.views.py

Views for Alma SAP Invoices GUI.

This module contains definitions for the routes (or pages)
that can be accessed via the GUI.
"""

from datetime import datetime, UTC

from flask import Blueprint, render_template, session

from sapinvoices.config import Config
from sapinvoices.utils import CloudWatchClient, ECSClient
from sapinvoices.utils.helpers import get_task_id_from_arn

CONFIG = Config()
bp = Blueprint("views", __name__)


@bp.route("/")
def home():
    # [TODO]: Need to find a way to track executed tasks in session but also clear
    # session when appropriate. With the current code, the "tasks" variable will always
    # be reset to an empty list when user returns to home page.
    session["tasks"] = []
    return render_template("views/home.html")


@bp.route("/process-invoices")
def process_invoices():
    return render_template("views/process_invoices.html")


@bp.route("/process-invoices/review-run")
def process_invoices_review_run():
    ecs_client = ECSClient(
        cluster=CONFIG.ALMA_SAPINVOICES_ECS_CLUSTER_ARN,
        network_configuration=CONFIG.ALMA_SAPINVOICES_VPC_CONFIG,
    )

    # get start time of invoice processing
    # [TODO] TIMEZONES?!
    review_run_start_time = datetime.now()
    review_run_start_time_readable = review_run_start_time.strftime(
        "%Y-%m-%d %H:%M:%S.%f %Z"
    )
    review_run_start_time_epoch = int(review_run_start_time.strftime("%s"))

    # [TODO] Uncomment when ready for testing ECS task runs!
    response = ecs_client.run_task(
        taskDefinition=CONFIG.ALMA_SAPINVOICES_ECS_TASK_ARN,
        overrides={
            "containerOverrides": [
                {
                    "name": "carbon-ecs-stage",
                    "command": ["--run_connection_tests", "--ignore_sns_logging"],
                }
            ]
        },
    )

    container_details = response["tasks"][0]["containers"][0]

    # track ARN for task run in session
    task_arn = container_details["taskArn"]
    session["tasks"].append(
        {
            "task_arn": task_arn,
            "task_id": get_task_id_from_arn(task_arn),
            "run_type": "Review",
            "start_time": review_run_start_time_epoch,
        }
    )
    session.modified = True
    # session["tasks"].append({"task_arn": "ARN", "run_type": "Review"})

    return render_template(
        "views/process_invoices.html",
        review_run_output=f"Running {container_details['name']} task: {container_details["taskArn"]}",
        # review_run_output=f"Running task: {session["task_arn"]}",
    )


@bp.route("/process-invoices/review-run/check-task-status")
def check_status_review_run():
    ecs_client = ECSClient(
        cluster=CONFIG.ALMA_SAPINVOICES_ECS_CLUSTER_ARN,
        network_configuration=CONFIG.ALMA_SAPINVOICES_VPC_CONFIG,
    )
    status_template = (
        "Task: {task_arn} (type = {run_type}) "
        "Desired_status: {desired_status} "
        "Last status: {last_status}"
    )

    review_run_tasks = [task for task in session["tasks"] if task["run_type"] == "Review"]

    if len(review_run_tasks) > 0:
        status_updates = []
        for task in review_run_tasks:
            response = ecs_client.get_task_status([task["task_arn"]])
            task_details = response["tasks"][0]
            status_updates.append(
                status_template.format(
                    task_arn=task["task_arn"],
                    run_type=task["run_type"],
                    desired_status=task_details["desiredStatus"],
                    last_status=task_details["lastStatus"],
                )
            )

        return render_template(
            "views/process_invoices.html",
            review_run_output="\n".join(status_updates),
        )

    return render_template(
        "views/process_invoices.html",
        review_run_output="No tasks are running.",
    )


@bp.route("/process-invoices/review-run/results")
def display_review_result():
    log_group = f"carbon-ecs-{CONFIG.WORKSPACE}"
    cloudwatch_client = CloudWatchClient(log_group=log_group)

    # [TODO]: If session contains multiple task, need to be able to identify
    # which task to display results for
    response = cloudwatch_client.get_task_result(
        start_time=session["tasks"][0]["start_time"],
        end_time=int(datetime.now().strftime("%s")),
        query=(
            "fields @logStream, @message |"
            f"filter @logStream='carbon/{log_group}/{session['tasks'][0]['task_id']}'"
        ),
    )
    print(response)
    print(f"START TIME: {session["tasks"][0]["start_time"]}")
    return render_template(
        "views/process_invoices.html",
        review_run_output=f"Logs: {response}",
    )


#############
# Final Run
#############


@bp.route("/process-invoices/final-run")
def process_invoices_final_run():
    ecs_client = ECSClient(
        cluster=CONFIG.ALMA_SAPINVOICES_ECS_CLUSTER_ARN,
        network_configuration=CONFIG.ALMA_SAPINVOICES_VPC_CONFIG,
    )

    # [TODO] Uncomment when ready for testing ECS task runs!
    response = ecs_client.run_task(
        taskDefinition=CONFIG.ALMA_SAPINVOICES_ECS_TASK_ARN,
        overrides={
            "containerOverrides": [
                {
                    "name": "carbon-ecs-stage",
                    "command": ["--run_connection_tests", "--ignore_sns_logging"],
                }
            ]
        },
    )

    container_details = response["tasks"][0]["containers"][0]

    # track ARN for task run in session
    task_arn = container_details["taskArn"]
    session["tasks"].append({"task_arn": task_arn, "run_type": "Final"})
    session.modified = True
    # session["tasks"].append({"task_arn": "ARN", "run_type": "Final"})
    return render_template(
        "views/process_invoices.html",
        final_run_output=f"Running {container_details['name']} task: {container_details["taskArn"]}",
        # review_run_output=f"Running task: {session["task_arn"]}",
    )


@bp.route("/process-invoices/final-run/check-task-status")
def check_status_final_run():
    ecs_client = ECSClient(
        cluster=CONFIG.ALMA_SAPINVOICES_ECS_CLUSTER_ARN,
        network_configuration=CONFIG.ALMA_SAPINVOICES_VPC_CONFIG,
    )

    status_template = (
        "Task: {task_arn} (type = {run_type}) "
        "Desired_status: {desired_status} "
        "Last status: {last_status}"
    )

    final_run_tasks = [task for task in session["tasks"] if task["run_type"] == "Final"]

    if len(final_run_tasks) > 0:
        status_updates = []
        for task in final_run_tasks:
            response = ecs_client.get_task_status([task["task_arn"]])
            task_details = response["tasks"][0]
            status_updates.append(
                status_template.format(
                    task_arn=task["task_arn"],
                    run_type=task["run_type"],
                    desired_status=task_details["desiredStatus"],
                    last_status=task_details["lastStatus"],
                )
            )

        return render_template(
            "views/process_invoices.html",
            final_run_output="\n".join(status_updates),
        )

    return render_template(
        "views/process_invoices.html",
        final_run_output="No tasks are running.",
    )
