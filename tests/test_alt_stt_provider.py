import importlib.util
import pathlib

import numpy as np

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "whisper-dictation.py"


def load_module():
    spec = importlib.util.spec_from_file_location("whisper_dictation", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_audio_to_wav_bytes_has_riff_header():
    m = load_module()
    audio = np.zeros(1600, dtype=np.float32)
    wav_bytes = m._audio_to_wav_bytes(audio, 16000)
    assert wav_bytes[:4] == b"RIFF"
    assert b"WAVE" in wav_bytes[:16]


def test_multipart_body_contains_fields_and_file():
    m = load_module()
    boundary, body = m._multipart_body(
        {"model": "whisper-large-v3-turbo"},
        {"file": ("a.wav", b"123", "audio/wav")},
    )
    assert boundary
    assert b'Content-Disposition: form-data; name="model"' in body
    assert b'Content-Disposition: form-data; name="file"; filename="a.wav"' in body
    assert b"audio/wav" in body


def test_groq_without_key_raises_runtime_error(monkeypatch):
    m = load_module()
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    audio = np.zeros(1600, dtype=np.float32)
    try:
        m.transcribe_with_groq(audio, 16000, None)
    except RuntimeError as exc:
        assert "GROQ_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError when GROQ_API_KEY is missing")
