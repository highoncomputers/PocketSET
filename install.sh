#!/usr/bin/env bash
# PocketSET v2.0 — Dual-Platform Installer (Termux / Kali / Other Linux)
set -eo pipefail

# ── Auto-clone if running via curl-pipe-bash ──────────────────────────────────
if [ ! -f "wrapper.py" ]; then
    echo "[*] Cloning PocketSET..."
    git clone --depth 1 https://github.com/highoncomputers/PocketSET.git /tmp/PocketSET
    cd /tmp/PocketSET
fi

# Cleanup trap
TMPFILES=()
cleanup() {
    for f in "${TMPFILES[@]}"; do rm -rf "$f" 2>/dev/null || true; done
}
trap cleanup EXIT

SCRIPT_SRC="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SRC")" 2>/dev/null && pwd || echo "$PWD")"
[ -n "$SCRIPT_DIR" ] && cd "$SCRIPT_DIR" 2>/dev/null || true

echo "╔══════════════════════════════════════════════════════╗"
echo "║         PocketSET v2.0 — Dual-Platform Install       ║"
echo "║  Interactive TUI for Social-Engineer Toolkit (SET)  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Platform Detection ───────────────────────────────────────────────────────
IS_TERMUX=0
IS_KALI=0
IS_ROOT=0
PLATFORM="linux"

if [ -n "$TERMUX_VERSION" ] || echo "$HOME" | grep -q "com.termux"; then
    IS_TERMUX=1
    PLATFORM="termux"
    echo "[*] Detected: Termux (Android)"
elif grep -qi "kali" /etc/os-release 2>/dev/null; then
    IS_KALI=1
    PLATFORM="kali"
    echo "[*] Detected: Kali Linux"
else
    echo "[*] Detected: Other Linux"
fi

# Ask user to confirm or override platform
echo ""
echo "[?] Install mode detected as: $PLATFORM"
echo "    1) Termux (Android / proot)"
echo "    2) Kali Linux"
echo "    3) Other Linux"
read -r -p "Select [1-3, default=$PLATFORM]: " PLAT_CHOICE
case "${PLAT_CHOICE:-$PLATFORM}" in
    1|termux) PLATFORM="termux"; IS_TERMUX=1; IS_KALI=0 ;;
    2|kali)   PLATFORM="kali";   IS_TERMUX=0; IS_KALI=1 ;;
    3|linux)  PLATFORM="linux";  IS_TERMUX=0; IS_KALI=0 ;;
    *) PLATFORM="$PLATFORM" ;;
esac
echo "[✓] Installing for: $PLATFORM"

# ── Root / Sudo Detection ────────────────────────────────────────────────────
if [ "$(id -u)" = "0" ]; then
    IS_ROOT=1
    SUDO=""
    echo "[*] Running as root"
elif command -v sudo &>/dev/null; then
    SUDO="sudo"
    echo "[*] sudo available"
else
    SUDO=""
    echo "[!] Running without sudo — user-local install only"
fi

# ── Python Check ──────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    if [ "$IS_TERMUX" = "1" ]; then
        echo "[*] Installing Python via pkg..."
        pkg update -y && pkg install -y python git
    else
        echo "[ERROR] Python 3 is required. Install:"
        echo "  apt install python3 python3-pip"
        exit 1
    fi
fi
echo "[*] Python: $(python3 --version 2>&1)"

# ── Install SET ───────────────────────────────────────────────────────────────
install_set_source() {
    local TMPDIR
    TMPDIR=$(mktemp -d)
    TMPFILES+=("$TMPDIR")
    echo "  -> Cloning SET from GitHub..."
    git clone --depth 1 https://github.com/trustedsec/social-engineer-toolkit.git "$TMPDIR/set"
    echo "  -> Installing SET via pip..."
    if (cd "$TMPDIR/set" && python3 -m pip install -e . --break-system-packages 2>/dev/null); then
        echo "[✓] SET installed from source"
        return 0
    fi
    if (cd "$TMPDIR/set" && python3 -m pip install -e . 2>/dev/null); then
        echo "[✓] SET installed from source"
        return 0
    fi
    echo "[!] Could not install SET automatically."
    echo "    Manual: cd $TMPDIR/set && pip install -e ."
    return 1
}

