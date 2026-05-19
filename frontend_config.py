#!/usr/bin/env python3
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "whisper-dictation"
CONFIG_PATH = CONFIG_DIR / "config.json"
DEFAULT_CONFIG = {
    "key": "f12",
    "toggle": False,
    "language": "es",
    "model": "auto",
    "stt_provider": "local",
}


def load_config():
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return DEFAULT_CONFIG.copy()
    return {**DEFAULT_CONFIG, **data}


def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")
