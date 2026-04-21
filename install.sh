#!/usr/bin/env bash
set -e

# ── Colores ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ── Verificar que no se ejecute como root ─────────────────────────────────────
[ "$EUID" -eq 0 ] && error "No ejecutar como root. Ejecuta como tu usuario normal."

echo ""
echo "  whisper-ptt — Instalador"
echo "  Push-to-talk dictation con Whisper offline"
echo ""

# ── Dependencias del sistema ──────────────────────────────────────────────────
info "Verificando dependencias del sistema..."
MISSING=()
command -v python3 &>/dev/null || MISSING+=("python3")
command -v xdotool &>/dev/null || MISSING+=("xdotool")
command -v xclip &>/dev/null   || MISSING+=("xclip")
dpkg -l libportaudio2 &>/dev/null 2>&1 || MISSING+=("libportaudio2")

if [ ${#MISSING[@]} -gt 0 ]; then
    warn "Instalando dependencias faltantes: ${MISSING[*]}"
    sudo apt-get install -y "${MISSING[@]}" portaudio19-dev
fi

# ── Entorno virtual Python ────────────────────────────────────────────────────
VENV_DIR="$HOME/.local/share/whisper-dictation"
info "Creando entorno virtual en $VENV_DIR..."
python3 -m venv "$VENV_DIR"

info "Instalando librerías Python (puede tardar varios minutos)..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install faster-whisper sounddevice numpy pynput --quiet

# ── Copiar archivos ───────────────────────────────────────────────────────────
info "Instalando archivos..."
mkdir -p "$HOME/.local/bin"
cp whisper-dictation.py "$HOME/.local/bin/whisper-dictation.py"
cp dictate "$HOME/.local/bin/dictate"
chmod +x "$HOME/.local/bin/dictate"

# ── Servicio systemd ──────────────────────────────────────────────────────────
info "Configurando servicio systemd..."
mkdir -p "$HOME/.config/systemd/user"
cp whisper-dictation.service "$HOME/.config/systemd/user/whisper-dictation.service"
systemctl --user daemon-reload
systemctl --user enable whisper-dictation
systemctl --user start whisper-dictation

# ── Verificar ~/.local/bin en PATH ───────────────────────────────────────────
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    warn "~/.local/bin no está en tu PATH."
    warn "Agrega esta línea a tu ~/.bashrc o ~/.zshrc:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
info "¡Instalación completada!"
echo ""
echo "  Mantén presionada F12 para dictar."
echo "  Usa 'dictate --download-all' para predescargar todos los modelos."
echo "  Estado del servicio:"
systemctl --user status whisper-dictation --no-pager -l || true
echo ""
