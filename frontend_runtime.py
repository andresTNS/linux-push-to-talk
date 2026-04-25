#!/usr/bin/env python3
import fcntl
import os
import subprocess
from pathlib import Path

from frontend_config import CONFIG_PATH, DEFAULT_CONFIG, load_config

LOCK_PATH = Path.home() / ".local" / "share" / "whisper-dictation" / "frontend.lock"
PID_PATH = Path.home() / ".local" / "share" / "whisper-dictation" / "frontend.pid"
AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_PATH = AUTOSTART_DIR / "whisper-ptt-gui.desktop"

_lock_handle = None


def acquire_single_instance_lock():
    global _lock_handle
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    _lock_handle = LOCK_PATH.open("w")
    try:
        fcntl.flock(_lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    PID_PATH.write_text(f"{os.getpid()}\n")
    return True


def ensure_autostart_entry():
    AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
    AUTOSTART_PATH.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=whisper-ptt GUI\n"
        f"Exec={Path.home() / '.local' / 'bin' / 'whisper-ptt-gui'}\n"
        "X-GNOME-Autostart-enabled=true\n"
        "Terminal=false\n"
        "Categories=Utility;AudioVideo;\n"
    )


def build_runtime_command(config=None):
    cfg = config or load_config()
    command = [str(Path.home() / ".local" / "bin" / "dictate")]
    command.extend(["--key", cfg.get("key", DEFAULT_CONFIG["key"])])
    command.extend(["--model", cfg.get("model", DEFAULT_CONFIG["model"])])
    command.extend(["--language", cfg.get("language", DEFAULT_CONFIG["language"])])
    if cfg.get("toggle", DEFAULT_CONFIG["toggle"]):
        command.append("--toggle")
    return command


def get_runtime_command_preview():
    return " ".join(build_runtime_command())


def sync_service_unit(config=None):
    command = build_runtime_command(config)
    service_path = Path.home() / ".config" / "systemd" / "user" / "whisper-dictation.service"
    if not service_path.exists():
        return False, "Servicio systemd no encontrado"

    service_text = service_path.read_text()
    exec_line = f"ExecStart={' '.join(command)}"
    lines = service_text.splitlines()
    updated = []
    replaced = False
    for line in lines:
        if line.startswith("ExecStart="):
            updated.append(exec_line)
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        updated.append(exec_line)

    service_path.write_text("\n".join(updated) + "\n")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    return True, exec_line


def read_runtime_snapshot():
    config = load_config()
    service_path = Path.home() / ".config" / "systemd" / "user" / "whisper-dictation.service"
    exec_line = None
    if service_path.exists():
        for line in service_path.read_text().splitlines():
            if line.startswith("ExecStart="):
                exec_line = line[len("ExecStart="):]
                break
    return {
        "config": config,
        "service_exec": exec_line,
        "config_path": str(CONFIG_PATH),
        "autostart_path": str(AUTOSTART_PATH),
    }
