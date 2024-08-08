from webapp.exceptions import ECSTaskDoesNotExistError
from webapp.utils.aws import CloudWatchLogsClient, ECSClient


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
        task_status = "COMPLETED"

    # If logs cannot be found, task did not exist
    logs = ["Waiting for logs."]
    if task_status == "COMPLETED":
        logs = cloudwatchlogs_client.get_log_messages(task_id)

    return task_status, logs
