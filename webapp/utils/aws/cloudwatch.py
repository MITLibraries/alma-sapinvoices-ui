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
            messages.extend(event["message"] for event in logs)
        return messages

    def get_log_events(self, task_id: str) -> list:
        logger.info("Retrieving CloudWatch logs for task.")
        log_events = []
        params = {
            "logGroupName": self.log_group_name,
            "logStreamName": f"{self.log_stream_name_prefix}{task_id}",
            "startFromHead": True,
        }

        if self.log_stream_exists(task_id):
            while True:
                response = self.client.get_log_events(**params)  # type: ignore[arg-type]
                log_events.extend(response["events"])
                next_token = response.get("nextForwardToken")
                if next_token == params.get("nextToken"):
                    # the end of the stream is marked by returning the same token
                    break
                params["nextToken"] = next_token
            logger.info("CloudWatch logs retrieved.")
            return log_events
        raise ECSTaskLogStreamDoesNotExistError(task_id)

    def log_stream_exists(self, task_id: str) -> bool:
        return any(
            task_id == log_stream_name.split("/")[-1]
            for log_stream_name in self.get_log_streams()
        )

    def get_log_streams(self) -> list[str]:
        log_streams: list[str] = []
        params = {
            "logGroupName": self.log_group_name,
        }
        while True:
            response = self.client.describe_log_streams(**params)  # type: ignore[arg-type]
            log_streams.extend(
                logstream["logStreamName"] for logstream in response["logStreams"]
            )
            next_token = response.get("nextToken")
            if next_token is None:
                # all log streams retrieved is "nextToken" excluded from response
                break
            params["nextToken"] = next_token
        return log_streams
