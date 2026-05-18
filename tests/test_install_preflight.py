import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SH = REPO_ROOT / "install.sh"


def preflight_definition():
    text = INSTALL_SH.read_text()
    marker = "\npreflight_check\n"
    assert marker in text
    return text.split(marker, 1)[0]


def run_preflight_with_stubs(command_stub):
    script = f"""
{preflight_definition()}
{command_stub}
preflight_check
"""
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True)


def test_preflight_succeeds_when_required_commands_are_available():
    result = run_preflight_with_stubs(
        r'''
command() {
  if [ "$1" = "-v" ]; then
    case "$2" in
      python3|pip3|pkg-config|xdotool|pactl) return 0 ;;
      *) return 1 ;;
    esac
  fi
  builtin command "$@"
}
python3() { return 0; }
pkg-config() { return 0; }
'''
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Preflight OK" in result.stdout


def test_preflight_reports_missing_xdotool_with_install_hint():
    result = run_preflight_with_stubs(
        r'''
command() {
  if [ "$1" = "-v" ]; then
    case "$2" in
      python3|pip3|pkg-config|pactl) return 0 ;;
      xdotool) return 1 ;;
      *) return 1 ;;
    esac
  fi
  builtin command "$@"
}
python3() { return 0; }
pkg-config() { return 0; }
'''
    )

    assert result.returncode == 1
    assert "xdotool" in result.stdout
    assert "Instala con:" in result.stdout
    assert "Preflight falló" in result.stdout
