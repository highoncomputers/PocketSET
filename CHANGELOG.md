# Changelog

## [2.0.0] - 2026-06-28

### Added
- Interactive TUI wrapper for SET with guided menus and forms
- Dual-platform support: Termux (Android) + Kali/Linux
- Schema-driven parameter wizards with full input validation
- Input history with persistent storage
- Attack presets (save/load JSON configurations)
- Attack history with execution logging
- Live output streaming and real-time display
- Pre-flight connectivity checks (ping/port)
- Auto-update checking via GitHub API
- HTML report generation
- Plugin system with JSON-defined custom scripts
- Batch mode for multi-target attacks
- Process cleanup with try/finally guarantees
- Support for all major SET attack vectors:
  - Spear-Phishing (file format + mass mailer)
  - Web attack vectors (cloning, credential harvesting)
  - Media generation
  - Payload generation
  - Mailer attacks
  - Teensy USB / Arduino
  - Wireless AP attacks
  - QR Code generation
  - PowerShell attacks
