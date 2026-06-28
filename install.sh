#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════╗"
echo "║            PocketSET v1.0 — Quick Install            ║"
echo "║  Interactive TUI for Social-Engineer Toolkit (SET)  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python 3 is required. Install it first:"
    echo "  apt install python3 python3-pip"
    exit 1
fi

PY_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d. -f1-2)
echo "[*] Python version: $(python3 --version 2>&1)"

# Install SET if missing
if command -v setoolkit &>/dev/null; then
    echo "[✓] SET already installed"
else
    echo "[*] Installing Social-Engineer Toolkit..."
    if command -v apt &>/dev/null; then
        echo "  -> Trying apt..."
        sudo apt update -qq && sudo apt install -y set 2>/dev/null && echo "[✓] SET installed via apt" || {
            echo "  -> apt install failed, installing from source..."
            _install_from_source
        }
    else
        _install_from_source
    fi
fi

# Verify SET
if ! command -v setoolkit &>/dev/null; then
    echo "[!] setoolkit not found in PATH after install."
    echo "    You may need to add it or run pocketset from the SET directory."
    echo "    Attempting pip install..."
    _install_from_source
fi

# Install Python dependencies
echo "[*] Installing Python dependencies..."
python3 -m pip install --upgrade pip -q
python3 -m pip install rich pexpect Pillow qrcode -q
echo "[✓] Python dependencies installed"

# Make wrapper executable
chmod +x wrapper.py
echo "[✓] wrapper.py made executable"

# Symlink to PATH
if [ -d /usr/local/bin ]; then
    sudo ln -sf "$(pwd)/wrapper.py" /usr/local/bin/pocketset
    echo "[✓] Symlinked to /usr/local/bin/pocketset"
elif [ -d "$HOME/.local/bin" ]; then
    ln -sf "$(pwd)/wrapper.py" "$HOME/.local/bin/pocketset"
    echo "[✓] Symlinked to ~/.local/bin/pocketset"
    echo "[!] Make sure ~/.local/bin is in your PATH"
else
    echo "[!] Could not create symlink. Run manually:"
    echo "    sudo ln -sf $(pwd)/wrapper.py /usr/local/bin/pocketset"
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║           PocketSET installed successfully!          ║"
echo "║                                                     ║"
echo "║   Run:  pocketset                                    ║"
echo "║   Or:   python3 $(pwd)/wrapper.py                    ║"
echo "╚══════════════════════════════════════════════════════╝"

function _install_from_source() {
    local TMPDIR
    TMPDIR=$(mktemp -d)
    echo "  -> Cloning SET from GitHub..."
    git clone --depth 1 https://github.com/trustedsec/social-engineer-toolkit.git "$TMPDIR/set"
    cd "$TMPDIR/set"
    python3 -m venv .venv 2>/dev/null || true
    python3 -m pip install -e . 2>/dev/null || {
        echo "  -> Trying setup.py install..."
        sudo python3 setup.py 2>/dev/null || {
            echo "[!] Source install needs manual steps."
            echo "    cd $TMPDIR/set && pip install -e ."
        }
    }
    cd "$SCRIPT_DIR"
}
