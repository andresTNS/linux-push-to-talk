# whisper-ptt

Push-to-talk dictation para Linux usando OpenAI Whisper offline.
Mantén presionada una tecla para grabar tu voz y el texto se escribe
automáticamente donde tengas el cursor. Sin internet, sin APIs, funciona
en cualquier aplicación.

## Características
- 100% offline — tu voz nunca sale de tu máquina
- Funciona en cualquier aplicación (navegador, editor, terminal, etc.)
- Notificaciones visuales en KDE
- Arranque automático al iniciar sesión (systemd)
- Tecla configurable (por defecto F12)
- Soporte multiidioma (español, inglés y más)

## Requisitos
- Linux con X11
- Python 3.9+
- xdotool y portaudio19-dev

## Instalación
```bash
bash install.sh
```

## Uso
| Acción | Resultado |
|--------|-----------|
| Mantener F12 | Inicia grabación |
| Soltar F12 | Transcribe y escribe el texto |

### Opciones avanzadas
```bash
dictate --key F10          # Cambiar tecla
dictate --model medium     # Más preciso (más lento)
dictate --language auto    # Detectar idioma automáticamente
dictate --toggle           # Modo toggle en vez de mantener presionado
```

### Controlar el servicio
```bash
systemctl --user status whisper-dictation
systemctl --user restart whisper-dictation
systemctl --user stop whisper-dictation
journalctl --user -u whisper-dictation -f
```

## Modelos disponibles
| Modelo | Velocidad | Precisión | RAM aprox |
|--------|-----------|-----------|-----------|
| tiny   | Muy rápido | Básica   | 200 MB    |
| base   | Rápido     | Buena    | 300 MB    |
| small  | Medio      | Muy buena| 500 MB    |
| medium | Lento      | Excelente| 1.5 GB    |

## Probado en
- Debian 12 (Bookworm) + KDE Plasma + X11

## Frontend proposal
A frontend proposal for visual configuration and operation is documented in:
- `docs/frontend/FRONTEND-PROPOSAL.md`
- `docs/frontend/UI-FLOWS.md`
- `docs/frontend/IMPLEMENTATION-PLAN.md`

## Licencia
MIT
