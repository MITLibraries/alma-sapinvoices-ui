import logging
import re
import time
from typing import TYPE_CHECKING, Literal

import boto3
from attrs import define, field

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient as ECSClientType

from webapp.config import Config
from webapp.exceptions import (
    ECSTaskDefinitionDoesNotExistError,
    ECSTaskDoesNotExistError,
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
    def task_family(self) -> str:
        return re.sub(":.*", "", self.task_family_revision)

    @property
    def task_family_revision(self) -> str:
        return self.task_definition.split("/")[-1]

    def execute_review_run(self) -> str | None:
        logger.info("Executing ECS task for 'Review Run'")
        return self.run(run_type="review", commands=["--blah"])

    def execute_final_run(self) -> str | None:
        logger.info("Executing ECS task for 'Final Run'")
        return self.run(run_type="final", commands=["--blah", "--bloop"])

    def run(
        self, run_type: Literal["review", "final"], commands: list | None = None
    ) -> str | None:
        """Execute an ECS task run."""
        if run_type not in ["review", "final"]:
            message = f"Cannot run task for unrecognized run_type='{run_type}'"
            raise ValueError(message)

        if self.task_definition_exists():
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
            return response["tasks"][0]["taskArn"]
        raise ECSTaskDefinitionDoesNotExistError(self.task_definition)

    def monitor_task(self, task_id: str, timeout: int = 600) -> None:
        """Polls ECS for task status updates.

        This method will periodically (every 5 seconds) check for the status
        of the running ECS task that matches the provided task ARN.
        When the task run is complete, details of the run are returned.
        """
        start = time.time()
        while True:
            if time.time() - start > timeout:
                raise ECSTaskRuntimeExceededTimeoutError(timeout)
            task_status = self.get_task_status(task_id)
            if task_status == "STOPPED":
                logger.info("Task run has completed.")
                break
            time.sleep(5)

    def get_task_status(self, task_id: str) -> str:
        """Get status of an ECS task.

        For more information on the different stages of the ECS task lifecycle,
        see https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-lifecycle-explanation.html.

        Args:
            task_id (str): ECS task ID.

        Returns:
            str: Status of an ECS task, representing a stage of the task lifecycle.
        """
        if self.task_exists(task_id):
            response = self.client.describe_tasks(cluster=self.cluster, tasks=[task_id])
            task_status = response["tasks"][0]["lastStatus"]
            message = f"Status for task {task_id}: {task_status}"
            logger.info(message)
            return task_status
        raise ECSTaskDoesNotExistError(task_id)

    def get_active_tasks(self) -> dict:
        """Get active ECS tasks.

        Tasks are considered 'active' when their 'lastStatus'
        is not "STOPPED". The method returns a dictionary of
        task IDs, sorted by the 'createdAt' timestamps in
        descending (most recent) order.

        Returns:
            dict: Active task IDs (keys) and the corresponding
                'createdAt' timestamps (values).
        """
        if any(tasks := self.get_tasks()):
            response = self.client.describe_tasks(cluster=self.cluster, tasks=tasks)
            active_tasks = {
                task["taskArn"].split("/")[-1]: task["createdAt"]
                for task in response["tasks"]
                if task["lastStatus"] != "STOPPED"
            }
            return dict(
                sorted(active_tasks.items(), key=lambda item: item[1], reverse=True)
            )
        return None

    def task_exists(self, task_id: str) -> bool:
        """Determine if the task exists.

        Given a task ID, this method will determine whether the task
        exists by looping through the list of ARNs recently executed ECS
        tasks and checking if the task ID appears in any of the task ARNs.

        Note: Task runs are retained by ECS for a limited amount of time.

        Args:
            task_id (str): ECS task ID.

        Returns:
            bool: If task run exists, return True, else False.
        """
        return any(task_id in task_arn for task_arn in self.get_tasks())

    def task_definition_exists(self) -> bool:
        """Determine if the task definition exists.

        This method will determine if the task definition exists by
        looping through the list of task definition ARNs and seeing if
        ECSClient.task_family_revision appears in any of the task definition
        ARNS.
        """
        response = self.client.list_task_definitions(
            familyPrefix=self.task_family, sort="DESC"
        )
        existing_task_definitions = [
            task.split("/")[-1] for task in response["taskDefinitionArns"]
        ]
        return self.task_family_revision in existing_task_definitions

    def get_tasks(self) -> list[str]:
        """Get list of all ECS tasks."""
        existing_tasks = set()
        for status in ["RUNNING", "PENDING", "STOPPED"]:
            response = self.client.list_tasks(
                cluster=self.cluster,
                family=self.task_family,
                desiredStatus=status,  # type: ignore[arg-type]
            )
            existing_tasks.update(response["taskArns"])
        return list(existing_tasks)
