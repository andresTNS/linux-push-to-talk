# Instalación y prueba paso a paso

Esta guía explica cómo dejar `whisper-ptt` funcionando en Linux y cómo comprobar que quedó correctamente instalado.

## 1. Requisitos previos

Antes de instalar, verifica que tu entorno cumpla con lo siguiente:

- Linux con X11
- Python 3.9 o superior
- `sudo` disponible para instalar dependencias del sistema
- Una aplicación abierta donde puedas escribir texto para probar el dictado

Dependencias del sistema usadas por el proyecto:

- `python3`
- `xdotool`
- `libportaudio2`
- `portaudio19-dev`

## 2. Clonar el repositorio

```bash
git clone https://github.com/andresTNS/linux-push-to-talk.git
cd linux-push-to-talk
```

## 3. Ejecutar el instalador

```bash
bash install.sh
```

El instalador realiza estas acciones:

1. verifica dependencias del sistema
2. instala paquetes faltantes con `apt-get` si hace falta
3. crea un entorno virtual en `~/.local/share/whisper-dictation`
4. instala las librerías Python necesarias
5. copia `dictate` y `whisper-dictation.py` a `~/.local/bin`
6. instala y activa el servicio `whisper-dictation` en `systemd --user`

Importante: no ejecutes `install.sh` como `root`.

## 4. Verificar que la instalación quedó correcta

Comprueba que el binario exista:

```bash
which dictate
```

Debería resolver a una ruta dentro de `~/.local/bin`.

Comprueba que el servicio esté activo:

```bash
systemctl --user status whisper-dictation
```

Si quieres reiniciarlo manualmente:

```bash
systemctl --user restart whisper-dictation
```

Si quieres ver logs en vivo:

```bash
journalctl --user -u whisper-dictation -f
```

## 5. Primera prueba funcional

1. abre un editor de texto, navegador o cualquier campo donde puedas escribir
2. mantén presionada `F12`
3. habla con claridad durante 1 a 3 segundos
4. suelta `F12`
5. espera a que termine el procesamiento
6. confirma que el texto aparezca donde estaba el cursor

Si todo está bien, el flujo esperado es:

- aparece notificación de grabación
- luego aparece notificación de procesamiento
- finalmente el texto se escribe automáticamente en la ventana activa

## 6. Pruebas recomendadas

### Prueba básica

- dicta una frase corta en español
- confirma que el texto se inserta correctamente

### Prueba de ventana activa

- repite la prueba en distintas aplicaciones
- por ejemplo: navegador, editor de texto, terminal, chat

### Prueba de idioma

```bash
dictate --language auto
```

Luego dicta en otro idioma y verifica el resultado.

### Prueba de precisión

```bash
dictate --model medium
```

Esto usa un modelo más preciso, pero más lento y con mayor consumo de RAM.

### Prueba de tecla alternativa

```bash
dictate --key F10
```

Útil si `F12` está ocupada por otra aplicación o atajo del escritorio.

### Prueba de modo toggle

```bash
dictate --toggle
```

En este modo:

- una pulsación inicia la grabación
- la siguiente pulsación la detiene y dispara la transcripción

## 7. Solución rápida de problemas

### `dictate` no se encuentra

Agrega `~/.local/bin` a tu `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Luego agrega esa línea a tu `~/.bashrc` o `~/.zshrc`.

### El servicio no inicia

Revisa:

```bash
systemctl --user status whisper-dictation
journalctl --user -u whisper-dictation -n 100 --no-pager
```

### No escribe texto en la aplicación

Verifica que:

- estés usando X11
- `xdotool` esté instalado
- la ventana destino tenga el foco

### No captura audio

Verifica que:

- el micrófono funcione en el sistema
- tengas permisos para usar el dispositivo de audio
- `libportaudio2` esté instalado

## 8. Comandos útiles

```bash
dictate --key F10
dictate --model medium
dictate --language auto
dictate --toggle
systemctl --user status whisper-dictation
systemctl --user restart whisper-dictation
journalctl --user -u whisper-dictation -f
```
