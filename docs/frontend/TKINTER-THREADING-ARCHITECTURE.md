# Tkinter Threading Architecture — whisper-ptt

Issue: #6

## Purpose

Define a safe threading model for the first functional GUI iteration so the interface remains responsive while the runtime performs service checks, diagnostics, and configuration actions.

## Constraint

Tkinter is not thread-safe.

Because of that:
- the main thread must own all widget creation and updates,
- background work must not directly touch widgets,
- worker results must be marshalled back to the UI safely.

## Proposed model

### 1. UI thread
Responsibilities:
- create the root window
- render status, configuration, diagnostics, and logs views
- handle button clicks and form events
- consume messages from workers and refresh widgets

Allowed operations:
- `tkinter` widgets
- `after(...)` polling
- lightweight state transitions

Forbidden operations:
- long-running subprocess calls
- blocking diagnostics
- model download work
- keyboard/event loops that can stall rendering

### 2. Service/diagnostics worker
Responsibilities:
- query `systemctl --user` state
- read recent logs
- run dependency checks
- detect config and cache health
- execute install/update/restart workflows

Output channel:
- push structured events into a thread-safe queue consumed by the UI thread

### 3. Runtime/event worker
Responsibilities:
- isolate keyboard/event-related runtime behavior from the GUI
- coordinate hotkey-related configuration or monitoring tasks
- keep event handling independent from Tkinter repaint cycles

Output channel:
- emit runtime state changes into the same queue abstraction

## Event flow

1. User triggers an action in the GUI.
2. UI thread validates the request and dispatches work to a worker.
3. Worker executes the blocking operation.
4. Worker posts a structured result event.
5. Tkinter main thread consumes the event via scheduled polling.
6. UI updates status badges, forms, logs, or error banners.

## Suggested event types

- `service_status_changed`
- `service_logs_loaded`
- `diagnostic_result_ready`
- `config_saved`
- `model_download_started`
- `model_download_finished`
- `runtime_error`
- `microphone_state_changed`

## Stability rules

- no direct widget mutation from worker threads
- no infinite blocking call inside button handlers
- no synchronous shell command tied directly to repaint-sensitive flows
- every background task must surface errors explicitly to the UI
- status polling frequency should be conservative to avoid unnecessary CPU usage on low-resource machines

## Initial implementation recommendation

Start with this minimum architecture:
- one Tkinter app shell
- one shared queue
- one worker for service/diagnostics tasks
- one polling loop with `root.after(...)`

That is enough for the first usable iteration and preserves a clean path for later growth.
