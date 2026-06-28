# PocketSET

**Interactive TUI wrapper for the Social-Engineer Toolkit (SET)**

PocketSET provides a beginner-friendly terminal user interface for SET. No terminal knowledge required — no flags, no syntax, just guided menus and forms.

## Legal Disclaimer

> **The Social-Engineer Toolkit (SET) is a penetration testing framework for AUTHORIZED security assessments ONLY.**
>
> By using PocketSET you agree that:
> - You have explicit written permission to test the target systems, networks, and/or personnel
> - You will not use SET for any illegal or unauthorized purpose
> - You accept full responsibility for any consequences arising from your use of this tool
> - You comply with all applicable local, state, federal, and international laws
>
> **Unauthorized use is a criminal offence.**

## Requirements

- **Python 3.8+** (tested on Python 3.13)
- **setoolkit** (Social-Engineer Toolkit) — installed automatically on Debian/Kali
- **Debian trixie** / Kali Linux / Ubuntu (other distros may work)

## Quick Install (One Command)

### Option 1 — curl (recommended)
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/highoncomputers/PocketSET/main/install.sh)"
pocketset
```

### Option 2 — git clone
```bash
git clone https://github.com/highoncomputers/PocketSET.git && cd PocketSET && bash install.sh && pocketset
```

### Option 3 — manual
```bash
pip install rich pexpect Pillow qrcode
chmod +x wrapper.py
ln -sf "$(pwd)/wrapper.py" /usr/local/bin/pocketset
pocketset
```

### For Termux / Proot (Debian trixie)

Termux proot runs as root with no `sudo`. The install script auto-detects this:

```bash
pkg install git curl -y
git clone https://github.com/highoncomputers/PocketSET.git
cd PocketSET
bash install.sh
source ~/.bashrc
pocketset
```

Or one-liner:
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/highoncomputers/PocketSET/main/install.sh)" && source ~/.bashrc && pocketset
```

## Usage

Simply run:

```bash
sudo pocketset
```

If `setoolkit` is in your PATH without root, you can also run:

```bash
pocketset
```

### Navigation

1. Accept the **Legal Disclaimer** (once per session)
2. Select from the **Main Menu**:
   - **1** — Social-Engineering Attacks (spear-phishing, web attacks, infectious media, payloads, mass mailer, Teensy, wireless, QR codes, PowerShell)
   - **2** — Fast-Track Penetration Testing (MSSQL bruter, custom exploits, SCCM, DRAC, RID enumeration, PSExec)
   - **3** — Third Party Modules
   - **4** — Update SET
   - **5** — Update SET Configuration
   - **6** — Help & About
   - **99** — Exit
3. Follow the **wizard prompts** for your chosen attack
4. **Confirm** the attack details
5. Watch **real-time output** as SET executes

### Examples

#### Website Attack (Credential Harvester)

```
Main Menu → 1) Social-Engineering Attacks
  → 2) Website Attack Vectors
  → 3) Credential Harvester Attack Method
  → 2) Site Cloner
  → Enter URL: https://example.com
  → Enter LHOST: 192.168.1.100
  → Confirm → Execute
```

#### QRCode Generator

```
Main Menu → 1) Social-Engineering Attacks
  → 8) QRCode Generator Attack Vector
  → Enter URL: https://malicious.com
  → Confirm → Generate QR code
```

## Directory Structure

```
~/.pocketset/
├── disclaimer_accepted     # Legal disclaimer acceptance marker
├── logs/                   # Error logs
│   └── error_*.log
└── temp/                   # Temporary automate scripts
    └── automate_*.txt
```

## Features

- **Full menu tree** — all SET attack vectors accessible via clean TUI
- **Input validation** — IP addresses, ports, URLs, files, emails all validated
- **Real-time output** — watch SET execute with live streaming
- **Wizard-based** — step-by-step guided parameter collection
- **Auto-install** — install script handles SET + dependencies
- **Error handling** — every error caught, logged, and displayed clearly
- **Graceful exit** — Ctrl+C cleanup, no orphan processes
- **No terminal knowledge required** — radio buttons, checkboxes, validated text fields

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `setoolkit: command not found` | Run `apt install set` or install from source |
| `ModuleNotFoundError: No module named 'rich'` | Run `pip install rich pexpect Pillow qrcode` |
| `Not running as root` | Most SET attacks require root. Run `sudo pocketset` |
| `pexpect not available` | Fallback mode active. Run `pip install pexpect` |
| `Metasploit not found` | Only MSF-dependent attacks disabled. Install with `apt install metasploit-framework` |

## Repository

- **GitHub**: https://github.com/highoncomputers/PocketSET
- **Original SET**: https://github.com/trustedsec/social-engineer-toolkit

## Credits

- **SET Author**: David Kennedy (ReL1K) / TrustedSec
- **PocketSET**: Interactive TUI wrapper for simplified SET usage

---

*Hack the Gibson...and remember...hugs are worth more than handshakes.*
