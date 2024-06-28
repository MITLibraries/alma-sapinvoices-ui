# ruff: noqa: E501
import json
import os

import pytest

from webapp.exceptions import (
    ECSTaskDefinitionDoesNotExistError,
    ECSTaskRuntimeExceededTimeoutError,
)
from webapp.utils.aws import ECSClient


def test_ecs_client_init_success(ecs_client):
    assert ecs_client.cluster == os.environ["ALMA_SAP_INVOICES_ECS_CLUSTER"]
    assert (
        ecs_client.task_definition == os.environ["ALMA_SAP_INVOICES_ECS_TASK_DEFINITION"]
    )
    assert ecs_client.network_configuration == json.loads(
        os.environ["ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG"]
    )
    assert ecs_client.container == os.environ["ALMA_SAP_INVOICES_ECR_IMAGE_NAME"]


def test_ecs_client_task_family_revision_property_success(ecs_client):
    assert (
        ecs_client.task_definition
        == "arn:aws:ecs:us-east-1:123456789012:task-definition/mock-sapinvoices-ecs-test:1"
    )
    assert ecs_client.task_family_revision == "mock-sapinvoices-ecs-test:1"


def test_ecs_client_task_family_property_success(ecs_client):
    assert (
        ecs_client.task_definition
        == "arn:aws:ecs:us-east-1:123456789012:task-definition/mock-sapinvoices-ecs-test:1"
    )
    assert ecs_client.task_family == "mock-sapinvoices-ecs-test"


def test_ecs_client_execute_review_run_success(
    ecs_client, ecs_client_execute_run_details_success, caplog
):
    assert ecs_client.execute_review_run() == {
        "task_run_arn": "arn:aws:ecs:us-east-1:123456789012:task/mock-sapinvoices-ecs-test/abc123",
        "status": "PROVISIONING",
        "created_at": "2024-07-02T10:16:43.077000-04:00",
        "stopped_at": None,
    }
    assert "Executing ECS task for 'Review Run'" in caplog.text


def test_ecs_client_execute_final_run_success(
    ecs_client, ecs_client_execute_run_details_success, caplog
):
    assert ecs_client.execute_final_run() == {
        "task_run_arn": "arn:aws:ecs:us-east-1:123456789012:task/mock-sapinvoices-ecs-test/abc123",
        "status": "PROVISIONING",
        "created_at": "2024-07-02T10:16:43.077000-04:00",
        "stopped_at": None,
    }
    assert "Executing ECS task for 'Final Run'" in caplog.text


def test_ecs_client_run_task_if_run_type_is_invalid(ecs_client):
    with pytest.raises(
        ValueError, match="Cannot run task for unrecognized run_type='invalid'"
    ):
        ecs_client.run(run_type="invalid")


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


def test_ecs_client_monitor_task_raise_timeout_error(
    ecs_client, mock_ecs_task_state_transitions, caplog
):

    task_arn = mock_ecs_task_state_transitions

    with pytest.raises(
        ECSTaskRuntimeExceededTimeoutError,
        match="Task runtime exceeded set timeout of 2 seconds.",
    ):
        ecs_client.monitor_task(task_arn, timeout=2)


def test_ecs_client_task_exists_success(ecs_client, mock_ecs_task_definition):
    assert ecs_client.task_exists()


def test_ecs_client_task_exists_error(mock_ecs_task_definition):
    bad_ecs_client = ECSClient(
        cluster="test",
        task_definition="DOES_NOT_EXIST",
        network_configuration="test",
        container="test",
    )
    with pytest.raises(
        ECSTaskDefinitionDoesNotExistError,
        match="No task definition found for 'DOES_NOT_EXIST'",
    ):
        _ = bad_ecs_client.task_exists()
