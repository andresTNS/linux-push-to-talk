#!/usr/bin/env python3
"""
Push-to-talk dictation para Linux X11 + KDE.
Mantén presionada F12 para grabar. Al soltar, transcribe y escribe.

Uso:
  python3 whisper-dictation.py                   # Modelo automático según RAM
  python3 whisper-dictation.py --key F10         # Cambiar tecla
  python3 whisper-dictation.py --toggle          # Modo toggle
  python3 whisper-dictation.py --model medium    # Modelo específico
  python3 whisper-dictation.py --download-all    # Predescargar todos los modelos
"""

import argparse
import os
import subprocess
import threading
import time
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput import keyboard

# ---------- Configuración por defecto ----------
DEFAULT_KEY      = "f12"
DEFAULT_MODEL    = "auto"   # auto = mejor modelo según RAM disponible
DEFAULT_LANGUAGE = "auto"   # auto = detección por segmento (soporta code-switching)
SAMPLE_RATE      = 16000
CHANNELS         = 1

# Usado solo en modelos con quality <= 3 (tiny, base, small) que tienen capacidad
# multilingüe limitada. En modelos medianos y grandes el code-switching funciona
# nativamente y el prompt introduciría sesgo innecesario.
INITIAL_PROMPT = (
    "Transcripción en español con términos técnicos en inglés: "
    "GitHub, issue, pull request, commit, branch, merge, API, Python, Linux, "
    "deploy, bug, feature, terminal, script, model, token, pipeline, Docker, "
    "JavaScript, TypeScript, React, Node, database, endpoint, repository."
)

# Directorio de caché de HuggingFace — respeta XDG_CACHE_HOME (KDE usa ~/.cachekde)
_xdg_cache = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
CACHE_DIR = os.path.join(_xdg_cache, "huggingface", "hub")
# -----------------------------------------------

# ---------- Registro de modelos ----------------
# Todos los modelos faster-whisper con requisitos de RAM y nivel de calidad.
# Solo los multilingual=True son candidatos para auto-selección.
MODEL_REGISTRY = {
    # cpu_viable=False: modelos demasiado lentos en CPU puro (>60s por dictado)
    "tiny":             {"ram_mb": 200,  "quality": 1, "multilingual": True,  "cpu_viable": True},
    "tiny.en":          {"ram_mb": 200,  "quality": 1, "multilingual": False, "cpu_viable": True},
    "base":             {"ram_mb": 300,  "quality": 2, "multilingual": True,  "cpu_viable": True},
    "base.en":          {"ram_mb": 300,  "quality": 2, "multilingual": False, "cpu_viable": True},
    "small":            {"ram_mb": 500,  "quality": 3, "multilingual": True,  "cpu_viable": True},
    "small.en":         {"ram_mb": 500,  "quality": 3, "multilingual": False, "cpu_viable": True},
    "medium":           {"ram_mb": 1500, "quality": 4, "multilingual": True,  "cpu_viable": True},
    "medium.en":        {"ram_mb": 1500, "quality": 4, "multilingual": False, "cpu_viable": True},
    "large-v1":         {"ram_mb": 3000, "quality": 5, "multilingual": True,  "cpu_viable": False},
    "large-v2":         {"ram_mb": 3000, "quality": 6, "multilingual": True,  "cpu_viable": False},
    "large-v3":         {"ram_mb": 3000, "quality": 7, "multilingual": True,  "cpu_viable": False},
    "distil-large-v3":  {"ram_mb": 1500, "quality": 6, "multilingual": True,  "cpu_viable": True},
    "distil-medium.en": {"ram_mb": 800,  "quality": 4, "multilingual": False, "cpu_viable": True},
    "distil-small.en":  {"ram_mb": 400,  "quality": 3, "multilingual": False, "cpu_viable": True},
}
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
        pass


