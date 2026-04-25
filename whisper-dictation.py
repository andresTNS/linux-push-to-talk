#!/usr/bin/env python3
"""
Push-to-talk dictation para Linux X11 + KDE.
Mantén presionada F12 para grabar. Al soltar, transcribe y escribe.
"""

import argparse
import subprocess
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput import keyboard

DEFAULT_KEY = "f12"
DEFAULT_MODEL = "base"
DEFAULT_LANGUAGE = "es"
SAMPLE_RATE = 16000
CHANNELS = 1
MODEL_REGISTRY = [
    "tiny", "tiny.en",
    "base", "base.en",
    "small", "small.en",
    "medium", "medium.en",
    "large-v1", "large-v2", "large-v3", "large-v3-turbo",
    "distil-small.en", "distil-medium.en", "distil-large-v2", "distil-large-v3",
]
MODEL_CACHE_DIR = Path.home() / ".cache" / "huggingface" / "hub"


def notify(title, message, timeout=3):
    try:
        subprocess.Popen(
            ["kdialog", "--passivepopup", f"{message}", str(timeout), "--title", title],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass


def ensure_model_available(model_name, language):
    notify("Whisper Dictation", f"⏳ Verificando modelo {model_name}...", 3)
    if not any(model_name in p.name for p in MODEL_CACHE_DIR.glob("**/*")):
        notify("Whisper Dictation", f"⬇️ Descargando modelo {model_name}...", 8)
    compute_type = "int8"
    if language == "auto" and not model_name.endswith(".en"):
        compute_type = "int8"
    return WhisperModel(model_name, device="cpu", compute_type=compute_type)


def download_all_models():
    for model_name in MODEL_REGISTRY:
        print(f"[Whisper Dictation] Descargando {model_name}...")
        ensure_model_available(model_name, None)
    print("[Whisper Dictation] Todos los modelos registrados quedaron descargados.")


class Dictation:
    def __init__(self, model_name, language, toggle_mode):
        print(f"[Whisper Dictation] Cargando modelo '{model_name}'...")
        notify("Whisper Dictation", "⏳ Cargando modelo, espera un momento...", 5)
        self.model = ensure_model_available(model_name, language)
        self.language = None if language == "auto" else language
        self.toggle_mode = toggle_mode
        self.recording = False
        self.audio_frames = []
        self.lock = threading.Lock()
        print(f"[Whisper Dictation] Listo. Idioma: {self.language or 'auto'}")
        notify("Whisper Dictation", "✅ Listo — mantén F12 para dictar", 4)

    def start_recording(self):
        with self.lock:
            if self.recording:
                return
            self.recording = True
            self.audio_frames = []
        print("[●] Grabando...", flush=True)
        notify("🎙 Dictado", "Grabando... suelta la tecla para transcribir", 30)
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            callback=self._audio_callback,
        )
        self._stream.start()

    def _audio_callback(self, indata, frames, time_info, status):
        with self.lock:
            if self.recording:
                self.audio_frames.append(indata.copy())

    def stop_and_transcribe(self):
        with self.lock:
            if not self.recording:
                return
            self.recording = False
        self._stream.stop()
        self._stream.close()
        print("[■] Procesando...", flush=True)
        notify("🎙 Dictado", "⏳ Procesando audio...", 10)

        if not self.audio_frames:
            print("[!] Sin audio grabado.")
            notify("🎙 Dictado", "⚠️ Sin audio grabado", 3)
            return

        audio = np.concatenate(self.audio_frames, axis=0).flatten()
        if len(audio) < SAMPLE_RATE * 0.5:
            print("[!] Grabación muy corta, ignorada.")
            notify("🎙 Dictado", "⚠️ Grabación muy corta, ignorada", 3)
            return

        segments, _ = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            condition_on_previous_text=False,
        )

        text = " ".join(seg.text for seg in segments).strip()
        if text:
            print(f'[✓] "{text}"', flush=True)
            notify("✅ Transcripción", text, 5)
            self._type_text(text)
        else:
            print("[!] No se detectó habla.")
            notify("🎙 Dictado", "⚠️ No se detectó habla", 3)

    def _type_text(self, text):
        time.sleep(0.15)
        commands = [
            ["xdotool", "type", "--clearmodifiers", "--delay", "0", "--", text],
            ["bash", "-lc", f"printf %s {text!r} | xclip -selection clipboard && xdotool key --clearmodifiers ctrl+shift+v"],
            ["bash", "-lc", f"printf %s {text!r} | xclip -selection clipboard && xdotool key --clearmodifiers ctrl+v"],
        ]
        for command in commands:
            try:
                subprocess.run(command, check=True)
                return
            except Exception:
                continue
        print("[Error] No se pudo escribir el texto con xdotool/xclip")


def main():
    parser = argparse.ArgumentParser(description="Push-to-talk dictation con Whisper")
    parser.add_argument("--key", default=DEFAULT_KEY, help=f"Tecla para activar (default: {DEFAULT_KEY})")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=MODEL_REGISTRY, help=f"Modelo Whisper (default: {DEFAULT_MODEL})")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="Código de idioma ISO (es, en, fr...) o 'auto'")
    parser.add_argument("--toggle", action="store_true", help="Modo toggle: presionar una vez inicia, presionar de nuevo detiene")
    parser.add_argument("--download-all", action="store_true", help="Descarga previamente todos los modelos registrados")
    args = parser.parse_args()

    if args.download_all:
        download_all_models()
        return

    dictation = Dictation(args.model, args.language, args.toggle)

    mode = "toggle" if args.toggle else "mantener presionada"
    print(f"[Whisper Dictation] Tecla activa: {args.key.upper()} ({mode})")
    print("[Whisper Dictation] Ctrl+C para salir\n")

    pressed = False

    def on_press(key):
        nonlocal pressed
        try:
            key_name = key.name if hasattr(key, "name") else key.char
        except AttributeError:
            return
        if key_name == args.key.lower():
            if args.toggle:
                if not pressed:
                    pressed = True
                    dictation.start_recording()
                else:
                    pressed = False
                    threading.Thread(target=dictation.stop_and_transcribe, daemon=True).start()
            else:
                if not pressed:
                    pressed = True
                    dictation.start_recording()

    def on_release(key):
        nonlocal pressed
        if args.toggle:
            return
        try:
            key_name = key.name if hasattr(key, "name") else key.char
        except AttributeError:
            return
        if key_name == args.key.lower() and pressed:
            pressed = False
            threading.Thread(target=dictation.stop_and_transcribe, daemon=True).start()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            print("\n[Whisper Dictation] Saliendo.")
            notify("Whisper Dictation", "🔴 Servicio detenido", 3)


if __name__ == "__main__":
    main()
