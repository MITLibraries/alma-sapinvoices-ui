import logging
from typing import TYPE_CHECKING

import boto3
from attrs import define, field

if TYPE_CHECKING:
    from mypy_boto3_logs.client import CloudWatchLogsClient as CloudWatchLogsClientType

from webapp.config import Config
from webapp.exceptions import ECSTaskLogStreamDoesNotExistError

logger = logging.getLogger(__name__)


@define
class CloudWatchLogsClient:
    """CloudWatch Logs client for retrieving logs.

    The client is used to retrieve logs for ECS task runs.
    A log stream is created for each ECS task run, easily
    identifiable as the ECS task ID is included in the
    log stream name. For this reason, the client only requires
    the log group name and the task ID to get the log stream
    associated with an ECS task.
    """

    log_group_name: str = field(
        factory=lambda: Config().ALMA_SAP_INVOICES_CLOUDWATCH_LOG_GROUP
    )
    log_stream_name_prefix: str = field(
        factory=lambda: f"sapinvoices/{Config().ALMA_SAP_INVOICES_CLOUDWATCH_LOG_GROUP}/"
    )

    @property
    def client(self) -> "CloudWatchLogsClientType":
        return boto3.client("logs")

    def get_log_messages(self, task_id: str) -> list:
        messages: list = []
        if logs := self.get_log_events(task_id):
            return self.get_log_summary(logs)
        return messages

    def get_log_summary(self, logs: list[dict]) -> list[str]:
        """Get summary of SAP invoice processing logs.

        This function will first determine the index of the log event
        the marks the start of the "summary" log messages that
        describe the output of the SAP invoice processing run.
        The function will then retrieve all the messages starting from
        that index, effectively retrieving a summary of the run.
        """
        summary_index: int | None = None
        for index, event in enumerate(logs):
            message = event["message"]
            if (
                "SAP invoice process completed" in message
                or "No invoices waiting to be sent in Alma" in message
            ):
                summary_index = index
                return [event["message"] for event in logs[summary_index:]]
        return ["SAP invoice process did not complete."]

    def get_log_events(self, task_id: str) -> list:
        logger.info("Retrieving CloudWatch logs for task.")
        log_events = []
        params = {
            "logGroupName": self.log_group_name,
            "logStreamName": f"{self.log_stream_name_prefix}{task_id}",
            "startFromHead": True,
        }

        while True:
            try:
                response = self.client.get_log_events(**params)  # type: ignore[arg-type]
            except self.client.exceptions.ResourceNotFoundException as error:
                raise ECSTaskLogStreamDoesNotExistError(task_id) from error
            log_events.extend(response["events"])
            next_token = response.get("nextForwardToken")
            if next_token == params.get("nextToken"):
                # the end of the stream is marked by returning the same token
                break
            params["nextToken"] = next_token

        logger.info("CloudWatch logs retrieved.")
        return log_events
