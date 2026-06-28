# PocketSET v2.0

**Interactive TUI wrapper for the Social-Engineer Toolkit (SET)**
**Dual-Platform: Android (Termux) + Linux (Kali / Debian / Ubuntu)**

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

## Features

- **Dual-platform**: Auto-detects Termux (Android) vs Kali vs Other Linux, adjusts paths + deps
- **Schema-driven wizards**: Parameter collection driven by `schema.json` — easy to extend
- **Input history**: Frequently entered values (IPs, ports, URLs) remembered across sessions
- **Attack presets**: Save/load attack configurations as JSON files
- **Attack history**: Every run logged with timestamp, params, and success status
- **Live output streaming**: Watch SET execute in real-time
- **Pre-flight checks**: Optional ping/port checks before launching attacks
- **Auto-update**: Checks GitHub for new PocketSET versions on startup
- **Report generation**: Save attack output as HTML reports
- **Plugin system**: Extend with custom JSON-defined scripts
- **Batch mode**: Run same attack against multiple targets from a file
- **Full input validation**: IP, port, URL, email, CIDR, hostname, file paths
- **Error handling**: Every error caught, logged, displayed clearly
- **Process cleanup**: try/finally on all subprocesses + pexpect, no orphans

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
*Hack the Gibson...and remember...hugs are worth more than handshakes.*
