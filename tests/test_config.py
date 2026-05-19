import importlib.util
from pathlib import Path


def config_module(monkeypatch, tmp_path):
    module_path = Path(__file__).resolve().parents[1] / "frontend_config.py"
    spec = importlib.util.spec_from_file_location("frontend_config", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "CONFIG_DIR", tmp_path / "whisper-dictation")
    monkeypatch.setattr(module, "CONFIG_PATH", tmp_path / "whisper-dictation" / "config.json")
    return module


def test_load_config_returns_defaults_when_file_is_missing(monkeypatch, tmp_path):
    module = config_module(monkeypatch, tmp_path)

    assert module.load_config() == module.DEFAULT_CONFIG


def test_save_config_creates_parent_directory_and_round_trips(monkeypatch, tmp_path):
    module = config_module(monkeypatch, tmp_path)
    config = {"key": "f10", "toggle": True, "language": "auto", "model": "small", "stt_provider": "groq"}

    module.save_config(config)

    assert module.CONFIG_PATH.exists()
    assert module.load_config() == config


def test_load_config_merges_partial_config_with_defaults(monkeypatch, tmp_path):
    module = config_module(monkeypatch, tmp_path)
    module.CONFIG_DIR.mkdir(parents=True)
    module.CONFIG_PATH.write_text('{"key": "f9"}\n')

    assert module.load_config() == {**module.DEFAULT_CONFIG, "key": "f9"}


def test_load_config_falls_back_to_defaults_for_invalid_json(monkeypatch, tmp_path):
    module = config_module(monkeypatch, tmp_path)
    module.CONFIG_DIR.mkdir(parents=True)
    module.CONFIG_PATH.write_text("not-json")

    assert module.load_config() == module.DEFAULT_CONFIG
