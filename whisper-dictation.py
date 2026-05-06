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
import json
import os
import shutil
import subprocess
import threading
import time

# ---------- Configuración por defecto ----------
DEFAULT_KEY = "f12"
DEFAULT_MODEL = "auto"
DEFAULT_LANGUAGE = "auto"
SERVICE_NAME = "whisper-dictation"
CONFIG_PATH = os.path.expanduser("~/.config/whisper-dictation/config.json")
SAMPLE_RATE = 16000
CHANNELS = 1

INITIAL_PROMPT = (
    "Transcripción en español con términos técnicos en inglés: "
    "GitHub, issue, pull request, commit, branch, merge, API, Python, Linux, "
    "deploy, bug, feature, terminal, script, model, token, pipeline, Docker, "
    "JavaScript, TypeScript, React, Node, database, endpoint, repository."
)

_xdg_cache = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
CACHE_DIR = os.path.join(_xdg_cache, "huggingface", "hub")
# -----------------------------------------------

# ---------- Registro de modelos ----------------
MODEL_REGISTRY = {
    "tiny": {"ram_mb": 200, "quality": 1, "multilingual": True, "cpu_viable": True},
    "tiny.en": {"ram_mb": 200, "quality": 1, "multilingual": False, "cpu_viable": True},
    "base": {"ram_mb": 300, "quality": 2, "multilingual": True, "cpu_viable": True},
    "base.en": {"ram_mb": 300, "quality": 2, "multilingual": False, "cpu_viable": True},
    "small": {"ram_mb": 500, "quality": 3, "multilingual": True, "cpu_viable": True},
    "small.en": {"ram_mb": 500, "quality": 3, "multilingual": False, "cpu_viable": True},
    "medium": {"ram_mb": 1500, "quality": 4, "multilingual": True, "cpu_viable": True},
    "medium.en": {"ram_mb": 1500, "quality": 4, "multilingual": False, "cpu_viable": True},
    "large-v1": {"ram_mb": 3000, "quality": 5, "multilingual": True, "cpu_viable": False},
    "large-v2": {"ram_mb": 3000, "quality": 6, "multilingual": True, "cpu_viable": False},
    "large-v3": {"ram_mb": 3000, "quality": 7, "multilingual": True, "cpu_viable": False},
    "distil-large-v3": {"ram_mb": 1500, "quality": 6, "multilingual": True, "cpu_viable": True},
    "distil-medium.en": {"ram_mb": 800, "quality": 4, "multilingual": False, "cpu_viable": True},
    "distil-small.en": {"ram_mb": 400, "quality": 3, "multilingual": False, "cpu_viable": True},
}
# -----------------------------------------------


