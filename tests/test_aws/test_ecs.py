# ruff: noqa: E501
import os

import pytest

from webapp.exceptions import (
    ECSTaskDefinitionDoesNotExistError,
    ECSTaskDoesNotExistError,
    ECSTaskRuntimeExceededTimeoutError,
)
from webapp.utils.aws import ECSClient


def test_ecs_client_init_success(ecs_client):
    assert ecs_client.cluster == os.environ["ALMA_SAP_INVOICES_ECS_CLUSTER"]
    assert (
        ecs_client.task_definition == os.environ["ALMA_SAP_INVOICES_ECS_TASK_DEFINITION"]
    )
    assert ecs_client.network_configuration == {
        "awsvpcConfiguration": {
            "subnets": ["subnet-abc123", "subnet-def456"],
            "securityGroups": ["sg-abc123"],
            "assignPublicIp": "DISABLED",
        }
    }
    assert ecs_client.container == os.environ["ALMA_SAP_INVOICES_ECR_IMAGE_NAME"]


def test_ecs_client_task_family_property_success(ecs_client):
    assert (
        ecs_client.task_definition
        == "arn:aws:ecs:us-east-1:123456789012:task-definition/mock-sapinvoices-ecs-test:1"
    )
    assert ecs_client.task_family == "mock-sapinvoices-ecs-test"


def test_ecs_client_task_family_revision_property_success(ecs_client):
    assert (
        ecs_client.task_definition
        == "arn:aws:ecs:us-east-1:123456789012:task-definition/mock-sapinvoices-ecs-test:1"
    )
    assert ecs_client.task_family_revision == "mock-sapinvoices-ecs-test:1"


def test_ecs_client_execute_review_run_success(
    ecs_client, ecs_client_execute_run_details_success, caplog
):
    assert (
        ecs_client.execute_review_run()
        == "arn:aws:ecs:us-east-1:123456789012:task/mock-sapinvoices-ecs-test/abc123"
    )
    assert "Executing ECS task for 'Review Run'" in caplog.text


def test_ecs_client_execute_final_run_success(
    ecs_client, ecs_client_execute_run_details_success, caplog
):
    assert (
        ecs_client.execute_final_run()
        == "arn:aws:ecs:us-east-1:123456789012:task/mock-sapinvoices-ecs-test/abc123"
    )
    assert "Executing ECS task for 'Final Run'" in caplog.text


def test_ecs_client_run_raise_error_if_run_type_is_invalid(ecs_client):
    with pytest.raises(
        ValueError, match="Cannot run task for unrecognized run_type='invalid'"
    ):
        ecs_client.run(run_type="invalid")


def test_client_run_raise_error_if_task_definition_does_not_exist(
    mock_ecs_task_definition,
):
    bad_ecs_client = ECSClient(
        cluster="test",
        task_definition="DOES_NOT_EXIST",
        network_configuration="test",
        container="test",
    )
    with pytest.raises(
        ECSTaskDefinitionDoesNotExistError,
        match=r"No task definition found for 'DOES_NOT_EXIST'.",
    ):
        bad_ecs_client.run(run_type="review")


def test_ecs_client_monitor_task_success(
    ecs_client, mock_ecs_task_state_transitions, caplog
):
    """Mock iterative ECSClient.monitor_task method.

    ECS task state transitions are mocked. Passing this test verifies that
    ECSClient.monitor_task will repeatedly make calls to boto3.ECS.Client.describe_tasks
    until the task is completed (i.e., status="STOPPED") by checking that each
    transition is captured in the logs.

    Note: The captured state transitions comprise of the last four stages of the
          ECS task lifecycle.
          See https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-lifecycle-explanation.html
    """
    task_arn = mock_ecs_task_state_transitions
    ecs_client.monitor_task(task_arn)
    for status in ("DEACTIVATING", "STOPPING", "DEPROVISIONING", "STOPPED"):
        assert status in caplog.text
    assert "Task run has completed." in caplog.text


def test_ecs_client_monitor_task_raise_error(
    ecs_client, mock_ecs_task_state_transitions, caplog
):

    task_arn = mock_ecs_task_state_transitions

    with pytest.raises(
        ECSTaskRuntimeExceededTimeoutError,
        match=r"Task runtime exceeded set timeout of 2 seconds.",
    ):
        ecs_client.monitor_task(task_arn, timeout=2)


def test_ecs_client_get_task_status_success(ecs_client, mock_ecs_task_state_transitions):
    task_arn = mock_ecs_task_state_transitions
    assert ecs_client.get_task_status(task_id=task_arn.split("/")[-1]) == "DEACTIVATING"


def test_ecs_client_get_task_status_raise_error(ecs_client):
    with pytest.raises(
        ECSTaskDoesNotExistError, match=r"No tasks found for id 'DOES_NOT_EXIST'."
    ):
        assert ecs_client.get_task_status(task_id="DOES_NOT_EXIST")


def test_ecs_client_get_active_tasks_success(
    ecs_client, ecs_client_get_active_tasks_success
):
    assert ecs_client.get_active_tasks() == {"abc123": "2024-07-29T17:16:13.688000-04:00"}


def test_ecs_client_task_exists_returns_true(ecs_client, mock_ecs_task_state_transitions):
    task_arn = mock_ecs_task_state_transitions
    assert ecs_client.task_exists(task_id=task_arn.split("/")[-1])


def test_ecs_client_task_exists_returns_false(ecs_client):
    assert ecs_client.task_exists(task_id="DOES_NOT_EXIST") is False


def test_ecs_client_task_definition_returns_true(ecs_client, mock_ecs_task_definition):
    assert ecs_client.task_definition_exists() is True


def test_ecs_client_task_definition_exists_returns_false(mock_ecs_task_definition):
    bad_ecs_client = ECSClient(
        cluster="test",
        task_definition="DOES_NOT_EXIST",
        network_configuration="test",
        container="test",
    )
    assert bad_ecs_client.task_definition_exists() is False
