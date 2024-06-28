import logging
import pytest

from webapp import Config
from webapp.exceptions import InvalidNetworkConfiguration


def test_configure_logger_not_verbose(config: Config, caplog):
    logger = logging.getLogger(__name__)
    result = config.configure_logger(verbose=False)
    assert logger.getEffectiveLevel() == logging.INFO
    assert result == "Logger 'root' configured with level=INFO"


def test_configure_logger_verbose(config: Config, caplog):
    logger = logging.getLogger(__name__)
    result = config.configure_logger(verbose=True)
    assert logger.getEffectiveLevel() == logging.DEBUG
    assert result == "Logger 'root' configured with level=DEBUG"


def test_config_check_required_env_vars_error(monkeypatch, config):
    monkeypatch.delenv("WORKSPACE")
    with pytest.raises(OSError, match="Missing required environment variables"):
        config.check_required_env_vars()


def test_config_env_access_success(config):
    assert config.WORKSPACE == "test"


def test_config_env_access_error(config):
    with pytest.raises(
        AttributeError, match="'DOES_NOT_EXIST' not a valid configuration variable"
    ):
        config.DOES_NOT_EXIST


def test_config_env_access_raise_error_if_network_config_not_json(config):
    with pytest.raises(InvalidNetworkConfiguration):
        config.ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG


def test_config_env_access_raise_error_if_network_config_is_none(monkeypatch, config):
    monkeypatch.delenv("ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG")
    with pytest.raises(
        InvalidNetworkConfiguration,
        match="the JSON object must be str, bytes or bytearray, not NoneType",
    ):
        config.ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG
