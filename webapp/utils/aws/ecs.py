import logging
import re
import time
from typing import TYPE_CHECKING, Literal

import boto3
from attrs import define, field

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient as ECSClientType

from webapp import Config
from webapp.exceptions import (
    ECSTaskDefinitionDoesNotExistError,
    ECSTaskRuntimeExceededTimeoutError,
)

logger = logging.getLogger(__name__)


@define
class ECSClient:
    """ECS Client for running and monitoring task runs."""

    cluster: str = field(factory=lambda: Config().ALMA_SAP_INVOICES_ECS_CLUSTER)
    task_definition: str = field(
        factory=lambda: Config().ALMA_SAP_INVOICES_ECS_TASK_DEFINITION
    )
    network_configuration: dict = field(
        factory=lambda: Config().ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG
    )
    container: str = field(factory=lambda: Config().ALMA_SAP_INVOICES_ECR_IMAGE_NAME)

    @property
    def client(self) -> "ECSClientType":
        return boto3.client("ecs")

    @property
    def task_family_revision(self) -> str:
        return self.task_definition.split("/")[-1]

    @property
    def task_family(self) -> str:
        return re.sub(":.*", "", self.task_family_revision)

    def execute_review_run(self) -> dict | None:
        logger.info("Executing ECS task for 'Review Run'")
        return self.run(run_type="review", commands=["--real"])

    def execute_final_run(self) -> dict | None:
        logger.info("Executing ECS task for 'Final Run'")
        return self.run(run_type="final", commands=["--real", "--final"])

    def run(
        self, run_type: Literal["review", "final"], commands: list | None = None
    ) -> dict | None:
        if run_type not in ["review", "final"]:
            message = f"Cannot run task for unrecognized run_type='{run_type}'"
            raise ValueError(message)

        if self.task_exists():
            response = self.client.run_task(
                cluster=self.cluster,
                launchType="FARGATE",
                networkConfiguration=self.network_configuration,  # type: ignore[arg-type]
                overrides={  # type: ignore[arg-type, misc]
                    "containerOverrides": [
                        {
                            "name": self.container,
                            "command": commands,
                        }
                    ]
                },
                taskDefinition=self.task_definition,
            )
            return self.parse_run_details(response)  # type: ignore[arg-type]
        return None

    def monitor_task(self, task: str, timeout: int = 600) -> dict:
        """Polls ECS for task status updates.

        This method will periodically (every 5 seconds) check for the status
        of the running ECS task that matches the provided task ARN.
        When the task run is complete, details of the run are returned.
        """
        start = time.time()
        while True:
            if time.time() - start > timeout:
                raise ECSTaskRuntimeExceededTimeoutError(timeout)
            response = self.client.describe_tasks(cluster=self.cluster, tasks=[task])
            task_run_details = self.parse_run_details(response)  # type: ignore[arg-type]
            task_status = task_run_details["status"]

            message = f"Status for task {task}: {task_status}"
            logger.info(message)

            if task_status == "STOPPED":
                logger.info("Task run has completed.")
                break
            time.sleep(5)
        return task_run_details

    def task_exists(self) -> bool | None:
        response = self.client.list_task_definitions(
            familyPrefix=self.task_family, sort="DESC"
        )
        valid_tasks = [task.split("/")[-1] for task in response["taskDefinitionArns"]]

        if self.task_family_revision in valid_tasks:
            return True
        raise ECSTaskDefinitionDoesNotExistError(self.task_definition)

    def parse_run_details(self, details: dict) -> dict:
        """Parse task run details.

        Note: While the 'taskArn' and 'lastStatus' parameters are automatically populated
              when an ECS task is kicked off, other parameters -- like 'createdAt'
              and 'stoppedAt' are populated as the task is running.

        For more information on the response syntax provided by boto3.ECS.Client.run_task,
        see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs/client/run_task.html.
        """
        task_details = details["tasks"][0]
        return {
            "task_run_arn": task_details["taskArn"],
            "status": task_details["lastStatus"],
            "created_at": task_details.get("createdAt"),
            "stopped_at": task_details.get("stoppedAt"),
        }
