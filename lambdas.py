import json
import logging

from apig_wsgi import make_lambda_handler

from webapp import Config, create_app

logger = logging.getLogger(__name__)
CONFIG = Config()


def lambda_handler(event: dict, context: dict) -> dict:
    """Launches the Flask app when the Lambda function is invoked.

    This is achieved by using the library 'apig-wsgi' to wrap the Flask app in an
    AWS Lambda handler function. This wrapper converts the Function URL
    request payload into a WSGI object for the Flask app, then converts the
    Flask app response into a payload suitable for the Lambda Function URL
    to return to the caller.

    See https://github.com/adamchainz/apig-wsgi/tree/main.
    """
    CONFIG.check_required_env_vars()
    CONFIG.configure_logger(verbose=True)
    CONFIG.configure_sentry()

    apig_wsgi_handler = make_lambda_handler(create_app())

    try:
        logger.debug(json.dumps(event))
    except TypeError as error:
        logger.warning(error)

    return apig_wsgi_handler(event, context)
