# Implementation Plan — whisper-ptt frontend

Issue: #6

## Goal

Translate the frontend proposal into an incremental implementation path that remains compatible with the current CLI + systemd architecture.

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
- current config readout.

### Acceptance
- GUI opens,
- reads config,
- checks service state,
- start/stop/restart buttons work.

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
- `frontend/views/*.py` — UI panels

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

Implement only this first:
- status screen,
- configuration screen,
- service controls,
- saved config,
- model dropdown.

That gives real user value without overbuilding.

## Relationship with open-source maintenance

This issue should be treated as a proposal/specification milestone, not as a promise to implement the full GUI immediately.

A good outcome for this issue is:
- clear proposal,
- clear screens,
- clear architecture,
- clear incremental roadmap,
- clear boundary between GUI and backend.
