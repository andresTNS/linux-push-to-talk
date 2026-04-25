#!/usr/bin/env python3
import subprocess

SERVICE_NAME = "whisper-dictation"


def run_systemctl(*args):
    return subprocess.run(
        ["systemctl", "--user", *args, SERVICE_NAME],
        capture_output=True,
        text=True,
    )


def get_service_status():
    result = run_systemctl("is-active")
    status = (result.stdout or result.stderr).strip()
    return status or "unknown"


def start_service():
    return run_systemctl("start")


def stop_service():
    return run_systemctl("stop")


def restart_service():
    return run_systemctl("restart")


def tail_service_logs(lines=20):
    result = subprocess.run(
        ["journalctl", "--user", "-u", SERVICE_NAME, "-n", str(lines), "--no-pager"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or result.stderr.strip()
