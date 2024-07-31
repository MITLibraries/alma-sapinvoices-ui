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
    assert (
        cloudwatchlogs_client.get_log_messages(task_id="abc001")
        == cloudwatch_sapinvoices_review_run_logs
    )


def test_cloudwatchlogs_client_get_log_messages_final_run_success(
    cloudwatchlogs_client,
    cloudwatch_sapinvoices_final_run_logs,
    mock_cloudwatchlogs_log_stream_final_run_task,
):
    assert (
        cloudwatchlogs_client.get_log_messages(task_id="abc002")
        == cloudwatch_sapinvoices_final_run_logs
    )


def test_cloudwatchlogs_client_get_log_events_raise_error(
    cloudwatchlogs_client,
    mock_cloudwatchlogs_log_group,
):
    with pytest.raises(
        ECSTaskLogStreamDoesNotExistError,
        match="No log streams found for task id 'DOES_NOT_EXIST'.",
    ):
        assert cloudwatchlogs_client.get_log_events(task_id="DOES_NOT_EXIST")


def test_cloudwatchlogs_client_log_stream_exists_returns_true(
    cloudwatchlogs_client,
    mock_cloudwatchlogs_log_stream_review_run_task,
):
    # Note: Either 'review run' or 'final run' (task_id="abc002") mocked log stream
    #       fixture will work for this test.
    assert cloudwatchlogs_client.log_stream_exists(task_id="abc001") is True


def test_cloudwatchlogs_client_log_stream_exists_returns_false(
    cloudwatchlogs_client, mock_cloudwatchlogs_log_group
):
    assert cloudwatchlogs_client.log_stream_exists(task_id="DOES_NOT_EXIST") is False


def test_cloudwatchlogs_client_get_log_streams_success(
    cloudwatchlogs_client,
    mock_cloudwatchlogs_log_stream_review_run_task,
    mock_cloudwatchlogs_log_stream_final_run_task,
):
    assert cloudwatchlogs_client.get_log_streams() == [
        "sapinvoices/mock-sapinvoices-ecs-test/abc001",
        "sapinvoices/mock-sapinvoices-ecs-test/abc002",
    ]
