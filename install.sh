#!/usr/bin/env bash
set -e

# ── Colores ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step()    { echo -e "${CYAN}[→]${NC} $1"; }

# ── Preflight: detectar distro y validar dependencias sin modificar el sistema ─
preflight_check() {
    step "Ejecutando preflight de dependencias del sistema..."

    if [ ! -r /etc/os-release ]; then
        error "No se pudo detectar la distribución: falta /etc/os-release. Instala manualmente python>=3.9, pip, xdotool, headers de PortAudio y PulseAudio/PipeWire."
    fi

    # shellcheck disable=SC1091
    . /etc/os-release

    local distro="unsupported"
    case "${ID:-}" in
        ubuntu|debian) distro="debian" ;;
        fedora) distro="fedora" ;;
        arch|endeavouros|manjaro) distro="arch" ;;
        *)
            case " ${ID_LIKE:-} " in
                *" debian "*) distro="debian" ;;
                *" fedora "*) distro="fedora" ;;
                *" arch "*) distro="arch" ;;
            esac
            ;;
    esac

    if [ "$distro" = "unsupported" ]; then
        error "Distribución no soportada (${PRETTY_NAME:-desconocida}). Soportadas: Debian/Ubuntu, Fedora y Arch."
    fi

    local missing=()
    local packages=()

    if ! command -v python3 >/dev/null 2>&1 || ! python3 - <<'PYVER' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 9) else 1)
PYVER
    then
        missing+=("python>=3.9")
        case "$distro" in
            debian) packages+=("python3") ;;
            fedora) packages+=("python3") ;;
            arch) packages+=("python") ;;
        esac
    fi

    if ! python3 -m pip --version >/dev/null 2>&1 && ! command -v pip3 >/dev/null 2>&1; then
        missing+=("pip")
        case "$distro" in
            debian) packages+=("python3-pip") ;;
            fedora) packages+=("python3-pip") ;;
            arch) packages+=("python-pip") ;;
        esac
    fi

    if ! command -v xdotool >/dev/null 2>&1; then
        missing+=("xdotool")
        packages+=("xdotool")
    fi

    if ! command -v pkg-config >/dev/null 2>&1 || ! pkg-config --exists portaudio-2.0 2>/dev/null; then
        missing+=("headers de PortAudio")
        case "$distro" in
            debian) packages+=("portaudio19-dev") ;;
            fedora) packages+=("portaudio-devel") ;;
            arch) packages+=("portaudio") ;;
        esac
    fi

    if ! command -v pactl >/dev/null 2>&1 && ! command -v pipewire >/dev/null 2>&1; then
        missing+=("pulseaudio/pipewire")
        case "$distro" in
            debian) packages+=("pulseaudio-utils" "pipewire") ;;
            fedora) packages+=("pulseaudio-utils" "pipewire") ;;
            arch) packages+=("libpulse" "pipewire") ;;
        esac
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        warn "Faltan dependencias obligatorias: ${missing[*]}"
        case "$distro" in
            debian)
                echo "Instala con: sudo apt-get update && sudo apt-get install -y ${packages[*]}"
                ;;
            fedora)
                echo "Instala con: sudo dnf install -y ${packages[*]}"
                ;;
            arch)
                echo "Instala con: sudo pacman -S --needed ${packages[*]}"
                ;;
        esac
        error "Preflight falló. No se realizaron cambios."
    fi

    info "Preflight OK para ${PRETTY_NAME:-$ID}: dependencias obligatorias presentes."
}

preflight_check

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
