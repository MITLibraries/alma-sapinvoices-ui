import json
import os


from typing import Any


class Config:
    REQUIRED_ENV_VARS = (
        "ALMA_SAPINVOICES_ECS_CLUSTER_ARN",
        "ALMA_SAPINVOICES_VPC_CONFIG",
        "ALMA_SAPINVOICES_ECS_TASK_ARN",
        "SECRET_KEY",
        "WORKSPACE",
        "SENTRY_DSN",
    )
    OPTIONAL_ENV_VARS = ()

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        """Provide dot notation access to configurations and env vars on this class."""
        if name in self.REQUIRED_ENV_VARS or name in self.OPTIONAL_ENV_VARS:
            if name in ["ALMA_SAPINVOICES_VPC_CONFIG"]:
                return json.loads(os.getenv(name))
            return os.getenv(name)
        message = f"'{name}' not a valid configuration variable"
        raise AttributeError(message)
