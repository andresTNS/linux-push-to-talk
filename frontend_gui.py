#!/usr/bin/env python3
import os
import queue
import socket
import tempfile
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from frontend_config import load_config, save_config
from frontend_service import (
    get_service_status,
    restart_service,
    start_service,
    stop_service,
    tail_service_logs,
)

MODELS = ["auto", "tiny", "base", "small", "medium", "large-v3"]
LANGUAGES = ["es", "en", "auto"]
STT_PROVIDERS = ["local", "groq"]
INSTANCE_SOCKET = os.path.join(
    os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir(),
    f"whisper-ptt-gui-{os.getuid()}.sock",
)


def focus_existing_instance():
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(0.2)
        client.connect(INSTANCE_SOCKET)
        client.sendall(b"show")
        client.close()
        return True
    except OSError:
        try:
            os.unlink(INSTANCE_SOCKET)
        except FileNotFoundError:
            pass
        return False


class SingleInstanceServer:
    def __init__(self, app):
        self.app = app
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(INSTANCE_SOCKET)
        self.sock.listen(1)
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
                data = conn.recv(32)
                conn.close()
            except OSError:
                return
            if data.startswith(b"show"):
                self.app.root.after(0, self.app.show_window)

    def close(self):
        try:
            self.sock.close()
        finally:
            try:
                os.unlink(INSTANCE_SOCKET)
            except FileNotFoundError:
                pass


class TrayController:
    def __init__(self, app):
        self.app = app
        self.icon = None
        self.available = False
        try:
            import pystray
            from PIL import Image, ImageDraw
        except ImportError:
            return

        image = Image.new("RGB", (64, 64), "#1f2937")
        draw = ImageDraw.Draw(image)
        draw.ellipse((14, 8, 50, 44), fill="#22c55e")
        draw.rectangle((28, 42, 36, 54), fill="#22c55e")
        draw.rectangle((20, 54, 44, 59), fill="#22c55e")
        self.icon = pystray.Icon(
            "whisper-ptt",
            image,
            "whisper-ptt",
            menu=pystray.Menu(
                pystray.MenuItem("Mostrar", lambda: self.app.root.after(0, self.app.show_window), default=True),
                pystray.MenuItem("Reiniciar servicio", lambda: self.app._service_action(restart_service)),
                pystray.MenuItem("Salir", lambda: self.app.root.after(0, self.app.quit_app)),
            ),
        )
        self.available = True

    def start(self):
        if self.icon:
            threading.Thread(target=self.icon.run, daemon=True).start()

    def stop(self):
        if self.icon:
            self.icon.stop()


