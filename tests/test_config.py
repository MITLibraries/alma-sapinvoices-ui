import logging

import pytest

from webapp.config import configure_logger, configure_sentry


def test_config_check_required_env_vars_success(config):
    config.check_required_env_vars()


def test_config_check_required_env_vars_error(monkeypatch, config):
    monkeypatch.delenv("WORKSPACE")
    with pytest.raises(OSError, match="Missing required environment variables"):
        config.check_required_env_vars()


def test_configure_logger_not_verbose(config, caplog):
    logger = logging.getLogger(__name__)
    result = configure_logger(verbose=False)
    assert logger.getEffectiveLevel() == logging.INFO
    assert result == "Logger 'root' configured with level=INFO"


def test_configure_logger_verbose(config, caplog):
    logger = logging.getLogger(__name__)
    result = configure_logger(verbose=True)
    assert logger.getEffectiveLevel() == logging.DEBUG
    assert result == "Logger 'root' configured with level=DEBUG"


def test_configure_sentry_if_dsn_exists(config, caplog, monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://1234567890@00000.ingest.sentry.io/123456")

    assert (
        configure_sentry()
        == "Sentry DSN found, exceptions will be sent to Sentry with env=test"
    )


def test_configure_sentry_if_dsn_missing(config, caplog, monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert (
        configure_sentry() == "No Sentry DSN found, exceptions will not be sent to Sentry"
    )


def test_config_env_access_success(config):
    assert config.WORKSPACE == "test"


def test_config_env_access_error(config):
    with pytest.raises(
        AttributeError, match="'DOES_NOT_EXIST' not a valid configuration variable"
    ):
        _ = config.DOES_NOT_EXIST


def test_config_env_access_network_config_success(monkeypatch, config):
    assert config.ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG == {
        "awsvpcConfiguration": {
            "subnets": ["subnet-abc123", "subnet-def456"],
            "securityGroups": ["sg-abc123"],
            "assignPublicIp": "DISABLED",
        }
    }
