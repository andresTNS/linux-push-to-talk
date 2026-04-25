# Frontend Proposal — whisper-ptt

Issue: #6
Branch: `feature/issue-6-frontend-proposal`
Base: `dev`

## Objective

Design a lightweight graphical frontend for `whisper-ptt` that preserves the project's offline-first, minimal, Linux-native philosophy while reducing setup and operational friction for non-technical users.

The frontend is not intended to replace the CLI. It should sit on top of the existing scripts and service model, exposing the most important controls visually.

## Product principles

1. **Offline first**
   - No cloud dependency.
   - No telemetry by default.
   - No account model.

2. **Thin layer over the current system**
   - Reuse `install.sh`, `dictate`, `whisper-dictation.py`, and `systemd --user` service behavior.
   - Avoid duplicating configuration logic in multiple places.

3. **Operator clarity**
   - The user should immediately understand:
     - whether the service is running,
     - which model is active,
     - which language is active,
     - which hotkey is configured,
     - and whether dependencies are healthy.

4. **Safe progressive complexity**
   - The default view should be simple.
   - Advanced controls should exist, but remain secondary.

5. **Consistent with the current project scope**
   - Linux desktop utility.
   - X11-first today, with room for future Wayland strategy.

## Recommended technical direction

### Required MVP stack

**Python + Tkinter only**

This proposal now follows the explicit direction requested by the repository owner in issue #6:
- use Tkinter exclusively for the first functional iteration,
- avoid heavier GUI dependencies,
- preserve low resource usage on limited hardware,
- keep packaging and runtime footprint simple.

Why:
- matches the current Python-based project,
- minimal extra dependencies,
- easier to maintain for an open-source utility,
- enough for configuration, service control and diagnostics.

### Alternatives considered

#### PySide / Qt
Pros:
- better UX,
- stronger widget set,
- more scalable long term.

Cons:
- heavier dependency surface,
- more packaging complexity,
- likely overkill for first usable version.

#### Tauri / Web frontend
Pros:
- modern UX,
- future-friendly.

Cons:
- introduces a second application stack,
- higher build/distribution complexity,
- drifts from the current philosophy of simple offline utility.

## MVP scope

### 1. Status screen
Purpose: answer "is it working?"

Should show:
- service status: active / inactive / failed,
- configured hotkey,
- selected model,
- selected language,
- install mode / update state if known,
- quick buttons:
  - start service,
  - stop service,
  - restart service,
  - open logs.

### 2. Configuration screen
Purpose: answer "how do I set it up?"

Should allow editing:
- hotkey,
- push-to-talk mode vs toggle mode,
- language (`es`, `en`, `auto`, etc.),
- model selection from registry,
- download current model,
- pre-download all models.

### 3. Diagnostics screen
Purpose: answer "why is it failing?"

Should show:
- presence of `xdotool`, `xclip`, PortAudio,
- Python env presence,
- model cache visibility,
- recent `systemd --user` logs,
- a simple self-check result.

## Threading and responsiveness model

The GUI must remain responsive even while background dictation and service operations are happening.

Required design:
- Tkinter main thread owns all UI updates.
- Keyboard capture and long-running operations must run outside the UI thread.
- Communication back to the GUI should happen through thread-safe queues or scheduled UI polling via `after(...)`.
- Service actions, diagnostics, and model-management tasks must never block the main window.

Minimum worker separation for first functional iteration:
- UI thread: windows, widgets, rendering, user actions
- background worker: service status refresh, diagnostics, install/update actions
- dictation/event worker: hotkey/event capture and runtime coordination when needed

This separation is mandatory to avoid frozen windows and "not responding" states.

## Configuration model

The frontend should introduce a single local config file owned by the user, for example:

`~/.config/whisper-dictation/config.json`

Suggested fields:
- `key`
- `toggle`
- `language`
- `model`
- `downloaded_models`
- `typing_mode` (`xdotool` / `xclip+paste` fallback preference)

The CLI and service wrapper should eventually read from the same config source to avoid drift.

## Service integration

The frontend should not implement background dictation itself.

Instead, it should:
- read state from the existing user service,
- update config,
- restart service when needed,
- surface logs and operational status.

This keeps the GUI thin and consistent with the current architecture.

## UX guidelines

- one-window application,
- no modal-heavy flow,
- visible status at top,
- safe defaults,
- explicit error messages,
- copyable diagnostic output for issue reports.

## Relation to current branches

This proposal should build on the direction already visible in `feat/mejoras-generales`, especially around:
- better installation/update handling,
- richer model selection,
- improved operational behavior.

The frontend should leverage that evolution rather than fork from it conceptually.

## Non-goals for MVP

- Wayland-native injection support,
- audio waveform editor,
- account sync,
- cloud model providers,
- packaging for every distro format on day one.

## Deliverable target

A first implementation should produce:
- a runnable local Tkinter GUI,
- service start/stop/restart,
- editable settings persisted to config,
- automated hotkey configuration from the UI,
- immediate visual microphone/status feedback,
- model selection and download actions,
- diagnostic panel,
- logs view,
- installation and deployment guidance for Linux environments.
