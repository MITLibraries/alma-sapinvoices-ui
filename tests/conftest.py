import pytest

from webapp import Config, create_app


@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    monkeypatch.setenv("ALMA_SAP_INVOICES_ECS_CLUSTER", "test")
    monkeypatch.setenv("ALMA_SAP_INVOICES_ECS_TASK_DEFINITION", "test")
    monkeypatch.setenv(
        "ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG", '{"awsvpcConfiguration": "test"}'
    )
    monkeypatch.setenv("WORKSPACE", "test")
    monkeypatch.setenv("SENTRY_DSN", "https://1234567890@00000.ingest.sentry.io/123456")


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
