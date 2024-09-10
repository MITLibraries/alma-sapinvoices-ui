from http import HTTPStatus
from unittest import mock

from flask import session
from flask_login import current_user

from webapp.app import User


def test_app_request_index_success(
    sapinvoices_client, mock_parse_oidc_data, mock_request_headers_oidc_data
):
    response = sapinvoices_client.get("/", headers=mock_request_headers_oidc_data)
    assert response.status_code == HTTPStatus.OK
    assert "Welcome, Authenticated User!" in response.text


def test_app_request_index_unauthorized_error(sapinvoices_client):
    responses = sapinvoices_client.get("/")
    assert responses.status_code == HTTPStatus.UNAUTHORIZED


def test_app_login_identifies_current_user_success(
    sapinvoices_app,
    authenticated_user,
    mock_parse_oidc_data,
    mock_request_headers_oidc_data,
):
    with sapinvoices_app.test_request_context(headers=mock_request_headers_oidc_data):
        assert current_user == authenticated_user


def test_app_login_cannot_identify_user_if_missing_request_headers(
    sapinvoices_app, authenticated_user, mock_parse_oidc_data, caplog
):
    with sapinvoices_app.test_request_context():
        assert current_user.is_anonymous
        assert current_user != authenticated_user
        assert (
            "Access token ('x-amzn-oidc-accesstoken') is missing "
            "from the request headers."
        ) in caplog.text


def test_app_user_from_session_data_success(
    sapinvoices_client,
    authenticated_user,
    mock_parse_oidc_data,
    mock_request_headers_oidc_data,
):
    with sapinvoices_client:
        sapinvoices_client.get("/", headers=mock_request_headers_oidc_data)
        assert User.from_session_data() == authenticated_user


def test_app_user_from_session_data_returns_none_if_missing_oidc_data(
    sapinvoices_client, mock_parse_oidc_data, mock_request_headers_oidc_data
):
    with sapinvoices_client:
        sapinvoices_client.get("/", headers=mock_request_headers_oidc_data)

        # remove 'oidc_data' from session
        session.pop("oidc_data")

        assert User.from_session_data() is None


def test_app_log_activity_executed_runs_success(
    sapinvoices_client,
    ecs_client,
    mock_parse_oidc_data,
    mock_request_headers_oidc_data,
    caplog,
):
    with sapinvoices_client, mock.patch(
        "webapp.app.ECSClient.execute_review_run"
    ) as mock_ecsclient_review_run:
        mock_ecsclient_review_run.return_value = "abc123"
        sapinvoices_client.get(
            "/process-invoices/run/review/execute", headers=mock_request_headers_oidc_data
        )
        assert (
            "Authenticated User executed a 'review' run (task ID = 'abc123')."
            in caplog.text
        )


def test_app_log_activity_checked_task_status_success(
    sapinvoices_client, mock_parse_oidc_data, mock_request_headers_oidc_data, caplog
):
    with sapinvoices_client:
        sapinvoices_client.get(
            "/process-invoices/status/abc123", headers=mock_request_headers_oidc_data
        )
        assert "Authenticated User checked the status for task 'abc123'." in caplog.text


def test_app_log_activity_logged_out_success(
    sapinvoices_client, mock_parse_oidc_data, mock_request_headers_oidc_data, caplog
):
    with sapinvoices_client:
        sapinvoices_client.get("/logout", headers=mock_request_headers_oidc_data)
        assert "Authenticated User logged out." in caplog.text
