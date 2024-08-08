import json

import lambdas


def test_lambda_handler_success(lambda_function_event_payload):
    response = lambdas.lambda_handler(lambda_function_event_payload, {})
    assert response["statusCode"] == 200


def test_lambda_handler_returns_json(lambda_function_event_payload):
    response = lambdas.lambda_handler(lambda_function_event_payload, {})
    assert json.dumps(response)


def test_lambda_handler_logs_warning_if_event_not_json_serializble(
    lambda_function_event_payload, caplog
):
    bad_event = lambda_function_event_payload
    bad_event["bad_item"] = Exception("I can't be serialized")
    _ = lambdas.lambda_handler(bad_event, {})
    assert "Object of type Exception is not JSON serializable" in caplog.text
