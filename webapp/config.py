import json
import logging
import os

from json import JSONDecodeError
from typing import Any

from webapp.exceptions import InvalidNetworkConfiguration

logger = logging.getLogger("__name__")


class Config:
    REQUIRED_ENV_VARS = (
        "ALMA_SAP_INVOICES_ECS_CLUSTER",
        "ALMA_SAP_INVOICES_ECS_TASK_DEFINITION",
        "ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG",
        "SENTRY_DSN",
        "WORKSPACE",
    )
    OPTIONAL_ENV_VARS = ()

    def __getattr__(self, name: str) -> Any:
        """Method to raise exception if required env vars not set."""
        if name in self.REQUIRED_ENV_VARS or name in self.OPTIONAL_ENV_VARS:
            return os.getenv(name)
        message = f"'{name}' not a valid configuration variable"
        raise AttributeError(message)

    def check_required_env_vars(self) -> None:
        """Method to raise exception if required env vars not set."""
        missing_vars = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing_vars:
            message = f"Missing required environment variables: {', '.join(missing_vars)}"
            raise OSError(message)

    def configure_logger(self, *, verbose: bool) -> str:
        logger = logging.getLogger()
        if verbose:
            logging.basicConfig(
                format="%(asctime)s %(levelname)s %(name)s.%(funcName)s() line %(lineno)d: "
                "%(message)s"
            )
            logger.setLevel(logging.DEBUG)
            for handler in logging.root.handlers:
                handler.addFilter(logging.Filter("lambdas"))
        else:
            logging.basicConfig(
                format="%(asctime)s %(levelname)s %(name)s.%(funcName)s(): %(message)s"
            )
            logger.setLevel(logging.INFO)

        return (
            f"Logger '{logger.name}' configured with level="
            f"{logging.getLevelName(logger.getEffectiveLevel())}"
        )

    @property
    def ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG(self) -> dict:
        network_config = os.getenv("ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG")
        try:
            return json.loads(network_config)  # type: ignore[arg-type]
        except (TypeError, JSONDecodeError) as error:
            raise InvalidNetworkConfiguration(error)

    @property
    def WORKSPACE(self) -> str | None:
        return os.getenv("WORKSPACE")

    @property
    def ALMA_SAP_INVOICES_ECS_CLUSTER(self) -> str | None:
        return os.getenv("ALMA_SAP_INVOICES_ECS_CLUSTER")

    @property
    def ALMA_SAP_INVOICES_ECS_TASK_DEFINITION(self) -> str | None:
        return os.getenv("ALMA_SAP_INVOICES_ECS_TASK_DEFINITION")

    @property
    def SENTRY_DSN(self) -> str | None:
        return os.getenv("SENTRY_DSN")
