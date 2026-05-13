import importlib.util
import subprocess
from pathlib import Path


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "whisper-dictation.py"
    spec = importlib.util.spec_from_file_location("whisper_dictation", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_clipboard_paste_waits_for_new_text_before_pasting(monkeypatch):
    module = load_module()
    dictation = object.__new__(module.Dictation)
    expected = "texto dictado".encode("utf-8")
    previous = b"texto anterior"
    reads = [previous, previous, expected]
    calls = []

    def fake_run(command, input=None, capture_output=False, check=False):
        calls.append((command, input, capture_output, check))
        if command == ["xclip", "-selection", "clipboard", "-o"]:
            return subprocess.CompletedProcess(command, 0, stdout=reads.pop(0))
        return subprocess.CompletedProcess(command, 0, stdout=b"")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)

    assert dictation._try_xclip("texto dictado") is True

    paste_index = next(i for i, call in enumerate(calls) if call[0][:3] == ["xdotool", "key", "--clearmodifiers"])
    verification_reads = [i for i, call in enumerate(calls) if call[0] == ["xclip", "-selection", "clipboard", "-o"]]
    assert max(verification_reads) < paste_index


def test_clipboard_paste_falls_back_when_clipboard_never_updates(monkeypatch):
    module = load_module()
    dictation = object.__new__(module.Dictation)
    calls = []

    def fake_run(command, input=None, capture_output=False, check=False):
        calls.append(command)
        if command == ["xclip", "-selection", "clipboard", "-o"]:
            return subprocess.CompletedProcess(command, 0, stdout=b"texto anterior")
        return subprocess.CompletedProcess(command, 0, stdout=b"")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    monkeypatch.setattr(module.time, "monotonic", iter([0.0, 0.2, 0.4, 0.6, 0.8, 1.1]).__next__)

    assert dictation._try_xclip("texto dictado") is False
    assert not any(command[:3] == ["xdotool", "key", "--clearmodifiers"] for command in calls)
