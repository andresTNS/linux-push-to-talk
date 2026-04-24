# UI Flows — whisper-ptt frontend

Issue: #6

## Primary flow 1 — First-time setup

1. User opens the app.
2. Frontend checks:
   - whether user service exists,
   - whether dependencies are installed,
   - whether a model is already available,
   - whether local config exists.
3. If missing pieces are detected, the app shows a guided setup state:
   - install / update,
   - choose language,
   - choose hotkey,
   - choose model,
   - optional model download.
4. App writes config.
5. App starts or restarts `whisper-dictation` service.
6. User sees final validation state.

## Primary flow 2 — Daily operation

1. User opens the app.
2. Status screen shows:
   - service active,
   - current hotkey,
   - current model,
   - current language,
   - latest known diagnostics state.
3. User optionally changes model or language.
4. App persists config and offers restart.

## Primary flow 3 — Troubleshooting

1. User opens Diagnostics.
2. App runs health checks:
   - binary availability,
   - service state,
   - access to logs,
   - config parse check,
   - model cache visibility.
3. App marks each item:
   - OK,
   - warning,
   - error.
4. User can copy diagnostics output for a GitHub issue.

## Screen layout proposal

## Header
Visible on all screens:
- app title,
- service status badge,
- configured model,
- quick restart button.

## Left navigation
- Status
- Configuration
- Diagnostics
- About

## Status screen
Sections:
- Service state
- Active configuration
- Quick actions
- Recent log tail

## Configuration screen
Sections:
- Hotkey
- Toggle mode
- Language
- Model selector
- Download actions
- Save + restart

## Diagnostics screen
Sections:
- Dependencies
- Service health
- Cache health
- Typing path health (`xdotool`, `xclip`)
- Logs
- Copy diagnostic report

## About screen
Sections:
- project summary,
- version,
- links to README / repo / issues.

## Error handling principles

- show the exact failing subsystem,
- avoid vague 'something went wrong',
- suggest next action,
- allow copying technical details.

## Suggested status language

- Service running
- Service stopped
- Service failed
- Model not downloaded
- Missing dependency
- Config updated, restart required
- Ready to dictate

## Design tone

- sober,
- compact,
- utilitarian,
- consistent with a Linux desktop utility,
- no unnecessary animation or branding weight.
