import json
import logging
import os

import sentry_sdk
from apig_wsgi import make_lambda_handler
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

from webapp import create_app

logger = logging.getLogger(__name__)

logger.setLevel(logging.DEBUG)

env = os.getenv("WORKSPACE")
if sentry_dsn := os.getenv("SENTRY_DSN"):
    sentry = sentry_sdk.init(
        dsn=sentry_dsn,
        environment=env,
        integrations=[
            AwsLambdaIntegration(),
        ],
        traces_sample_rate=1.0,
    )
    logger.info("Sentry DSN found, exceptions will be sent to Sentry with env=%s", env)
else:
    logger.info("No Sentry DSN found, exceptions will not be sent to Sentry")


# this is the function that lambda should use
apig_wsgi_handler = make_lambda_handler(create_app())


def lambda_handler(event: dict, context: dict) -> dict:
    # if not os.getenv("WORKSPACE"):
    #     unset_workspace_error_message = "Required env variable WORKSPACE is not set"
    #     raise RuntimeError(unset_workspace_error_message)

    logger.debug(json.dumps(event))
    logger.debug(context)

    return apig_wsgi_handler(event, context)
