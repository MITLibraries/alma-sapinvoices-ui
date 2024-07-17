# ruff: noqa: E501, PT004
import json
from datetime import timedelta
from unittest.mock import patch

import boto3
import pandas as pd
import pytest
from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.core.utils import unix_time_millis, utcnow
from moto.moto_api import state_manager

from webapp import Config, create_app
from webapp.utils.aws import CloudWatchLogsClient, ECSClient

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
    monkeypatch.setenv(
        "ALMA_SAP_INVOICES_CLOUDWATCH_LOG_GROUP", "mock-sapinvoices-ecs-test"
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
def cloudwatchlogs_client():
    return CloudWatchLogsClient()


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
    boto3_ecs_client_describe_tasks_response_success, mock_boto3_client
):
    mock_boto3_client.describe_tasks.return_value = (
        boto3_ecs_client_describe_tasks_response_success
    )
    with patch(
        "webapp.utils.aws.ECSClient.get_tasks"
    ) as mock_webapp_ecs_client_get_tasks:
        mock_webapp_ecs_client_get_tasks.return_value = [
            "arn:aws:ecs:us-east-1:123456789012:task/mock-sapinvoices-ecs-test/abc123"
        ]
        yield


@pytest.fixture
def boto3_ecs_client_run_task_response_success():
    with open("tests/fixtures/ecs_run_task_response_success.json") as file:
        return json.loads(file.read())


@pytest.fixture
def boto3_ecs_client_describe_tasks_response_success():
    with open("tests/fixtures/ecs_describe_tasks_response_success.json") as file:
        return json.loads(file.read())


@pytest.fixture
def mock_cloudwatchlogs_log_group():
    with mock_aws():
        logs = boto3.client("logs", region_name=AWS_DEFAULT_REGION)
        log_group_name = "mock-sapinvoices-ecs-test"
        logs.create_log_group(logGroupName=log_group_name)
        yield log_group_name


@pytest.fixture
def mock_cloudwatchlogs_log_stream_review_run_task(
    cloudwatch_sapinvoices_review_run_logs, mock_cloudwatchlogs_log_group
):
    """Mocks CloudWatch log stream for a 'review run' of SAP invoice processing.

    A log stream is created for the mocked CloudWatch log group.
    Mock events are derived from a CSV file representing the logged messages from a
    a 'review run'. These mocked events are then placed on the mocked log stream.

    The CSV file was exported from CloudWatch and changed slightly for
    testing purposes:

      * The 'timestamp' column was removed as the past dates conflicted with the
        ingestion timestamp when putting log events to the stream.
      * Current timestamps are generated for every logged message.
      * Stats indicated in the logs were updated.
      * To avoid confusion, the past dates were also removed from the values of
        the "messages" column (i.e., the logged messages normally lead with a
        timestamp formatted like so "2024-07-02 13:58:20,524").
    """
    # create log group and log stream
    logs = boto3.client("logs", region_name=AWS_DEFAULT_REGION)
    task_id = "abc001"
    log_stream_name = f"sapinvoices/mock-sapinvoices-ecs-test/{task_id}"
    logs.create_log_stream(
        logGroupName=mock_cloudwatchlogs_log_group, logStreamName=log_stream_name
    )

    # put events on logstream
    timestamped_events = [
        (int(unix_time_millis(utcnow() + timedelta(seconds=count))), event)
        for count, event in enumerate(cloudwatch_sapinvoices_review_run_logs)
    ]
    logs.put_log_events(
        logGroupName=mock_cloudwatchlogs_log_group,
        logStreamName=log_stream_name,
        logEvents=[
            {"timestamp": timestamp, "message": message}
            for timestamp, message in timestamped_events
        ],
    )


@pytest.fixture
def mock_cloudwatchlogs_log_stream_final_run_task(
    cloudwatch_sapinvoices_final_run_logs, mock_cloudwatchlogs_log_group
):
    """Mocks CloudWatch log stream for a 'final run' of SAP invoice processing.

    See docstring for 'mock_cloudwatchlogs_log_stream_review_run_task'.
    """
    # create log group and log stream
    logs = boto3.client("logs", region_name=AWS_DEFAULT_REGION)
    task_id = "abc002"
    log_stream_name = f"sapinvoices/mock-sapinvoices-ecs-test/{task_id}"
    logs.create_log_stream(
        logGroupName=mock_cloudwatchlogs_log_group, logStreamName=log_stream_name
    )

    # put events on logstream
    timestamped_events = [
        (int(unix_time_millis(utcnow() + timedelta(seconds=count))), event)
        for count, event in enumerate(cloudwatch_sapinvoices_final_run_logs)
    ]
    logs.put_log_events(
        logGroupName=mock_cloudwatchlogs_log_group,
        logStreamName=log_stream_name,
        logEvents=[
            {"timestamp": timestamp, "message": message}
            for timestamp, message in timestamped_events
        ],
    )


@pytest.fixture
def cloudwatch_sapinvoices_review_run_logs():
    return pd.read_csv("tests/fixtures/cloudwatch_sapinvoices_review_run_logs.csv")[
        "message"
    ].to_list()


@pytest.fixture
def cloudwatch_sapinvoices_final_run_logs():
    return pd.read_csv("tests/fixtures/cloudwatch_sapinvoices_final_run_logs.csv")[
        "message"
    ].to_list()


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
