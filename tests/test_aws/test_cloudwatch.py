import pytest

from webapp.exceptions import ECSTaskLogStreamDoesNotExistError


def test_cloudwatchlogs_client_init_success(cloudwatchlogs_client):
    assert cloudwatchlogs_client.log_group_name == "mock-sapinvoices-ecs-test"
    assert (
        cloudwatchlogs_client.log_stream_name_prefix
        == "sapinvoices/mock-sapinvoices-ecs-test/"
    )


def test_cloudwatchlogs_client_get_log_messages_review_run_success(
    cloudwatchlogs_client,
    cloudwatch_sapinvoices_review_run_logs,
    mock_cloudwatchlogs_log_stream_review_run_task,
):
    assert cloudwatchlogs_client.get_log_messages(task_id="abc001") == [
        "INFO sapinvoices.cli.process_invoices(): SAP invoice process completed for a review run",  # noqa: E501
        "3 monograph invoices retrieved and processed:",
        "2 SAP monograph invoices",
        "1 other payment monograph invoices",
        "2 serial invoices retrieved and processed",
    ]


def test_cloudwatchlogs_client_get_log_messages_final_run_success(
    cloudwatchlogs_client,
    cloudwatch_sapinvoices_final_run_logs,
    mock_cloudwatchlogs_log_stream_final_run_task,
):
    assert cloudwatchlogs_client.get_log_messages(task_id="abc002") == [
        "INFO sapinvoices.cli.process_invoices(): SAP invoice process completed for a final run",  # noqa: E501
        "3 monograph invoices retrieved and processed:",
        "2 SAP monograph invoices",
        "1 other payment monograph invoices",
        "2 serial invoices retrieved and processed",
    ]


def test_cloudwatchlogs_client_get_log_events_raise_error(
    cloudwatchlogs_client,
    mock_cloudwatchlogs_log_group,
):
    with pytest.raises(
        ECSTaskLogStreamDoesNotExistError,
        match="No log streams found for task id 'DOES_NOT_EXIST'.",
    ):
        assert cloudwatchlogs_client.get_log_events(task_id="DOES_NOT_EXIST")
