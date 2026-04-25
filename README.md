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
### Paso a paso
1. Clona este repositorio.
2. Entra al directorio del proyecto.
3. Ejecuta el instalador:

```bash
git clone https://github.com/andresTNS/linux-push-to-talk.git
cd linux-push-to-talk
bash install.sh
```

El instalador:
- verifica e instala dependencias del sistema
- crea el entorno virtual en `~/.local/share/whisper-dictation`
- instala dependencias Python
- copia los binarios a `~/.local/bin`
- habilita e inicia el servicio `whisper-dictation`

Guía completa de instalación y pruebas:
- `docs/INSTALLATION-AND-TESTING.md`

## Uso
| Acción | Resultado |
|--------|-----------|
| Mantener F12 | Inicia grabación |
| Soltar F12 | Transcribe y escribe el texto |

### Cómo probar que funciona
1. Abre una aplicación donde puedas escribir.
2. Mantén presionada `F12`.
3. Habla durante unos segundos.
4. Suelta `F12`.
5. Verifica que el texto se escriba automáticamente en la ventana activa.

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

### Validaciones rápidas
```bash
which dictate
systemctl --user status whisper-dictation
journalctl --user -u whisper-dictation -n 50 --no-pager
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

## Frontend GUI
La primera iteración funcional de GUI ya incluye:
- pantalla de estado del servicio
- configuración visual de tecla, idioma, modelo y modo toggle
- recarga de logs del servicio
- operaciones de iniciar, detener y reiniciar servicio

Para abrir la GUI instalada:
```bash
whisper-ptt-gui
```

Documentación de frontend:
- `docs/frontend/FRONTEND-PROPOSAL.md`
- `docs/frontend/UI-FLOWS.md`
- `docs/frontend/IMPLEMENTATION-PLAN.md`
- `docs/frontend/TKINTER-THREADING-ARCHITECTURE.md`

## Licencia
MIT
