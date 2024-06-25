import logging

import pytest

from webapp.exceptions import InvalidNetworkConfigurationError


def test_config_check_required_env_vars_error(monkeypatch, config):
    monkeypatch.delenv("WORKSPACE")
    with pytest.raises(OSError, match="Missing required environment variables"):
        config.check_required_env_vars()


def test_configure_logger_not_verbose(config, caplog):
    logger = logging.getLogger(__name__)
    result = config.configure_logger(verbose=False)
    assert logger.getEffectiveLevel() == logging.INFO
    assert result == "Logger 'root' configured with level=INFO"


def test_configure_logger_verbose(config, caplog):
    logger = logging.getLogger(__name__)
    result = config.configure_logger(verbose=True)
    assert logger.getEffectiveLevel() == logging.DEBUG
    assert result == "Logger 'root' configured with level=DEBUG"


def test_configure_sentry_if_dsn_exists(config, caplog, monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://1234567890@00000.ingest.sentry.io/123456")
    config.configure_sentry()
    assert (
        "Sentry DSN found, exceptions will be sent to Sentry with env=test" in caplog.text
    )


def test_configure_sentry_if_dsn_missing(config, caplog, monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    config.configure_sentry()
    assert "No Sentry DSN found, exceptions will not be sent to Sentry" in caplog.text


def test_config_env_access_success(config):
    assert config.WORKSPACE == "test"


def test_config_env_access_error(config):
    with pytest.raises(
        AttributeError, match="'DOES_NOT_EXIST' not a valid configuration variable"
    ):
        _ = config.DOES_NOT_EXIST


def test_config_env_access_raise_error_if_network_config_not_json(monkeypatch, config):
    monkeypatch.setenv("ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG", "test")
    with pytest.raises(InvalidNetworkConfigurationError, match="Expecting value"):
        _ = config.ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG


def test_config_env_access_raise_error_if_network_config_is_missing(monkeypatch, config):
    monkeypatch.delenv("ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG")
    with pytest.raises(
        InvalidNetworkConfigurationError,
        match="the JSON object must be str, bytes or bytearray, not NoneType",
    ):
        _ = config.ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG
