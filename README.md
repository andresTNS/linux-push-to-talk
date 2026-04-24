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

El instalador detecta automáticamente si está corriendo por primera vez (`INSTALL`) o si está actualizando una instalación existente (`UPDATE`).

## Uso
| Acción | Resultado |
|--------|-----------|
| Mantener F12 | Inicia grabación |
| Soltar F12 | Transcribe y escribe el texto |

### Opciones avanzadas
```bash
dictate --key F10                # Cambiar tecla
dictate --model medium           # Más preciso (más lento)
dictate --model distil-large-v3  # Variante distil-whisper
dictate --language auto          # Detectar idioma automáticamente
dictate --toggle                 # Modo toggle en vez de mantener presionado
dictate --download-all           # Pre-descarga todos los modelos registrados
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
| tiny / tiny.en | Muy rápido | Básica | 200 MB |
| base / base.en | Rápido | Buena | 300 MB |
| small / small.en | Medio | Muy buena | 500 MB |
| medium / medium.en | Lento | Excelente | 1.5 GB |
| large-v1 / large-v2 / large-v3 / large-v3-turbo | Más lento | Máxima | 2-3+ GB |
| distil-small.en / distil-medium.en / distil-large-v2 / distil-large-v3 | Optimizado | Muy alta | variable |

Si un modelo no está cacheado localmente, se descarga automáticamente antes del primer uso con una notificación visible.

## Probado en
- Debian 12 (Bookworm) + KDE Plasma + X11

## Licencia
MIT
