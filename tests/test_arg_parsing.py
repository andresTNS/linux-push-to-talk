import importlib.util
import sys
import types
from pathlib import Path


def load_dictation_module(monkeypatch):
    monkeypatch.setitem(sys.modules, "numpy", types.SimpleNamespace(concatenate=lambda frames, axis=0: frames))
    monkeypatch.setitem(sys.modules, "sounddevice", types.SimpleNamespace(InputStream=object))
    monkeypatch.setitem(
        sys.modules,
        "faster_whisper",
        types.SimpleNamespace(WhisperModel=lambda *args, **kwargs: object()),
    )
    keyboard_stub = types.SimpleNamespace(Listener=object)
    monkeypatch.setitem(sys.modules, "pynput", types.SimpleNamespace(keyboard=keyboard_stub))
    monkeypatch.setitem(sys.modules, "pynput.keyboard", keyboard_stub)

    module_path = Path(__file__).resolve().parents[1] / "whisper-dictation.py"
    spec = importlib.util.spec_from_file_location("whisper_dictation", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ListenerStub:
    def __init__(self, on_press=None, on_release=None):
        self.on_press = on_press
        self.on_release = on_release

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def join(self):
        return None


def test_download_all_flag_exits_before_starting_listener(monkeypatch):
    module = load_dictation_module(monkeypatch)
    called = {"download_all": False}

    def fake_download_all_models():
        called["download_all"] = True

    monkeypatch.setattr(module, "download_all_models", fake_download_all_models)
    monkeypatch.setattr(sys, "argv", ["whisper-dictation.py", "--download-all"])

    module.main()

    assert called["download_all"] is True


def test_main_parses_key_model_language_and_toggle(monkeypatch):
    module = load_dictation_module(monkeypatch)
    created = {}

    class DictationStub:
        def __init__(self, model_name, language, toggle_mode):
            created.update(model_name=model_name, language=language, toggle_mode=toggle_mode)

        def start_recording(self):
            raise AssertionError("listener should not invoke recording during argument parsing")

        def stop_and_transcribe(self):
            raise AssertionError("listener should not invoke transcription during argument parsing")

    monkeypatch.setattr(module, "Dictation", DictationStub)
    keyboard_stub = types.SimpleNamespace(Listener=ListenerStub)
    monkeypatch.setitem(sys.modules, "pynput", types.SimpleNamespace(keyboard=keyboard_stub))
    monkeypatch.setitem(sys.modules, "pynput.keyboard", keyboard_stub)
    monkeypatch.setattr(
        sys,
        "argv",
        ["whisper-dictation.py", "--key", "F10", "--model", "small", "--language", "auto", "--toggle"],
    )

    module.main()

    assert created == {"model_name": "small", "language": None, "toggle_mode": True}


def test_auto_model_is_resolved_before_dictation_is_created(monkeypatch):
    module = load_dictation_module(monkeypatch)
    created = {}

    class DictationStub:
        def __init__(self, model_name, language, toggle_mode):
            created["model_name"] = model_name

    monkeypatch.setattr(module, "auto_select_model", lambda: "distil-large-v3")
    monkeypatch.setattr(module, "Dictation", DictationStub)
    keyboard_stub = types.SimpleNamespace(Listener=ListenerStub)
    monkeypatch.setitem(sys.modules, "pynput", types.SimpleNamespace(keyboard=keyboard_stub))
    monkeypatch.setitem(sys.modules, "pynput.keyboard", keyboard_stub)
    monkeypatch.setattr(sys, "argv", ["whisper-dictation.py", "--model", "auto"])

    module.main()

    assert created["model_name"] == "distil-large-v3"
