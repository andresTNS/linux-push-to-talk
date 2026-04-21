#!/usr/bin/env python3
"""
Push-to-talk dictation para Linux X11 + KDE.
Mantén presionada F12 para grabar. Al soltar, transcribe y escribe.

Uso:
  python3 whisper-dictation.py            # Tecla por defecto: F12
  python3 whisper-dictation.py --key F10  # Cambiar tecla
  python3 whisper-dictation.py --toggle   # Modo toggle
  python3 whisper-dictation.py --model medium  # Modelo más preciso
"""

import argparse
import subprocess
import threading
import time
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput import keyboard

# ---------- Configuración por defecto ----------
DEFAULT_KEY      = "f12"
DEFAULT_MODEL    = "base"   # tiny | base | small | medium | large-v3
DEFAULT_LANGUAGE = "es"     # None = autodetección
SAMPLE_RATE      = 16000
CHANNELS         = 1
# -----------------------------------------------

def notify(title, message, timeout=3):
    """Notificación visual en KDE (no bloqueante)."""
    try:
        subprocess.Popen(
            ["kdialog", "--passivepopup", f"{message}", str(timeout),
             "--title", title],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass  # Si kdialog no está disponible, continúa sin notificación


class Dictation:
    def __init__(self, model_name, language, toggle_mode):
        print(f"[Whisper Dictation] Cargando modelo '{model_name}'...")
        notify("Whisper Dictation", "⏳ Cargando modelo, espera un momento...", 5)
        self.model = WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
        )
        self.language = language
        self.toggle_mode = toggle_mode
        self.recording = False
        self.audio_frames = []
        self.lock = threading.Lock()
        print(f"[Whisper Dictation] Listo. Idioma: {language or 'auto'}")
        notify("Whisper Dictation", "✅ Listo — mantén F12 para dictar", 4)

    def start_recording(self):
        with self.lock:
            if self.recording:
                return
            self.recording = True
            self.audio_frames = []
        print("[●] Grabando...", flush=True)
        notify("🎙 Dictado", "Grabando... suelta F12 para transcribir", 30)
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

        segments, info = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
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
        # Pausa para que F12 se suelte antes de escribir
        time.sleep(0.15)
        try:
            subprocess.run(
                ["xdotool", "type", "--clearmodifiers", "--delay", "0", "--", text],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"[Error xdotool] {e}")
        except FileNotFoundError:
            print("[Error] xdotool no encontrado. Instalar con: sudo apt install xdotool")


def main():
    parser = argparse.ArgumentParser(description="Push-to-talk dictation con Whisper")
    parser.add_argument("--key", default=DEFAULT_KEY,
                        help=f"Tecla para activar (default: {DEFAULT_KEY})")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        help=f"Modelo Whisper (default: {DEFAULT_MODEL})")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE,
                        help="Código de idioma ISO (es, en, fr...) o 'auto'")
    parser.add_argument("--toggle", action="store_true",
                        help="Modo toggle: presionar una vez inicia, presionar de nuevo detiene")
    args = parser.parse_args()

    language = None if args.language == "auto" else args.language
    dictation = Dictation(args.model, language, args.toggle)

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

        if key_name == args.key.lower():
            if pressed:
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
