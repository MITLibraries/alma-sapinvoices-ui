# ruff: noqa: G004
import base64
import json
import logging
from typing import Any

import jwt
import requests
from flask_login import current_user

from webapp.config import Config
from webapp.exceptions import ECSTaskDoesNotExistError
from webapp.utils.aws import CloudWatchLogsClient, ECSClient

logger = logging.getLogger(__name__)


def get_task_status_and_logs(task_id: str) -> tuple[str, list]:
    """Utility method for retrieving task status and logs using AWS clients.

    The method relies on instances of ECSClient and CloudWatchLogsClient.
    To understand the flow of logic described below, some important clarification:

    * "task exists": This means the task appears in the Amazon ECS task history.
       Tasks are retained for about an hour after stopping.

    * "task does not exist": This means the task does not show up in the Amazon ECS
       task history. This does not mean the task wasn't executed -- just that it wasn't
       run within the last hour. A CloudWatch log stream may exist for the task.

    The flow of logic is as follows:

    1. Get the status of a task.
       - If the ECS task exists, the status for the task is retrieved.
         When task_status = "STOPPED" the ECS task is considered "COMPLETED"
         (the task run completed).
       - If the ECS task does not exist, proceed.

    2. Get the logs for the task.
       - Whether or not the ECS task exists, retrieve the logs when
         task_status = "COMPLETED". This ensures full set of logs are retrieved
         only when the task run completed. If logs are not found,
         raise ECSTaskLogStreamDoesNotExistError.
    """
    ecs_client = ECSClient()
    cloudwatchlogs_client = CloudWatchLogsClient()
    # If task exists, get the current status
    try:
        task_status = (
            "COMPLETED"
            if (status := ecs_client.get_task_status(task_id)) == "STOPPED"
            else status
        )
    except ECSTaskDoesNotExistError:
        task_status = "UNKNOWN"

    logs = ["Loading."]
    if task_status in ["COMPLETED", "UNKNOWN"]:
        logs = cloudwatchlogs_client.get_log_messages(task_id)
        if not logs:
            return "EXPIRED (UNKNOWN)", ["Log stream expired, cannot find logs for task."]

    return task_status, logs


def log_activity(message: str) -> None:
    """Logs actions taken by the current_user logged in."""
    if current_user.is_authenticated:
        logger.info(f"{current_user.name} {message}")


def parse_oidc_data(
    encoded_jwt: str,
    options: dict[str, Any] | None = None,
    *,
    verify: bool = True,
) -> Any:  # noqa: ANN401
    """Retrieve parsed OIDC data and access token from request headers.

    Authentication and authorization is handled by an Application Load Balancer (ALB).
    After the ALB authenticates a user successfully, it sends user claims received
    from the IdP (Okta) to the target (this app), along with an access token.
    The access token is provided in plain text and the user claims (OIDC data)
    in JSON web tokens (JWT) format. This method will parse OIDC data
    from the encoded user claims JWT.

    For more details, see:
    https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-authenticate-users.html
    """
    # parse JWT headers
    jwt_headers_str = encoded_jwt.split(".")[0]
    decoded_jwt_headers_json = base64.b64decode(jwt_headers_str).decode()
    jwt_headers = json.loads(decoded_jwt_headers_json)

    # get the key id from headers
    key_id = jwt_headers["kid"]

    # get the public key from regional endpoint
    url = (
        "https://public-keys.auth.elb."
        + Config().AWS_DEFAULT_REGION
        + ".amazonaws.com/"
        + key_id
    )
    pub_key = requests.get(url, timeout=60).text

    # decode payload
    return jwt.decode(
        encoded_jwt,
        pub_key,
        algorithms=["ES256"],
        verify=verify,
        options=options,
    )