class WhisperFrontendApp:
    def __init__(self, root):
        self.root = root
        self.root.title("whisper-ptt frontend")
        self.root.geometry("760x600")
        self.queue = queue.Queue()
        self.config = load_config()
        self.status_var = tk.StringVar(value="Cargando estado...")
        self.mic_var = tk.StringVar(value="Micrófono: inactivo")
        self.log_var = tk.StringVar(value="Cargando logs...")

        self.key_var = tk.StringVar(value=self.config["key"])
        self.toggle_var = tk.BooleanVar(value=self.config["toggle"])
        self.language_var = tk.StringVar(value=self.config["language"])
        self.model_var = tk.StringVar(value=self.config["model"])
        self.stt_provider_var = tk.StringVar(value=self.config.get("stt_provider", "local"))

        self.instance_server = SingleInstanceServer(self)
        self.tray = TrayController(self)
        self.tray.start()
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        self._build_ui()
        self._refresh_async()
        self._poll_queue()

    def _build_ui(self):
        header = ttk.Frame(self.root, padding=12)
        header.pack(fill="x")
        ttk.Label(header, text="whisper-ptt", font=("TkDefaultFont", 16, "bold")).pack(anchor="w")
        ttk.Label(header, textvariable=self.status_var).pack(anchor="w", pady=(4, 0))
        ttk.Label(header, textvariable=self.mic_var).pack(anchor="w")
        tray_text = (
            "Icono de bandeja activo" if self.tray.available else "Bandeja no disponible (pystray/pillow faltante)"
        )
        ttk.Label(header, text=tray_text).pack(anchor="w")

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)
        status_tab = ttk.Frame(notebook, padding=12)
        config_tab = ttk.Frame(notebook, padding=12)
        logs_tab = ttk.Frame(notebook, padding=12)
        notebook.add(status_tab, text="Estado")
        notebook.add(config_tab, text="Configuración")
        notebook.add(logs_tab, text="Logs")
        self._build_status_tab(status_tab)
        self._build_config_tab(config_tab)
        self._build_logs_tab(logs_tab)

    def _build_status_tab(self, parent):
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(0, 16))
        ttk.Button(actions, text="Iniciar servicio", command=lambda: self._service_action(start_service)).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Detener servicio", command=lambda: self._service_action(stop_service)).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Reiniciar servicio", command=lambda: self._service_action(restart_service)).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Actualizar estado", command=self._refresh_async).pack(side="left")
        summary = ttk.LabelFrame(parent, text="Configuración activa", padding=12)
        summary.pack(fill="x")
        self.summary_label = ttk.Label(summary, justify="left")
        self.summary_label.pack(anchor="w")
        self._update_summary()

    def _build_config_tab(self, parent):
        form = ttk.Frame(parent)
        form.pack(fill="x")
        ttk.Label(form, text="Tecla").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.key_var, width=20).grid(row=0, column=1, sticky="w", pady=6)
        ttk.Label(form, text="Idioma").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(form, textvariable=self.language_var, values=LANGUAGES, state="readonly", width=17).grid(
            row=1, column=1, sticky="w", pady=6
        )
        ttk.Label(form, text="Modelo").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Combobox(form, textvariable=self.model_var, values=MODELS, state="readonly", width=17).grid(
            row=2, column=1, sticky="w", pady=6
        )
        ttk.Label(form, text="Proveedor STT").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Combobox(form, textvariable=self.stt_provider_var, values=STT_PROVIDERS, state="readonly", width=17).grid(
            row=3, column=1, sticky="w", pady=6
        )
        ttk.Checkbutton(form, text="Modo toggle", variable=self.toggle_var).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=6
        )
        ttk.Button(form, text="Guardar y aplicar", command=self._save_config).grid(
            row=5, column=0, pady=(12, 0), sticky="w"
        )

    def _build_logs_tab(self, parent):
        ttk.Button(parent, text="Recargar logs", command=self._refresh_async).pack(anchor="w", pady=(0, 8))
        self.logs_text = tk.Text(parent, height=20, wrap="word")
        self.logs_text.pack(fill="both", expand=True)
        self.logs_text.insert("1.0", self.log_var.get())
        self.logs_text.configure(state="disabled")

    def _update_summary(self):
        self.summary_label.config(
            text=(
                f"Tecla: {self.key_var.get().upper()}\n"
                f"Idioma: {self.language_var.get()}\n"
                f"Modelo: {self.model_var.get()}\n"
                f"Proveedor STT: {self.stt_provider_var.get()}\n"
                "Modo toggle: " + ("sí" if self.toggle_var.get() else "no")
            )
        )

    def _save_config(self):
        self.config = {
            "key": self.key_var.get().strip().lower() or "f12",
            "toggle": self.toggle_var.get(),
            "language": self.language_var.get(),
            "model": self.model_var.get(),
            "stt_provider": self.stt_provider_var.get(),
        }
        save_config(self.config)
        self._update_summary()
        self.mic_var.set("Micrófono: configuración guardada, reiniciando servicio...")
        self._service_action(restart_service)
        messagebox.showinfo("whisper-ptt", "Configuración guardada y servicio reiniciado para aplicar cambios.")

    def _service_action(self, action):
        threading.Thread(target=self._run_service_action, args=(action,), daemon=True).start()

    def _run_service_action(self, action):
        result = action()
        self.queue.put(("service_action", result.returncode, (result.stdout or result.stderr).strip()))
        self.queue.put(("refresh", None, None))

    def _refresh_async(self):
        threading.Thread(target=self._load_runtime_state, daemon=True).start()

    def _load_runtime_state(self):
        status = get_service_status()
        logs = tail_service_logs()
        self.queue.put(("runtime", status, logs))

    def _poll_queue(self):
        try:
            while True:
                event, value, payload = self.queue.get_nowait()
                if event == "runtime":
                    self.status_var.set(f"Servicio: {value}")
                    self.mic_var.set("Micrófono: listo" if value == "active" else "Micrófono: inactivo")
                    self.logs_text.configure(state="normal")
                    self.logs_text.delete("1.0", "end")
                    self.logs_text.insert("1.0", payload or "Sin logs disponibles")
                    self.logs_text.configure(state="disabled")
                elif event == "service_action":
                    self.status_var.set(
                        "Acción ejecutada correctamente" if value == 0 else "La acción del servicio devolvió error"
                    )
                    if payload:
                        self.mic_var.set(payload)
                elif event == "refresh":
                    self._refresh_async()
        except queue.Empty:
            pass
        self.root.after(300, self._poll_queue)

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide_window(self):
        if self.tray.available:
            self.root.withdraw()
        else:
            self.quit_app()

    def quit_app(self):
        self.tray.stop()
        self.instance_server.close()
        self.root.destroy()


def main():
    if focus_existing_instance():
        return
    root = tk.Tk()
    WhisperFrontendApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
