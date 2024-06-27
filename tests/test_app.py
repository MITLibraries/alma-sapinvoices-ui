from importlib import reload

import lambdas


def test_app_configures_sentry_if_dsn_present(
    caplog,
    monkeypatch,
):
    monkeypatch.setenv("SENTRY_DSN", "https://1234567890@00000.ingest.sentry.io/123456")
    reload(lambdas)
    assert (
        "Sentry DSN found, exceptions will be sent to Sentry with env=test" in caplog.text
    )


def test_app_doesnt_configure_sentry_if_dsn_not_present(caplog, monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    reload(lambdas)
    assert "No Sentry DSN found, exceptions will not be sent to Sentry" in caplog.text


def test_lambda_handler_success(lambda_function_event_payload):
    reload(lambdas)
    response = lambdas.lambda_handler(lambda_function_event_payload, {})
    assert response["body"] == "Hello, World!"