install_set() {
    if command -v setoolkit &>/dev/null; then
        echo "[✓] SET already installed ($(which setoolkit))"
        return 0
    fi

    if [ "$IS_TERMUX" = "1" ]; then
        # Termux: must install from source
        echo "[*] Installing SET from source (Termux)..."
        install_set_source
        return $?
    fi

    if [ "$IS_KALI" = "1" ]; then
        echo "[*] Installing SET via apt (Kali)..."
        $SUDO apt update -qq 2>/dev/null || true
        if $SUDO apt install -y set 2>/dev/null; then
            echo "[✓] SET installed via apt"
            return 0
        fi
        echo "  -> apt failed, trying source..."
        install_set_source
        return $?
    fi

    # Other Linux
    echo "[*] Installing SET from source..."
    install_set_source
}

install_set || echo "[!] SET install had issues — some attacks may not work"

# ── Platform-Specific System Dependencies ────────────────────────────────────
echo "[*] Installing system dependencies..."

if [ "$IS_TERMUX" = "1" ]; then
    pkg install -y aircrack-ng 2>/dev/null || true
    echo "[*] Note: wireless attacks require root + external NIC on Android"
elif [ "$IS_KALI" = "1" ]; then
    $SUDO apt install -y aircrack-ng dsniff isc-dhcp-server sendmail 2>/dev/null && \
        echo "[✓] System deps installed" || echo "[!] Some deps failed"
else
    $SUDO apt install -y aircrack-ng dsniff isc-dhcp-server sendmail 2>/dev/null && \
        echo "[✓] System deps installed" || echo "[!] Some deps failed"
fi

# ── Install Metasploit ───────────────────────────────────────────────────────
if command -v msfconsole &>/dev/null; then
    echo "[✓] Metasploit already installed ($(which msfconsole))"
else
    if [ "$IS_TERMUX" = "1" ]; then
        echo "[*] Metasploit on Termux requires manual install."
        echo "    See: https://wiki.termux.com/wiki/Metasploit-Framework"
        echo "    Or run: pkg install metasploit"
        pkg install -y metasploit 2>/dev/null && echo "[✓] Metasploit installed" || \
            echo "[!] Metasploit not installed — MSF attacks disabled"
    elif [ "$IS_KALI" = "1" ]; then
        echo "[*] Installing Metasploit via apt (Kali)..."
        $SUDO apt install -y metasploit-framework 2>/dev/null && echo "[✓] Metasploit installed" || \
            echo "[!] Metasploit install failed"
    else
        echo "[*] Installing Metasploit Framework via Rapid7 installer..."
        TMPFILES+=("/tmp/msfinstall")
        curl -fsSL https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > /tmp/msfinstall
        chmod +x /tmp/msfinstall
        /tmp/msfinstall 2>/dev/null && echo "[✓] Metasploit installed" || \
            echo "[!] Metasploit install failed — MSF-dependent attacks disabled"
    fi
fi

# ── Verify SET ────────────────────────────────────────────────────────────────
SETOOLKIT_PATH=""
if command -v setoolkit &>/dev/null; then
    SETOOLKIT_PATH=$(which setoolkit)
elif [ -f "./setoolkit" ]; then
    SETOOLKIT_PATH="./setoolkit"
elif [ -f "/usr/local/share/setoolkit/setoolkit" ]; then
    SETOOLKIT_PATH="/usr/local/share/setoolkit/setoolkit"
elif [ -f "/data/data/com.termux/files/usr/bin/setoolkit" ]; then
    SETOOLKIT_PATH="/data/data/com.termux/files/usr/bin/setoolkit"
fi
echo "[✓] SET located at: ${SETOOLKIT_PATH:-not in PATH}"

# ── Install Python Dependencies ──────────────────────────────────────────────
echo "[*] Installing Python dependencies..."
pip_install() {
    python3 -m pip install "$@" -q 2>/dev/null && return 0
    python3 -m pip install "$@" -q --break-system-packages 2>/dev/null && return 0
    return 1
}
DEPS="rich pexpect Pillow qrcode"
if pip_install $DEPS; then
    echo "[✓] Python dependencies installed"
else
    echo "[!] pip install had issues — run: pip install $DEPS"
fi

