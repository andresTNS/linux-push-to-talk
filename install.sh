#!/usr/bin/env bash
set -e

# ── Colores ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step()    { echo -e "${CYAN}[→]${NC} $1"; }

# ── Verificar que no se ejecute como root ────────────────────────────────────
[ "$EUID" -eq 0 ] && error "No ejecutar como root. Ejecuta como tu usuario normal."

VENV_DIR="$HOME/.local/share/whisper-dictation"
BIN_SCRIPT="$HOME/.local/bin/whisper-dictation.py"
SERVICE_NAME="whisper-dictation"

# ── Detectar modo: instalación nueva vs actualización ────────────────────────
IS_UPDATE=false
if [ -d "$VENV_DIR" ] && [ -f "$BIN_SCRIPT" ] && \
   systemctl --user is-enabled "$SERVICE_NAME" &>/dev/null; then
    IS_UPDATE=true
fi

echo ""
echo "  whisper-ptt — Instalador"
echo "  Push-to-talk dictation con Whisper offline"
echo ""

if $IS_UPDATE; then
    echo -e "  ${CYAN}Modo: ACTUALIZACIÓN${NC} — instalación previa detectada"
else
    echo -e "  ${GREEN}Modo: INSTALACIÓN NUEVA${NC}"
fi
echo ""

# ── Dependencias del sistema (ambos modos) ───────────────────────────────────
step "Verificando dependencias del sistema..."
MISSING=()
command -v python3  &>/dev/null || MISSING+=("python3")
command -v xdotool  &>/dev/null || MISSING+=("xdotool")
command -v xclip    &>/dev/null || MISSING+=("xclip")
dpkg -l libportaudio2 &>/dev/null 2>&1 || MISSING+=("libportaudio2")

if [ ${#MISSING[@]} -gt 0 ]; then
    warn "Instalando dependencias faltantes: ${MISSING[*]}"
    sudo apt-get install -y "${MISSING[@]}" portaudio19-dev
else
    info "Todas las dependencias del sistema están presentes."
fi

# ── Flujo de ACTUALIZACIÓN ───────────────────────────────────────────────────
if $IS_UPDATE; then

    step "Deteniendo servicio en ejecución..."
    systemctl --user stop "$SERVICE_NAME"
    info "Servicio detenido."

    step "Actualizando archivos..."
    # Mostrar qué cambió en el script principal
    if ! diff -q whisper-dictation.py "$BIN_SCRIPT" &>/dev/null; then
        info "whisper-dictation.py tiene cambios — actualizando."
        cp whisper-dictation.py "$BIN_SCRIPT"
    else
        info "whisper-dictation.py sin cambios."
    fi

    if ! diff -q dictate "$HOME/.local/bin/dictate" &>/dev/null; then
        info "dictate tiene cambios — actualizando."
        cp dictate "$HOME/.local/bin/dictate"
        chmod +x "$HOME/.local/bin/dictate"
    else
        info "dictate sin cambios."
    fi

    SERVICE_FILE="$HOME/.config/systemd/user/$SERVICE_NAME.service"
    if ! diff -q whisper-dictation.service "$SERVICE_FILE" &>/dev/null; then
        info "Archivo de servicio tiene cambios — actualizando."
        cp whisper-dictation.service "$SERVICE_FILE"
        systemctl --user daemon-reload
    else
        info "Archivo de servicio sin cambios."
    fi

    step "Reiniciando servicio..."
    systemctl --user start "$SERVICE_NAME"
    info "Servicio reiniciado."

# ── Flujo de INSTALACIÓN NUEVA ───────────────────────────────────────────────
else

    step "Creando entorno virtual Python en $VENV_DIR..."
    python3 -m venv "$VENV_DIR"

    step "Instalando librerías Python (puede tardar varios minutos)..."
    "$VENV_DIR/bin/pip" install --upgrade pip --quiet
    "$VENV_DIR/bin/pip" install faster-whisper sounddevice numpy pynput --quiet
    info "Librerías Python instaladas."

    step "Copiando archivos..."
    mkdir -p "$HOME/.local/bin"
    cp whisper-dictation.py "$BIN_SCRIPT"
    cp dictate "$HOME/.local/bin/dictate"
    chmod +x "$HOME/.local/bin/dictate"
    info "Archivos copiados."

    step "Configurando servicio systemd..."
    mkdir -p "$HOME/.config/systemd/user"
    cp whisper-dictation.service "$HOME/.config/systemd/user/$SERVICE_NAME.service"
    systemctl --user daemon-reload
    systemctl --user enable "$SERVICE_NAME"
    systemctl --user start "$SERVICE_NAME"
    info "Servicio habilitado e iniciado."

    # ── Verificar ~/.local/bin en PATH ────────────────────────────────────────
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        warn "~/.local/bin no está en tu PATH."
        warn "Agrega esta línea a tu ~/.bashrc o ~/.zshrc:"
        echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi

fi

# ── Resumen final (ambos modos) ──────────────────────────────────────────────
echo ""
if $IS_UPDATE; then
    info "¡Actualización completada!"
else
    info "¡Instalación completada!"
fi
echo ""
echo "  Mantén presionada F12 para dictar."
echo "  Usa 'dictate --download-all' para predescargar todos los modelos."
echo "  Estado del servicio:"
systemctl --user status "$SERVICE_NAME" --no-pager -l || true
echo ""
