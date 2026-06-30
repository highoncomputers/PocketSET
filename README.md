<div align="center">
  <h1>PocketSET v2.0</h1>
  <p><strong>Interactive TUI wrapper for the Social-Engineer Toolkit (SET)</strong></p>
  <p><em>Dual-Platform: Android (Termux) + Linux (Kali / Debian / Ubuntu)</em></p>
</div>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://github.com/highoncomputers/PocketSET/actions/workflows/ci.yml"><img src="https://github.com/highoncomputers/PocketSET/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue" alt="Python"></a>
  <a href="https://github.com/highoncomputers/PocketSET/releases"><img src="https://img.shields.io/github/v/release/highoncomputers/PocketSET" alt="Release"></a>
  <a href="https://github.com/highoncomputers/PocketSET/stargazers"><img src="https://img.shields.io/github/stars/highoncomputers/PocketSET" alt="Stars"></a>
</p>

<p align="center">
  <a href="#quick-install-one-command">Install</a> ·
  <a href="#usage">Usage</a> ·
  <a href="#features">Features</a> ·
  <a href="#screenshots">Screenshots</a> ·
  <a href="#faq">FAQ</a> ·
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

---

PocketSET provides a beginner-friendly terminal user interface for SET. No flags, no syntax, just guided menus and forms.

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

## Quick Install (One Command)

### Termux (Android)
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/highoncomputers/PocketSET/main/install.sh)"
source ~/.bashrc
pocketset
```

### Kali Linux
```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/highoncomputers/PocketSET/main/install.sh)"
pocketset
```

### Other Linux (Debian / Ubuntu)
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/highoncomputers/PocketSET/main/install.sh)"
pocketset
```

The installer auto-detects your platform and asks for confirmation. It installs SET, Metasploit, and all Python dependencies automatically.

## Manual Install
```bash
git clone https://github.com/highoncomputers/PocketSET.git && cd PocketSET
bash install.sh
pocketset
```

## Usage

```bash
pocketset
```

### Main Menu
| # | Option |
|---|--------|
| 1 | Social-Engineering Attacks (spear-phishing, web, media, payloads, mailer, Teensy, wireless, QR, PS) |
| 2 | Fast-Track Penetration Testing (MSSQL, exploits, SCCM, DRAC, RID, PSExec) |
| 3 | Third Party Modules |
| 4 | Update SET |
| 5 | Update SET Configuration |
| 6 | Help & About |
| 7 | Attack Presets (save/load) |
| 8 | Plugins (extend with custom scripts) |
| 9 | Attack History (view past runs) |
| 99 | Exit |

## Screenshots

<!-- Screenshots will be added once a demo environment is available -->
<p align="center">
  <i>Demo screenshots and GIFs coming soon. The TUI interface features a rich terminal dashboard with real-time output streaming and highlight detection.</i>
</p>

## Features

- **Dual-platform**: Auto-detects Termux (Android) vs Kali vs Other Linux, adjusts paths + deps
- **Schema-driven wizards**: Parameter collection driven by `schema.json` — easy to extend
- **Input history**: Frequently entered values (IPs, ports, URLs) remembered across sessions
- **Attack presets**: Save/load attack configurations as JSON files
- **Attack history**: Every run logged with timestamp, params, and success status
- **Live output streaming**: Watch SET execute in real-time with syntax-highlighted output
- **Smart filtering**: Deduplicates repetitive SET output, highlights key events
- **Pre-flight checks**: Optional ping/port checks before launching attacks
- **Auto-update**: Checks GitHub for new PocketSET versions on startup
- **Report generation**: Save attack output as HTML reports
- **Plugin system**: Extend with custom JSON-defined scripts
- **Batch mode**: Run same attack against multiple targets from a file
- **Full input validation**: IP, port, URL, email, CIDR, hostname, file paths
- **Error handling**: Every error caught, logged, displayed clearly
- **Process cleanup**: try/finally on all subprocesses + pexpect, no orphans
- **Pexpect fallback**: Graceful degradation when pexpect is unavailable

## Presets (Examples)

Pre-built attack configurations in `~/.pocketset/presets/`:
- **Clone Login Page** — spear-phish with cloned login + attachment
- **Rogue AP** — wireless credential harvesting with DNS spoofing
- **Teensy USB** — PowerShell reverse shell via USB HID
- **MSSQL Brute** — CIDR scan + SA account brute force
- **QR Code** — malicious URL QR code generator

## Directory Structure
```
~/.pocketset/
├── config.json              # Platform config
├── disclaimer_accepted      # Legal acceptance marker
├── input_history.json       # Input history (IPs, URLs, etc.)
├── history.jsonl            # Attack execution history
├── logs/                    # Error + debug logs
│   └── pocketset.log
├── presets/                 # Saved attack configurations
├── plugins/                 # Custom plugin JSON files
├── reports/                 # HTML attack reports
└── temp/                    # Temporary automate scripts
```

## Plugin Development

Drop a `.json` file into `~/.pocketset/plugins/`:
```json
{
  "name": "My Custom Exploit",
  "description": "Runs a custom Python script",
  "params": [
    {"key": "target", "label": "Target IP", "default": ""}
  ],
  "script_path": "/home/user/my_exploit.py",
  "timeout": 300
}
```

## Config Reference

`~/.pocketset/config.json` controls behavior:
```json
{
  "platform": "auto",
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
  "pre_flight_ping": true,
  "auto_update": true
}
```

## FAQ

| Question | Answer |
|----------|--------|
| Does PocketSET work without SET installed? | No. The installer handles SET installation automatically. |
| Can I use this on Windows? | Not directly. Use WSL with Kali or Ubuntu. |
| Does it work on non-rooted Android? | Yes, via Termux proot. Some features (wireless) require root. |
| How do I update? | PocketSET checks for updates on every launch. Or re-run the installer. |
| Can I contribute translations? | Yes! Open a PR or issue with your language. |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `setoolkit: command not found` | Run installer again or `pip install -e .` from SET source |
| `ModuleNotFoundError: No module named 'rich'` | `pip install rich pexpect Pillow qrcode` |
| `Not running as root` | Most SET attacks require root |
| `pexpect not available` | Fallback mode active. `pip install pexpect` |
| `Metasploit not found` | MSF-dependent attacks only. Install via apt or Rapid7 script |
| Wireless on Termux | Not supported (no monitor mode in proot) |

## Repository
- **GitHub**: https://github.com/highoncomputers/PocketSET
- **Original SET**: https://github.com/trustedsec/social-engineer-toolkit

## Credits
- **SET Author**: David Kennedy (ReL1K) / TrustedSec
- **PocketSET**: Interactive TUI wrapper for simplified SET usage

---

*Hack the Gibson...and remember...hugs are worth more than hands. Also read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) before opening issues.*