# ── Generate Platform Config ─────────────────────────────────────────────────
mkdir -p ~/.pocketset
cat > ~/.pocketset/config.json << 'CONFEOF'
{
  "platform": "PLATFORM_PLACEHOLDER",
  "theme": {
    "header": "bold cyan",
    "success": "bold green",
    "error": "bold red",
    "warning": "bold yellow",
    "info": "white",
    "muted": "dim white"
  },
  "pexpect_delay": 0.3,
  "timeout_seconds": 600,
  "history_size": 100,
  "auto_update": true,
  "pre_flight_ping": true,
  "default_smtp": "",
  "default_lhost": "",
  "default_port": "443"
}
CONFEOF
sed -i "s/PLATFORM_PLACEHOLDER/$PLATFORM/g" ~/.pocketset/config.json
echo "[✓] Platform config written (~/.pocketset/config.json)"

# ── Copy Files to /opt ────────────────────────────────────────────────────────
echo "[*] Installing PocketSET to /opt/PocketSET..."
mkdir -p /opt/PocketSET
cp -f wrapper.py schema.json validation.json ui.json workflow.json requirements.txt README.md /opt/PocketSET/ 2>/dev/null || true
cp -f install.sh /opt/PocketSET/ 2>/dev/null || true
chmod +x /opt/PocketSET/wrapper.py
cp -f ~/.pocketset/config.json /opt/PocketSET/ 2>/dev/null || true

# ── Copy Examples ─────────────────────────────────────────────────────────────
if [ -d "examples" ]; then
    mkdir -p /opt/PocketSET/examples ~/.pocketset/presets
    cp examples/*.json /opt/PocketSET/examples/ 2>/dev/null || true
    cp examples/*.json ~/.pocketset/presets/ 2>/dev/null || true
fi

# ── Create Launcher ───────────────────────────────────────────────────────────
LAUNCHER_INSTALLED=0
LAUNCHER_SCRIPT='#!/usr/bin/env bash
exec python3 /opt/PocketSET/wrapper.py "$@"
'

if [ -w /usr/local/bin ]; then
    echo "$LAUNCHER_SCRIPT" > /usr/local/bin/pocketset
    chmod +x /usr/local/bin/pocketset
    echo "[✓] Installed to /usr/local/bin/pocketset"
    LAUNCHER_INSTALLED=1
elif [ "$IS_TERMUX" = "1" ] && [ -w "$PREFIX/bin" ]; then
    echo "$LAUNCHER_SCRIPT" > "$PREFIX/bin/pocketset"
    chmod +x "$PREFIX/bin/pocketset"
    echo "[✓] Installed to $PREFIX/bin/pocketset"
    LAUNCHER_INSTALLED=1
elif [ -d "$HOME/.local/bin" ] && [ -w "$HOME/.local/bin" ]; then
    echo "$LAUNCHER_SCRIPT" > "$HOME/.local/bin/pocketset"
    chmod +x "$HOME/.local/bin/pocketset"
    echo "[✓] Installed to ~/.local/bin/pocketset"
    echo "[!] Make sure ~/.local/bin is in your PATH"
    LAUNCHER_INSTALLED=1
fi

# ── Bashrc Alias Fallback ─────────────────────────────────────────────────────
if [ "$LAUNCHER_INSTALLED" = "0" ]; then
    ALIAS_CMD="alias pocketset='python3 /opt/PocketSET/wrapper.py'"
    if ! grep -q "alias pocketset" ~/.bashrc 2>/dev/null; then
        echo "" >> ~/.bashrc
        echo "# PocketSET" >> ~/.bashrc
        echo "$ALIAS_CMD" >> ~/.bashrc
        echo "[✓] Added 'pocketset' alias to ~/.bashrc"
    else
        echo "[✓] pocketset alias already in ~/.bashrc"
    fi
    eval "$ALIAS_CMD"
    LAUNCHER_INSTALLED=1
fi

# ── Wrapper symlink in cwd ────────────────────────────────────────────────────
chmod +x wrapper.py
ln -sf /opt/PocketSET/wrapper.py ./pocketset 2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║       PocketSET v2.0 installed successfully!        ║"
echo "║                                                     ║"
echo "║   Platform: $PLATFORM"
echo "║                                                     ║"
echo "║   Run:  pocketset                                    ║"
if [ "$LAUNCHER_INSTALLED" = "1" ]; then
    echo "║                                                     ║"
    echo "║   You may need to restart your shell or run:        ║"
    echo "║     source ~/.bashrc                                ║"
fi
echo "║                                                     ║"
echo "║   Or directly: python3 /opt/PocketSET/wrapper.py     ║"
echo "╚══════════════════════════════════════════════════════╝"
