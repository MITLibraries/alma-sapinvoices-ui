# ruff: noqa: E501, PT004
import json
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.moto_api import state_manager

from webapp import Config, create_app
from webapp.utils.aws import ECSClient

AWS_DEFAULT_REGION = "us-east-1"


@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    monkeypatch.setenv("ALMA_SAP_INVOICES_ECR_IMAGE_NAME", "mock-sapinvoices-test")
    monkeypatch.setenv(
        "ALMA_SAP_INVOICES_ECS_CLUSTER",
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/mock-sapinvoices-ecs-test",
    )
    monkeypatch.setenv(
        "ALMA_SAP_INVOICES_ECS_TASK_DEFINITION",
        f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:task-definition/mock-sapinvoices-ecs-test:1",
    )
    monkeypatch.setenv(
        "ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG",
        '{"awsvpcConfiguration": {"securityGroups": ["sg-abc123"], "subnets": ["subnet-abc123"]}}',
    )
    monkeypatch.setenv("WORKSPACE", "test")
    monkeypatch.setenv("SENTRY_DSN", "https://1234567890@00000.ingest.sentry.io/123456")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def sapinvoices_app(config):
    return create_app(config)


@pytest.fixture
def sapinvoices_client(sapinvoices_app):
    return sapinvoices_app.test_client()


@pytest.fixture
def ecs_client(mock_ecs_cluster, mock_ecs_task_definition, mock_ecs_network_config):
    return ECSClient()


@pytest.fixture
def mock_boto3_client():
    with patch("boto3.client") as mock_client:
        yield mock_client.return_value


@pytest.fixture
def mock_ecs_cluster():
    with mock_aws():
        ecs = boto3.client("ecs", region_name=AWS_DEFAULT_REGION)
        ecs.create_cluster(clusterName="mock-sapinvoices-ecs-test")
        yield


@pytest.fixture
def mock_ecs_task_definition():
    with mock_aws():
        ecs = boto3.client("ecs", region_name=AWS_DEFAULT_REGION)
        definition = {
            "family": "mock-sapinvoices-ecs-test",
            "containerDefinitions": [
                {
                    "name": "mock-sapinvoices-ecs-test",
                    "image": "mock-sapinvoices-test:latest",
                    "memory": 400,
                }
            ],
        }
        ecs.register_task_definition(**definition)
        yield


@pytest.fixture
def mock_ecs_network_config():
    return {
        "awsvpcConfiguration": {
            "securityGroups": ["sg-abc123"],
            "subnets": ["subnet-abc123"],
        }
    }


@pytest.fixture
def mock_ecs_task_state_transitions(
    mock_ecs_cluster, mock_ecs_task_definition, mock_ecs_network_config
):
    with mock_aws():
        state_manager.set_transition(
            model_name="ecs::task", transition={"progression": "manual", "times": 1}
        )
        ecs = boto3.client("ecs", region_name=AWS_DEFAULT_REGION)
        response = ecs.run_task(
            cluster="mock-sapinvoices-ecs-test",
            launchType="FARGATE",
            networkConfiguration=mock_ecs_network_config,
            overrides={},
            taskDefinition="mock-sapinvoices-ecs-test:1",
        )
        yield response["tasks"][0]["taskArn"]


@pytest.fixture
def ecs_client_execute_run_details_success(
    boto3_ecs_client_run_task_response_success,
    mock_boto3_client,
):
    mock_boto3_client.run_task.return_value = boto3_ecs_client_run_task_response_success
    with patch(
        "webapp.utils.aws.ECSClient.task_definition_exists"
    ) as mock_webapp_ecs_client_task_exists:
        mock_webapp_ecs_client_task_exists.return_value = True
        yield


@pytest.fixture
def ecs_client_get_active_tasks_success(
    boto3_ecs_client_describe_task_response_success, mock_boto3_client
):
    mock_boto3_client.describe_tasks.return_value = (
        boto3_ecs_client_describe_task_response_success
    )


@pytest.fixture
def boto3_ecs_client_describe_task_response_success():
    with open("tests/fixtures/ecs_describe_task_response_success.json") as file:
        return json.loads(file.read())


@pytest.fixture
def boto3_ecs_client_run_task_response_success():
    with open("tests/fixtures/ecs_run_task_response_success.json") as file:
        return json.loads(file.read())


@pytest.fixture
def lambda_function_event_payload():
    """Event payload API Gateway sends to Lambda when invoking via function URL.

    This fixture contains a minimal subset of the available payload parameters
    required for testing.

    For a full set of payload paraneters, see:
    https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html
    """
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/",
        "rawQueryString": "",
        "headers": {"header1": "value1", "header2": "value1,value2"},
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api-id",
            "domainName": "id.execute-api.us-east-1.amazonaws.com",
            "domainPrefix": "id",
            "http": {
                "method": "GET",
                "path": "/",
                "protocol": "HTTP/1.1",
                "sourceIp": "192.0.2.1",
                "userAgent": "agent",
            },
            "requestId": "id",
            "routeKey": "$default",
            "stage": "$default",
            "time": "12/Mar/2020:19:03:58 +0000",
            "timeEpoch": 1583348638390,
        },
        "isBase64Encoded": "false",
    }