def get_available_ram_mb():
    """Lee la RAM disponible del sistema desde /proc/meminfo."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 1000  # fallback conservador


def auto_select_model():
    """Elige el mejor modelo multilingüe y viable en CPU según RAM disponible."""
    available = get_available_ram_mb()
    usable = available * 0.75
    candidates = {
        k: v for k, v in MODEL_REGISTRY.items()
        if v["ram_mb"] <= usable and v["multilingual"] and v["cpu_viable"]
    }
    if not candidates:
        print("[Auto] RAM insuficiente para cualquier modelo, usando tiny.")
        return "tiny"
    best = max(candidates, key=lambda k: MODEL_REGISTRY[k]["quality"])
    print(f"[Auto] RAM disponible: {available} MB → modelo seleccionado: '{best}'")
    return best


def is_model_cached(model_name):
    """Verifica si el modelo ya está descargado en caché local."""
    model_dir = os.path.join(CACHE_DIR, f"models--Systran--faster-whisper-{model_name}")
    return os.path.isdir(model_dir)


def download_all_models():
    """Descarga todos los modelos del registry que no estén en caché."""
    print("[⬇] Iniciando descarga de todos los modelos...")
    notify("Whisper Dictation", "⬇️ Descargando todos los modelos...", 10)
    for model_name in MODEL_REGISTRY:
        if is_model_cached(model_name):
            print(f"[✓] {model_name} — ya en caché, omitido.")
            continue
        print(f"[⬇] Descargando '{model_name}'...")
        notify("Whisper Dictation", f"⬇️ Descargando {model_name}...", 30)
        WhisperModel(model_name, device="cpu", compute_type="int8")
        print(f"[✓] '{model_name}' descargado.")
    print("[✓] Todos los modelos están disponibles.")
    notify("Whisper Dictation", "✅ Todos los modelos descargados.", 5)


class Dictation:
    def __init__(self, model_name, language, toggle_mode):
        if not is_model_cached(model_name):
            print(f"[Whisper Dictation] Descargando modelo '{model_name}' (primera vez, puede tardar)...")
            notify("Whisper Dictation", f"⬇️ Descargando modelo '{model_name}'...", 60)
        else:
            print(f"[Whisper Dictation] Cargando modelo '{model_name}'...")
            notify("Whisper Dictation", "⏳ Cargando modelo, espera un momento...", 5)

        self.model = WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
        )
        self.model_name = model_name
        self.language = language
        self.toggle_mode = toggle_mode
        self.recording = False
        self.audio_frames = []
        self.lock = threading.Lock()
        lang_display = language if language else "auto (multilingüe)"
        print(f"[Whisper Dictation] Listo. Modelo: {model_name} | Idioma: {lang_display}")
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

        # INITIAL_PROMPT solo para modelos pequeños (quality <= 3)
        model_quality = MODEL_REGISTRY.get(self.model_name, {}).get("quality", 4)
        prompt = INITIAL_PROMPT if model_quality <= 3 else None

        segments, info = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt=prompt,
            temperature=0.0,
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
        """Escribe el texto usando la mejor herramienta disponible."""
        time.sleep(0.15)
        if self._try_xclip(text):
            return
        if self._try_xsel(text):
            return
        self._fallback_xdotool(text)

    def _try_xclip(self, text):
        """Escribe vía xclip + Ctrl+V, guardando y restaurando el portapapeles."""
        try:
            prev = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True,
            )
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text.encode("utf-8"),
                check=True,
            )
            subprocess.run(
                ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                check=True,
            )
            time.sleep(0.1)
            if prev.returncode == 0:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=prev.stdout,
                    check=False,
                )
            return True
        except FileNotFoundError:
            return False
        except subprocess.CalledProcessError:
            return False

    def _try_xsel(self, text):
        """Escribe vía xsel + Ctrl+V, guardando y restaurando el portapapeles."""
        try:
            prev = subprocess.run(
                ["xsel", "--clipboard", "--output"],
                capture_output=True,
            )
            subprocess.run(
                ["xsel", "--clipboard", "--input"],
                input=text.encode("utf-8"),
                check=True,
            )
            subprocess.run(
                ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                check=True,
            )
            time.sleep(0.1)
            if prev.returncode == 0:
                subprocess.run(
                    ["xsel", "--clipboard", "--input"],
                    input=prev.stdout,
                    check=False,
                )
            return True
        except FileNotFoundError:
            return False
        except subprocess.CalledProcessError:
            return False

    def _fallback_xdotool(self, text):
        """Último recurso: xdotool type. Puede perder tildes y caracteres especiales."""
        print("[!] xclip y xsel no disponibles. Usando xdotool type (puede perder tildes).")
        notify("⚠️ Dictado", "xclip/xsel no instalados — tildes pueden perderse", 5)
        try:
            subprocess.run(
                ["xdotool", "type", "--clearmodifiers", "--delay", "0", "--", text],
                check=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            print(f"[Error] No se pudo escribir el texto: {e}")


def main():
    parser = argparse.ArgumentParser(description="Push-to-talk dictation con Whisper")
    parser.add_argument("--key", default=DEFAULT_KEY,
                        help=f"Tecla para activar (default: {DEFAULT_KEY})")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        choices=["auto"] + list(MODEL_REGISTRY.keys()),
                        help="Modelo Whisper a usar. 'auto' selecciona el mejor según RAM disponible.")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE,
                        help="Código ISO del idioma (es, en, fr...) o 'auto' para detección multilingüe.")
    parser.add_argument("--toggle", action="store_true",
                        help="Modo toggle: presionar una vez inicia, presionar de nuevo detiene.")
    parser.add_argument("--download-all", action="store_true",
                        help="Descarga todos los modelos del registro y sale.")
    args = parser.parse_args()

    if args.download_all:
        download_all_models()
        return

    model_name = auto_select_model() if args.model == "auto" else args.model
    language = None if args.language == "auto" else args.language

    dictation = Dictation(model_name, language, args.toggle)

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
