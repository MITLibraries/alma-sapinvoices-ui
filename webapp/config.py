# ruff: noqa:ANN401,  N802

import json
import logging
import os
from json import JSONDecodeError
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

from webapp.exceptions import InvalidNetworkConfigurationError

logger = logging.getLogger("__name__")


class Config:
    REQUIRED_ENV_VARS = (
        "ALMA_SAP_INVOICES_ECR_IMAGE_NAME",
        "ALMA_SAP_INVOICES_ECS_CLUSTER",
        "ALMA_SAP_INVOICES_ECS_TASK_DEFINITION",
        "ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG",
        "ALMA_SAP_INVOICES_CLOUDWATCH_LOG_GROUP",
        "SECRET_KEY",
        "WORKSPACE",
    )
    OPTIONAL_ENV_VARS = ("AWS_DEFAULT_REGION",)

    def __getattr__(self, name: str) -> Any:
        """Method to raise exception if required env vars not set."""
        if name in self.REQUIRED_ENV_VARS or name in self.OPTIONAL_ENV_VARS:
            return os.getenv(name)
        message = f"'{name}' not a valid configuration variable"
        raise AttributeError(message)

    def _getenv(self, name: str) -> Any:
        if value := os.getenv(name):
            return value
        if name in self.REQUIRED_ENV_VARS:
            message = f"'{name}' is a required environment variable."
            raise AttributeError(message)
        return None

    @property
    def ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG(self) -> dict:
        network_config = os.getenv("ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG")
        try:
            return json.loads(network_config)  # type: ignore[arg-type]
        except (TypeError, JSONDecodeError) as error:
            raise InvalidNetworkConfigurationError(error) from error

    @property
    def ALMA_SAP_INVOICES_ECR_IMAGE_NAME(self) -> str:
        return self._getenv("ALMA_SAP_INVOICES_ECR_IMAGE_NAME")

    @property
    def ALMA_SAP_INVOICES_ECS_CLUSTER(self) -> str:
        return self._getenv("ALMA_SAP_INVOICES_ECS_CLUSTER")

    @property
    def ALMA_SAP_INVOICES_ECS_TASK_DEFINITION(self) -> str:
        return self._getenv("ALMA_SAP_INVOICES_ECS_TASK_DEFINITION")

    @property
    def ALMA_SAP_INVOICES_CLOUDWATCH_LOG_GROUP(self) -> str:
        return self._getenv("ALMA_SAP_INVOICES_CLOUDWATCH_LOG_GROUP")

    @property
    def AWS_DEFAULT_REGION(self) -> str:
        if region_name := self._getenv("AWS_DEFAULT_REGION"):
            return region_name
        return "us-east-1"

    @property
    def LOGIN_DISABLED(self) -> bool:
        if self._getenv("LOGIN_DISABLED").lower() == "true":  # noqa: SIM103
            return True
        return False

    @property
    def SECRET_KEY(self) -> str:
        return self._getenv("SECRET_KEY")

    @property
    def SENTRY_DSN(self) -> str:
        return self._getenv("SENTRY_DSN")

    @property
    def WORKSPACE(self) -> str:
        return self._getenv("WORKSPACE")

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
                format=(
                    "%(asctime)s %(levelname)s %(name)s.%(funcName)s() "
                    "line %(lineno)d: "
                    "%(message)s"
                )
            )
            logger.setLevel(logging.DEBUG)
        else:
            logging.basicConfig(
                format="%(asctime)s %(levelname)s %(name)s.%(funcName)s(): %(message)s"
            )
            logger.setLevel(logging.INFO)

        return (
            f"Logger '{logger.name}' configured with level="
            f"{logging.getLevelName(logger.getEffectiveLevel())}"
        )

    def configure_sentry(self) -> None:
        if sentry_dsn := self.SENTRY_DSN:
            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=self.WORKSPACE,
                integrations=[
                    AwsLambdaIntegration(),
                ],
                traces_sample_rate=1.0,
            )
            logger.info(
                "Sentry DSN found, exceptions will be sent to Sentry with env=%s",
                self.WORKSPACE,
            )
        else:
            logger.info("No Sentry DSN found, exceptions will not be sent to Sentry")
