# Implementation Plan — whisper-ptt frontend

Issue: #6

## Goal

Translate the frontend proposal into an incremental implementation path that remains compatible with the current CLI + systemd architecture and aligns with the owner guidance in issue #6.

Owner constraints now incorporated into this plan:
- Tkinter only for the first functional iteration,
- robust behavior on low-resource Linux hardware,
- strict separation between GUI and keyboard/event logic,
- installation and deployment guide as part of the deliverable,
- atomic commits with Conventional Commits during implementation,
- every implementation commit linked back to issue #6.

## Phase 0 — Preparation

Before coding the GUI:
- consolidate the operational config model,
- define a single config file location,
- make the runtime read configuration from that file,
- keep CLI flags as overrides where appropriate.

### Expected output
- `config.json` schema defined,
- read/write helpers implemented,
- service wrapper capable of launching with persisted config.

## Phase 1 — MVP GUI shell

Build a minimal Python Tkinter app with:
- top status banner,
- tabs or left navigation,
- service controls,
- current config readout,
- clear microphone state indicator,
- non-blocking background refresh for service state.

### Acceptance
- GUI opens,
- reads config,
- checks service state,
- start/stop/restart buttons work,
- UI remains responsive while status checks run.

## Phase 2 — Configuration editor

Add editable controls for:
- hotkey,
- toggle mode,
- language,
- model selection.

### Acceptance
- user can save config without touching terminal,
- service restart applies changes,
- invalid inputs are blocked or explained.

## Phase 3 — Model management

Add:
- current model visibility,
- on-demand model download,
- `download all` action,
- progress feedback where feasible.

### Acceptance
- missing model can be downloaded from GUI,
- current model can be switched visually,
- registry options remain aligned with backend support.

## Phase 4 — Diagnostics

Add health panel for:
- dependencies,
- service logs,
- model cache presence,
- typing path capability.

### Acceptance
- GUI identifies the most common failure modes,
- user can copy diagnostic text for issue reporting.

## Phase 5 — Packaging polish

Optional after MVP:
- desktop entry,
- icon,
- launcher integration,
- distro-specific packaging.

## Architecture notes

Recommended frontend module split:
- `frontend/app.py` — entrypoint
- `frontend/service.py` — systemd interaction
- `frontend/config.py` — config read/write
- `frontend/models.py` — model registry / downloads
- `frontend/diagnostics.py` — checks / report generation
- `frontend/hotkey.py` — keyboard/event orchestration outside the UI thread
- `frontend/runtime_queue.py` — thread-safe message passing to Tkinter
- `frontend/views/*.py` — UI panels

Threading rules:
- all Tkinter widget updates happen only on the main thread,
- blocking work runs in workers,
- workers communicate results to the UI through a queue,
- the UI consumes events through periodic `after(...)` polling.

## Risks

1. **Config drift**
   - If GUI config and CLI flags diverge, support becomes confusing.
   - Mitigation: one canonical config source.

2. **Desktop environment variance**
   - Different Linux environments may behave differently.
   - Mitigation: MVP should target the currently documented X11 path first.

3. **Model availability / cache assumptions**
   - Heuristics for downloaded models may become brittle.
   - Mitigation: centralize registry/cache logic.

4. **Text injection reliability**
   - GUI cannot solve every injection-path issue by itself.
   - Mitigation: expose current typing strategy and diagnostics.

## Recommended first implementation milestone

Implement this first functional milestone:
- status screen,
- configuration screen,
- service controls,
- saved config,
- model dropdown,
- hotkey configuration from UI,
- microphone/status feedback,
- installation/testing guide aligned with Linux deployment.

That gives real user value without overbuilding while still honoring the owner's request for a usable first iteration.

## Commit discipline for implementation

When implementation starts, use this delivery discipline:
- one file changed per commit,
- Conventional Commits naming,
- each commit body references issue `#6`,
- keep GUI and runtime changes traceable by layer.

Suggested examples:
- `feat(frontend): add tkinter app shell`
- `feat(frontend): add config loader`
- `feat(frontend): add service status panel`
- `docs(frontend): add linux deployment notes`
