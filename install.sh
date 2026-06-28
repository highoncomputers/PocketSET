#!/usr/bin/env bash
set -euo pipefail

# Auto-detect if we're running via curl-pipe-bash (standalone)
if [ ! -f "wrapper.py" ]; then
    echo "[*] Cloning PocketSET..."
    git clone --depth 1 https://github.com/highoncomputers/PocketSET.git /tmp/PocketSET
    cd /tmp/PocketSET
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════╗"
echo "║            PocketSET v1.0 — Quick Install            ║"
echo "║  Interactive TUI for Social-Engineer Toolkit (SET)  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# --- ROOT DETECTION ---
# In proot (Termux), docker, etc. we run as root with no sudo available
IS_ROOT=0
if [ "$(id -u)" = "0" ]; then
    IS_ROOT=1
    SUDO=""
    echo "[*] Running as root (proot/docker detected)"
elif command -v sudo &>/dev/null; then
    SUDO="sudo"
    echo "[*] sudo available"
else
    SUDO=""
    echo "[!] Running without sudo — installing user-local only"
fi

# --- CHECK PYTHON ---
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python 3 is required. Install it first:"
    echo "  apt install python3 python3-pip"
    exit 1
fi
echo "[*] Python: $(python3 --version 2>&1)"

# --- INSTALL SET ---
_install_from_source() {
    local TMPDIR
    TMPDIR=$(mktemp -d)
    echo "  -> Cloning SET from GitHub..."
    git clone --depth 1 https://github.com/trustedsec/social-engineer-toolkit.git "$TMPDIR/set"
    (cd "$TMPDIR/set" && python3 -m pip install -e . 2>/dev/null) || {
        echo "  -> Trying setup.py..."
        (cd "$TMPDIR/set" && $SUDO python3 setup.py 2>/dev/null) || {
            echo "[!] Could not install SET automatically."
            echo "    Run manually: cd $TMPDIR/set && pip install -e ."
            return 1
        }
    }
}

install_set() {
    if command -v setoolkit &>/dev/null; then
        echo "[✓] SET already installed ($(which setoolkit))"
        return 0
    fi
    echo "[*] Installing Social-Engineer Toolkit..."
    if command -v apt &>/dev/null; then
        echo "  -> Trying apt..."
        $SUDO apt update -qq 2>/dev/null || true
        $SUDO apt install -y set 2>/dev/null && {
            echo "[✓] SET installed via apt"
            return 0
        }
        echo "  -> apt failed, trying source..."
    fi
    _install_from_source
}

install_set || echo "[!] SET install had issues — some attacks may not work"

# --- VERIFY SET ---
SETOOLKIT_PATH=""
if command -v setoolkit &>/dev/null; then
    SETOOLKIT_PATH=$(which setoolkit)
elif [ -f "./setoolkit" ]; then
    SETOOLKIT_PATH="./setoolkit"
elif [ -f "/usr/local/share/setoolkit/setoolkit" ]; then
    SETOOLKIT_PATH="/usr/local/share/setoolkit/setoolkit"
else
    echo "[!] setoolkit binary not found in PATH."
    echo "    Some attacks may fail. You can still run: python3 wrapper.py"
fi
echo "[✓] SET located at: ${SETOOLKIT_PATH:-not in PATH}"

# --- INSTALL PYTHON DEPS ---
echo "[*] Installing Python dependencies..."
python3 -m pip install --upgrade rich pexpect Pillow qrcode -q 2>/dev/null || \
    python3 -m pip install rich pexpect Pillow qrcode --break-system-packages -q 2>/dev/null || \
    echo "[!] Some pip packages failed — try: pip install rich pexpect"
echo "[✓] Python dependencies installed"

# --- COPY TO /opt FOR PERSISTENCE ---
echo "[*] Installing PocketSET to /opt/PocketSET..."
mkdir -p /opt/PocketSET
cp -f wrapper.py schema.json validation.json ui.json workflow.json requirements.txt README.md /opt/PocketSET/ 2>/dev/null
cp -f install.sh /opt/PocketSET/ 2>/dev/null
chmod +x /opt/PocketSET/wrapper.py

# --- CREATE LAUNCHER ---
LAUNCHER_INSTALLED=0
LAUNCHER_SCRIPT='#!/usr/bin/env bash
exec python3 /opt/PocketSET/wrapper.py "$@"
'

if [ -w /usr/local/bin ]; then
    echo "$LAUNCHER_SCRIPT" > /usr/local/bin/pocketset
    chmod +x /usr/local/bin/pocketset
    echo "[✓] Installed to /usr/local/bin/pocketset"
    LAUNCHER_INSTALLED=1
elif [ -d "$HOME/.local/bin" ] && [ -w "$HOME/.local/bin" ]; then
    echo "$LAUNCHER_SCRIPT" > "$HOME/.local/bin/pocketset"
    chmod +x "$HOME/.local/bin/pocketset"
    echo "[✓] Installed to ~/.local/bin/pocketset"
    echo "[!] Make sure ~/.local/bin is in your PATH"
    LAUNCHER_INSTALLED=1
fi

# --- BASHRC ALIAS FALLBACK ---
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

# --- COPY WRAPPER TO CWD TOO ---
chmod +x wrapper.py
ln -sf /opt/PocketSET/wrapper.py ./pocketset 2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║           PocketSET installed successfully!          ║"
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
