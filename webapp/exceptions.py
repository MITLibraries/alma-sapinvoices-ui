class InvalidNetworkConfigurationError(Exception):
    """Exception to raise when ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG is invalid."""


class ECSTaskLogStreamDoesNotExistError(Exception):
    """Exception to raise when a log stream is not found."""

    def __init__(self, task_id: str) -> None:
        super().__init__(f"No log streams found for task id '{task_id}'.")


class ECSTaskDoesNotExistError(Exception):
    """Exception to raise when an ECS task run is not found in ECS task history."""

    def __init__(self, task_id: str) -> None:
        super().__init__(f"No tasks found for id '{task_id}'.")


class ECSTaskDefinitionDoesNotExistError(Exception):
    """Exception to raise when ALMA_SAP_INVOICES_ECS_TASK_DEFINITION does not exist."""

    def __init__(self, task_definition: str) -> None:
        super().__init__(f"No task definition found for '{task_definition}'.")


class ECSTaskRuntimeExceededTimeoutError(TimeoutError):
    def __init__(self, timeout: int) -> None:
        super().__init__(f"Task runtime exceeded set timeout of {timeout} seconds.")
