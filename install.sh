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

APP_NAME="whisper-dictation"
VENV_DIR="$HOME/.local/share/${APP_NAME}"
LOCAL_BIN_DIR="$HOME/.local/bin"
SYSTEMD_DIR="$HOME/.config/systemd/user"
SERVICE_NAME="whisper-dictation"
SERVICE_PATH="$SYSTEMD_DIR/${SERVICE_NAME}.service"
INSTALL_MODE="INSTALL"

# ── Detectar modo: instalación nueva vs actualización ────────────────────────
if [ -d "$VENV_DIR" ] || [ -f "$LOCAL_BIN_DIR/whisper-dictation.py" ] || [ -f "$SERVICE_PATH" ]; then
    INSTALL_MODE="UPDATE"
fi

echo ""
echo "  whisper-ptt — ${INSTALL_MODE}"
echo "  Push-to-talk dictation con Whisper offline"
echo ""

if [ "$INSTALL_MODE" = "UPDATE" ]; then
    echo -e "  ${CYAN}Modo: ACTUALIZACIÓN${NC} — instalación previa detectada"
else
    echo -e "  ${GREEN}Modo: INSTALACIÓN NUEVA${NC}"
fi
echo ""

# ── Dependencias del sistema ──────────────────────────────────────────────────
step "Verificando dependencias del sistema..."
MISSING_PACKAGES=()
command -v python3 &>/dev/null || MISSING_PACKAGES+=("python3")
command -v xdotool &>/dev/null || MISSING_PACKAGES+=("xdotool")
command -v xclip &>/dev/null || MISSING_PACKAGES+=("xclip")
dpkg -s libportaudio2 &>/dev/null 2>&1 || MISSING_PACKAGES+=("libportaudio2")
dpkg -s portaudio19-dev &>/dev/null 2>&1 || MISSING_PACKAGES+=("portaudio19-dev")

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    warn "Instalando dependencias faltantes: ${MISSING_PACKAGES[*]}"
    sudo apt-get update
    sudo apt-get install -y "${MISSING_PACKAGES[@]}"
else
    info "Todas las dependencias del sistema están presentes."
fi

if systemctl --user is-active --quiet "$SERVICE_NAME"; then
    step "Deteniendo servicio actual antes de reemplazar archivos..."
    systemctl --user stop "$SERVICE_NAME"
    info "Servicio detenido."
fi

mkdir -p "$VENV_DIR"
if [ ! -x "$VENV_DIR/bin/python3" ]; then
    step "Creando entorno virtual en $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    info "Reutilizando entorno virtual existente en $VENV_DIR..."
fi

step "Instalando librerías Python (puede tardar varios minutos)..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install faster-whisper sounddevice numpy pynput --quiet
info "Librerías Python instaladas."

step "Instalando archivos..."
mkdir -p "$LOCAL_BIN_DIR"
cp whisper-dictation.py "$LOCAL_BIN_DIR/whisper-dictation.py"
cp dictate "$LOCAL_BIN_DIR/dictate"
cp frontend_gui.py "$LOCAL_BIN_DIR/whisper-ptt-gui"
cp frontend_config.py "$LOCAL_BIN_DIR/frontend_config.py"
cp frontend_service.py "$LOCAL_BIN_DIR/frontend_service.py"
chmod +x "$LOCAL_BIN_DIR/dictate"
chmod +x "$LOCAL_BIN_DIR/whisper-ptt-gui"

step "Configurando servicio systemd..."
mkdir -p "$SYSTEMD_DIR"
cp whisper-dictation.service "$SERVICE_PATH"
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user restart "$SERVICE_NAME"
info "Servicio habilitado y reiniciado."

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    warn "~/.local/bin no está en tu PATH."
    warn "Agrega esta línea a tu ~/.bashrc o ~/.zshrc:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
info "¡${INSTALL_MODE} completado!"
echo ""
echo "  Mantén presionada F12 para dictar."
echo "  Usa 'dictate --download-all' para predescargar todos los modelos."
echo "  Estado del servicio:"
systemctl --user status "$SERVICE_NAME" --no-pager -l || true
echo ""
