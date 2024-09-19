# ruff: noqa:ANN401,  N802

import logging
import os
from typing import Any

import sentry_sdk

logger = logging.getLogger("__name__")


class Config:
    REQUIRED_ENV_VARS = (
        "ALMA_SAP_INVOICES_CLOUDWATCH_LOG_GROUP",
        "ALMA_SAP_INVOICES_ECR_IMAGE_NAME",
        "ALMA_SAP_INVOICES_ECS_CLUSTER",
        "ALMA_SAP_INVOICES_ECS_GROUPS",
        "ALMA_SAP_INVOICES_ECS_SUBNETS",
        "ALMA_SAP_INVOICES_ECS_TASK_DEFINITION",
        "LOGIN_DISABLED",
        "SECRET_KEY",
        "WORKSPACE",
        "SENTRY_DSN",
    )
    OPTIONAL_ENV_VARS = ("AWS_DEFAULT_REGION",)

    def __getattr__(self, name: str) -> Any:
        """Method to raise exception if required env vars not set."""
        if name in self.REQUIRED_ENV_VARS or name in self.OPTIONAL_ENV_VARS:
            return os.getenv(name)
        message = f"'{name}' not a valid configuration variable"
        raise AttributeError(message)

    @property
    def ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG(self) -> dict:
        security_groups = self.ALMA_SAP_INVOICES_ECS_GROUPS
        subnets = self.ALMA_SAP_INVOICES_ECS_SUBNETS
        return {
            "awsvpcConfiguration": {
                "subnets": subnets.split(","),
                "securityGroups": security_groups.split(","),
                "assignPublicIp": "DISABLED",
            }
        }

    @property
    def AWS_DEFAULT_REGION(self) -> str:
        return os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    @property
    def LOGIN_DISABLED(self) -> bool:
        if login_disabled := os.getenv("LOGIN_DISABLED"):  # noqa: SIM102
            if login_disabled.lower() == "true":
                return True
        return False

    def check_required_env_vars(self) -> None:
        """Method to raise exception if required env vars not set."""
        missing_vars = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing_vars:
            message = f"Missing required environment variables: {', '.join(missing_vars)}"
            raise OSError(message)


def configure_logger(*, verbose: bool) -> str:
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


def configure_sentry() -> str:
    env = os.getenv("WORKSPACE")
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn and sentry_dsn.lower() != "none":
        sentry_sdk.init(
            sentry_dsn,
            environment=env,
        )
        return f"Sentry DSN found, exceptions will be sent to Sentry with env={env}"
    return "No Sentry DSN found, exceptions will not be sent to Sentry"