def notify(title, message, timeout=3):
    try:
        subprocess.Popen(
            ["kdialog", "--passivepopup", f"{message}", str(timeout), "--title", title],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass


def get_available_ram_mb():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 1000


def auto_select_model(quiet=False):
    available = get_available_ram_mb()
    usable = available * 0.75
    candidates = {
        k: v for k, v in MODEL_REGISTRY.items()
        if v["ram_mb"] <= usable and v["multilingual"] and v["cpu_viable"]
    }
    if not candidates:
        if not quiet:
            print("[Auto] RAM insuficiente para cualquier modelo, usando tiny.")
        return "tiny"
    best = max(candidates, key=lambda k: MODEL_REGISTRY[k]["quality"])
    if not quiet:
        print(f"[Auto] RAM disponible: {available} MB → modelo seleccionado: '{best}'")
    return best


def is_model_cached(model_name):
    model_dir = os.path.join(CACHE_DIR, f"models--Systran--faster-whisper-{model_name}")
    return os.path.isdir(model_dir)


def ensure_model_available(model_name):
    from faster_whisper import WhisperModel

    if not is_model_cached(model_name):
        print(f"[Whisper Dictation] Descargando modelo '{model_name}' (primera vez, puede tardar)...")
        notify("Whisper Dictation", f"⬇️ Descargando modelo '{model_name}'...", 60)
    else:
        print(f"[Whisper Dictation] Cargando modelo '{model_name}'...")
        notify("Whisper Dictation", "⏳ Cargando modelo, espera un momento...", 5)
    return WhisperModel(model_name, device="cpu", compute_type="int8")


def download_all_models():
    from faster_whisper import WhisperModel

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


def _run_command(command, timeout=0.8):
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired as exc:
        completed = subprocess.CompletedProcess(command, 124, exc.stdout or "", exc.stderr or "timeout")
        return completed


def _command_output(command, timeout=0.8):
    result = _run_command(command, timeout=timeout)
    if result is None:
        return None
    return (result.stdout or result.stderr or "").strip()


def _load_status_config():
    config = {
        "key": DEFAULT_KEY,
        "toggle": False,
        "language": DEFAULT_LANGUAGE,
        "model": DEFAULT_MODEL,
    }
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            config.update({k: data[k] for k in config if k in data})
    except (OSError, json.JSONDecodeError):
        pass
    return config


def _get_service_status():
    result = _run_command(
        ["systemctl", "--user", "show", SERVICE_NAME, "--property=ActiveState,SubState,MainPID", "--value"],
        timeout=0.8,
    )
    if result is None:
        return {"available": False, "state": "unknown", "substate": "systemctl not found", "pid": None}
    values = (result.stdout or "").splitlines()
    state = values[0].strip() if len(values) > 0 and values[0].strip() else "unknown"
    substate = values[1].strip() if len(values) > 1 and values[1].strip() else "unknown"
    pid_raw = values[2].strip() if len(values) > 2 else "0"
    try:
        pid = int(pid_raw)
    except ValueError:
        pid = 0
    return {"available": result.returncode == 0, "state": state, "substate": substate, "pid": pid or None}


def _get_session_type():
    session = os.environ.get("XDG_SESSION_TYPE")
    if session:
        return session.upper()
    if os.environ.get("WAYLAND_DISPLAY"):
        return "Wayland"
    if os.environ.get("DISPLAY"):
        return "X11"
    return "unknown"


def _get_typing_backend():
    version = _command_output(["xdotool", "--version"], timeout=0.5)
    xclip = shutil.which("xclip") is not None
    xsel = shutil.which("xsel") is not None
    if version:
        backend = "clipboard+xdotool" if xclip or xsel else "xdotool"
        return {"ok": True, "backend": backend, "xdotool": version, "xclip": xclip, "xsel": xsel}
    return {"ok": False, "backend": "missing", "xdotool": None, "xclip": xclip, "xsel": xsel}


def _get_audio_backend():
    pactl = _command_output(["pactl", "info"], timeout=0.8)
    if pactl:
        server = "unknown"
        sink = "unknown"
        source = "unknown"
        for line in pactl.splitlines():
            if line.startswith("Server Name:"):
                server = line.split(":", 1)[1].strip()
            elif line.startswith("Default Sink:"):
                sink = line.split(":", 1)[1].strip()
            elif line.startswith("Default Source:"):
                source = line.split(":", 1)[1].strip()
        return {"ok": True, "backend": "pulseaudio", "server": server, "default_sink": sink, "default_source": source}
    if shutil.which("pipewire"):
        return {"ok": True, "backend": "pipewire", "server": "pipewire", "default_sink": "unknown", "default_source": "unknown"}
    return {"ok": False, "backend": "missing", "server": None, "default_sink": None, "default_source": None}


def _get_cache_usage(path):
    if not os.path.exists(path):
        return 0
    total = 0
    for root, _, files in os.walk(path):
        for filename in files:
            try:
                total += os.path.getsize(os.path.join(root, filename))
            except OSError:
                pass
    return total


def _format_bytes(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f}{unit}" if unit == "B" else f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}GB"


def _get_last_journal_error():
    result = _run_command(
        ["journalctl", "--user", "-u", SERVICE_NAME, "--since", "24 hours ago", "-p", "err", "-n", "1", "--no-pager", "--output", "short-iso"],
        timeout=0.8,
    )
    if result is None:
        return {"available": False, "message": "journalctl not found"}
    output = (result.stdout or result.stderr or "").strip()
    if not output or "-- No entries --" in output:
        return {"available": True, "message": None}
    return {"available": True, "message": output.splitlines()[-1]}


def _get_last_activity():
    result = _run_command(
        ["journalctl", "--user", "-u", SERVICE_NAME, "-n", "1", "--no-pager", "--output", "short-iso"],
        timeout=0.8,
    )
    if result is None:
        return None
    output = (result.stdout or "").strip()
    if not output or "-- No entries --" in output:
        return None
    return output.splitlines()[-1]


def collect_status(cli_model=DEFAULT_MODEL):
    config = _load_status_config()
    configured_model = config.get("model") or cli_model or DEFAULT_MODEL
    if configured_model == "auto":
        model_name = auto_select_model(quiet=True)
    else:
        model_name = configured_model
    model_cache_dir = os.path.join(CACHE_DIR, f"models--Systran--faster-whisper-{model_name}")
    cache_bytes = _get_cache_usage(model_cache_dir)
    return {
        "service": _get_service_status(),
        "session_type": _get_session_type(),
        "model": {
            "configured": configured_model,
            "resolved": model_name,
            "cached": is_model_cached(model_name),
            "cache_path": model_cache_dir,
            "cache_bytes": cache_bytes,
            "cache_size": _format_bytes(cache_bytes),
        },
        "language": config.get("language", DEFAULT_LANGUAGE),
        "key_binding": str(config.get("key", DEFAULT_KEY)).upper(),
        "mode": "toggle" if config.get("toggle") else "hold",
        "audio_backend": _get_audio_backend(),
        "typing_backend": _get_typing_backend(),
        "dependencies": {
            "systemctl": shutil.which("systemctl") is not None,
            "journalctl": shutil.which("journalctl") is not None,
            "xdotool": shutil.which("xdotool") is not None,
            "xclip": shutil.which("xclip") is not None,
            "xsel": shutil.which("xsel") is not None,
            "pactl": shutil.which("pactl") is not None,
            "pipewire": shutil.which("pipewire") is not None,
        },
        "last_error": _get_last_journal_error(),
        "last_activity": _get_last_activity(),
    }


def _ok(value):
    return "✅" if value else "❌"


def print_status(report, json_output=False):
    if json_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    service = report["service"]
    model = report["model"]
    audio = report["audio_backend"]
    typing = report["typing_backend"]
    last_error = report["last_error"].get("message") or "none"
    pid = f" PID {service['pid']}" if service.get("pid") else ""
    model_cache = f"cached at {model['cache_path']}" if model["cached"] else "not cached"
    audio_device = audio.get("default_source") or audio.get("default_sink") or "unknown"

    print("whisper-ptt status")
    print("=====================================")
    print(f"service:        {service['state']} ({service['substate']}){pid}")
    print(f"session type:   {report['session_type']}")
    print(f"model:          {model['resolved']} ({model_cache})")
    print(f"language:       {report['language']}")
    print(f"key binding:    {report['key_binding']} ({report['mode']})")
    print(f"mode:           {report['mode']}")
    print(f"audio backend:  {_ok(audio['ok'])} {audio['backend']} (default device: {audio_device})")
    print(f"xdotool:        {_ok(typing['ok'])} {typing['xdotool'] or 'missing'}")
    print(f"typing backend: {typing['backend']}")
    print(f"disk usage:     model cache {model['cache_size']}")
    print(f"last error:     {last_error}")
    print(f"last activity:  {report['last_activity'] or 'none'}")
    missing = [name for name, present in report["dependencies"].items() if not present]
    print(f"dependencies:   {'ok' if not missing else 'missing ' + ', '.join(missing)}")


class Dictation:
    def __init__(self, model_name, language, toggle_mode):
        self.model = ensure_model_available(model_name)
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
        import numpy as np

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

        model_quality = MODEL_REGISTRY.get(self.model_name, {}).get("quality", 4)
        prompt = INITIAL_PROMPT if model_quality <= 3 else None

        segments, _ = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt=prompt,
            temperature=0.0,
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
        if self._try_xclip(text):
            return
        if self._try_xsel(text):
            return
        self._fallback_xdotool(text)

    def _try_xclip(self, text):
        try:
            prev = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True)
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode("utf-8"), check=True)
            try:
                subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+shift+v"], check=True)
            except subprocess.CalledProcessError:
                subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+v"], check=True)
            time.sleep(0.1)
            if prev.returncode == 0:
                subprocess.run(["xclip", "-selection", "clipboard"], input=prev.stdout, check=False)
            return True
        except FileNotFoundError:
            return False
        except subprocess.CalledProcessError:
            return False

    def _try_xsel(self, text):
        try:
            prev = subprocess.run(["xsel", "--clipboard", "--output"], capture_output=True)
            subprocess.run(["xsel", "--clipboard", "--input"], input=text.encode("utf-8"), check=True)
            subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+v"], check=True)
            time.sleep(0.1)
            if prev.returncode == 0:
                subprocess.run(["xsel", "--clipboard", "--input"], input=prev.stdout, check=False)
            return True
        except FileNotFoundError:
            return False
        except subprocess.CalledProcessError:
            return False

    def _fallback_xdotool(self, text):
        print("[!] xclip y xsel no disponibles. Usando xdotool type (puede perder tildes).")
        notify("⚠️ Dictado", "xclip/xsel no instalados — tildes pueden perderse", 5)
        try:
            subprocess.run(["xdotool", "type", "--clearmodifiers", "--delay", "0", "--", text], check=True)
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
    parser.add_argument("--status", action="store_true",
                        help="Muestra diagnóstico del servicio, modelo, sesión, audio, xdotool y último error del journal.")
    parser.add_argument("--json", action="store_true",
                        help="Con --status, emite el diagnóstico en JSON parseable.")
    args = parser.parse_args()

    if args.status:
        report = collect_status(args.model)
        print_status(report, json_output=args.json)
        return

    if args.download_all:
        download_all_models()
        return

    model_name = auto_select_model() if args.model == "auto" else args.model
    language = None if args.language == "auto" else args.language

    import sounddevice as sd
    from pynput import keyboard

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
