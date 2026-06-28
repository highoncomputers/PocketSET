#!/usr/bin/env bash
set -eo pipefail

# Auto-detect if we're running via curl-pipe-bash (standalone)
if [ ! -f "wrapper.py" ]; then
    echo "[*] Cloning PocketSET..."
    git clone --depth 1 https://github.com/highoncomputers/PocketSET.git /tmp/PocketSET
    cd /tmp/PocketSET
fi

SCRIPT_SRC="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SRC")" 2>/dev/null && pwd || echo "$PWD")"
[ -n "$SCRIPT_DIR" ] && cd "$SCRIPT_DIR" 2>/dev/null || true

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
_install_set_source() {
    local TMPDIR
    TMPDIR=$(mktemp -d)
    echo "  -> Cloning SET from GitHub..."
    git clone --depth 1 https://github.com/trustedsec/social-engineer-toolkit.git "$TMPDIR/set"
    echo "  -> Installing SET via pip..."
    (cd "$TMPDIR/set" && python3 -m pip install -e . --break-system-packages) && {
        echo "[✓] SET installed from source"
        return 0
    }
    (cd "$TMPDIR/set" && python3 -m pip install -e .) && {
        echo "[✓] SET installed from source"
        return 0
    }
    echo "[!] Could not install SET automatically."
    echo "    Run: cd $TMPDIR/set && pip install -e ."
    return 1
}

install_set() {
    if command -v setoolkit &>/dev/null; then
        echo "[✓] SET already installed ($(which setoolkit))"
        return 0
    fi
    echo "[*] Installing Social-Engineer Toolkit..."
    IS_KALI=0
    grep -qi kali /etc/os-release 2>/dev/null && IS_KALI=1
    if command -v apt &>/dev/null && [ "$IS_KALI" = "1" ]; then
        echo "  -> Kali detected, trying apt..."
        $SUDO apt update -qq 2>/dev/null || true
        if $SUDO apt install -y set 2>/dev/null; then
            echo "[✓] SET installed via apt"
            return 0
        fi
        echo "  -> apt failed, trying source..."
    fi
    _install_set_source
}

install_set || echo "[!] SET install had issues — some attacks may not work"

# --- INSTALL OPTIONAL SYSTEM DEPS ---
echo "[*] Installing optional system dependencies (wireless, email)..."
$SUDO apt install -y aircrack-ng dsniff isc-dhcp-server sendmail 2>/dev/null && \
    echo "[✓] System dependencies installed" || \
    echo "[!] Some system deps failed — wireless/email attacks may not work"

# --- INSTALL METASPLOIT ---
if command -v msfconsole &>/dev/null; then
    echo "[✓] Metasploit already installed ($(which msfconsole))"
else
    echo "[*] Installing Metasploit Framework..."
    curl -fsSL https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > /tmp/msfinstall
    chmod +x /tmp/msfinstall
    /tmp/msfinstall 2>/dev/null && echo "[✓] Metasploit installed" || \
        echo "[!] Metasploit install failed — MSF-dependent attacks disabled"
fi

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
