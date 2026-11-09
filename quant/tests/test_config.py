from pathlib import Path

import pytest
from dotenv import load_dotenv

from quant.config import Config, REPO_ROOT


def test_environment_values_are_read_when_config_created(monkeypatch):
    monkeypatch.setenv('QUANT_HTTP_TIMEOUT_SECONDS', '12')
    monkeypatch.setenv('QUANT_HTTP_RETRIES', '2')
    monkeypatch.setenv('QUANT_NSE_REQUEST_INTERVAL_SECONDS', '1.7')
    monkeypatch.setenv('QUANT_ENABLE_ANGEL', 'false')
    monkeypatch.setenv('QUANT_DATA_DIR', 'data/config-test')
    config = Config()
    assert config.timeout == 12 and config.retries == 2 and config.request_interval == 1.7
    assert config.data_dir == REPO_ROOT / 'data/config-test'
    assert not config.enable_angel
    monkeypatch.setenv('QUANT_HTTP_TIMEOUT_SECONDS', '15')
    assert Config().timeout == 15


def test_dotenv_precedence_and_config_does_not_contain_secrets(tmp_path, monkeypatch):
    monkeypatch.delenv('QUANT_ENABLE_ANGEL', raising=False)
    monkeypatch.setenv('QUANT_HTTP_TIMEOUT_SECONDS', '19')
    path = tmp_path / '.env'
    path.write_text('QUANT_HTTP_TIMEOUT_SECONDS=25\nQUANT_ENABLE_ANGEL=false\nANGEL_PIN=test-secret\n')
    monkeypatch.setenv('ANGEL_PIN', 'test-secret')
    load_dotenv(path, override=False)
    config = Config()
    assert config.timeout == 19
    assert not config.enable_angel
    assert 'test-secret' not in repr(config)


@pytest.mark.parametrize('overrides', [{'timeout': -1}, {'timeout': float('nan')},
                                     {'request_interval': -1}, {'retries': 99},
                                     {'nse_base_url': 'https://user:password@example.test'}])
def test_invalid_configuration(overrides):
    with pytest.raises(ValueError):
        Config(**overrides)


def test_paths_do_not_depend_on_scheduler_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert Config(data_dir=Path('data')).data_dir == REPO_ROOT / 'data'
