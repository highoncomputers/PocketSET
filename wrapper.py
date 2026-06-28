#!/usr/bin/env python3
"""PocketSET v2.0 — Interactive TUI wrapper for the Social-Engineer Toolkit"""

import os, sys, re, json, shutil, signal, textwrap, time, subprocess, socket
import logging, traceback, threading, importlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Union, Any

# ── Rich imports ──────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich.columns import Columns
    from rich import box
    from rich.prompt import Prompt, IntPrompt, Confirm as RichConfirm
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.syntax import Syntax
    from rich.rule import Rule
    from rich.align import Align
    from rich.markup import escape
except ImportError as e:
    print(f"Error: rich is required. Install: pip install rich\n{e}")
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────────────
try:
    BASE_DIR = Path(__file__).resolve().parent
except NameError:
    BASE_DIR = Path("/opt/PocketSET")
    if not BASE_DIR.exists():
        BASE_DIR = Path.cwd()

SCHEMA_PATH       = BASE_DIR / "schema.json"
POCKETSET_DIR     = Path.home() / ".pocketset"
LOGS_DIR          = POCKETSET_DIR / "logs"
TEMP_DIR          = POCKETSET_DIR / "temp"
CONFIG_PATH       = POCKETSET_DIR / "config.json"
HISTORY_PATH      = POCKETSET_DIR / "history.jsonl"
INPUT_HIST_PATH   = POCKETSET_DIR / "input_history.json"
PRESETS_DIR       = POCKETSET_DIR / "presets"
PLUGINS_DIR       = POCKETSET_DIR / "plugins"
REPORTS_DIR       = POCKETSET_DIR / "reports"

# ── Globals ───────────────────────────────────────────────────────────────────
console = Console()
VERSION = "2.0.0"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG = logging.getLogger("pocketset")
LOG.setLevel(logging.DEBUG)
_fh = logging.FileHandler(LOGS_DIR / "pocketset.log", encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
LOG.addHandler(_fh)
_ch = logging.StreamHandler(sys.stdout)
_ch.setLevel(logging.WARNING)
_ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
LOG.addHandler(_ch)

# ── Schema ────────────────────────────────────────────────────────────────────
with open(str(SCHEMA_PATH)) as f:
    SCHEMA = json.load(f)
MENU_TREE = SCHEMA["menu_tree"]

def _load_validation() -> dict:
    vpath = BASE_DIR / "validation.json"
    if vpath.exists():
        return json.loads(vpath.read_text())
    return {}
VAL_SCHEMA = _load_validation()

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_CONFIG: dict[str, Any] = {
    "platform": "auto",
    "theme": {
        "header": "bold cyan",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "white",
        "muted": "dim white",
    },
    "pexpect_delay": 0.3,
    "timeout_seconds": 600,
    "history_size": 100,
    "auto_update": True,
    "pre_flight_ping": True,
    "default_smtp": "",
    "default_lhost": "",
    "default_port": "443",
}

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text())
            merged = DEFAULT_CONFIG.copy()
            merged.update(cfg)
            return merged
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))

CONFIG = load_config()

# ── Platform Detection ────────────────────────────────────────────────────────
class Platform:
    @staticmethod
    def is_termux() -> bool:
        return "com.termux" in str(Path.home()) or "TERMUX_VERSION" in os.environ

    @staticmethod
    def is_kali() -> bool:
        try:
            r = subprocess.run(["grep", "-qi", "kali", "/etc/os-release"],
                               capture_output=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    @staticmethod
    def is_proot() -> bool:
        return os.path.exists("/data/data/com.termux/files/usr/bin/proot") or \
               "PROOT_TMP_DIR" in os.environ

    @staticmethod
    def detect() -> str:
        if Platform.is_termux():
            return "termux"
        if Platform.is_kali():
            return "kali"
        return "linux"

    @staticmethod
    def name() -> str:
        return Platform.detect().title()

# ── Colors (from config) ──────────────────────────────────────────────────────
class Colors:
    HEADER  = CONFIG["theme"]["header"]
    SUCCESS = CONFIG["theme"]["success"]
    ERROR   = CONFIG["theme"]["error"]
    WARNING = CONFIG["theme"]["warning"]
    INFO    = CONFIG["theme"]["info"]
    MUTED   = CONFIG["theme"]["muted"]

# ── Utility functions ─────────────────────────────────────────────────────────
def _ensure_dirs() -> None:
    for d in (POCKETSET_DIR, LOGS_DIR, TEMP_DIR, PRESETS_DIR, PLUGINS_DIR, REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)

def _cleanup_temp() -> None:
    if TEMP_DIR.exists():
        for f in TEMP_DIR.iterdir():
            try: f.unlink()
            except: pass
        try: TEMP_DIR.rmdir()
        except: pass

def _safe_input(prompt_str: str = "") -> str:
    try:
        return input(prompt_str)
    except (EOFError, KeyboardInterrupt):
        return ""

def signal_handler(sig, frame) -> None:
    console.print("\n[yellow]Shutting down PocketSET...[/]")
    _cleanup_temp()
    console.print("[yellow]Hack the Gibson...and remember...hugs are worth more than handshakes.[/]")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ── Validators ────────────────────────────────────────────────────────────────
def validate_ip(ip: str) -> bool:
    m = re.match(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$', ip.strip())
    if not m:
        return False
    return all(0 <= int(g) <= 255 for g in m.groups())

def validate_port(p: str) -> bool:
    try:
        return 1 <= int(p.strip()) <= 65535
    except (ValueError, TypeError):
        return False

def validate_url(url: str) -> bool:
    u = url.strip()
    if not u.startswith(('http://', 'https://')):
        return False
    return bool(re.match(r'^https?://[^\s/$.?#].[^\s]*$', u))

def validate_email(e: str) -> tuple[bool, str]:
    if bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', e.strip())):
        return True, ""
    return False, "Invalid email format"

def validate_file_read(p: str) -> tuple[bool, str]:
    if Path(p.strip()).expanduser().exists():
        return True, ""
    return False, "File not found"

def validate_cidr(c: str) -> bool:
    c = c.strip()
    m = re.match(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/(\d{1,2})$', c)
    if not m:
        return False
    return all(0 <= int(g) <= 255 for g in m.group(1).split('.')) and 0 <= int(m.group(2)) <= 32

def validate_hostname(h: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$', h.strip()))

class Validator:
    @staticmethod
    def validate(val_type: str, value: str, rules: dict) -> tuple[bool, str]:
        v = value.strip()
        if not v and rules.get("required", False):
            return False, "This field is required."
        if not v and not rules.get("required", False):
            return True, ""
        custom = rules.get("custom", "")
        if custom == "validate_ip":
            if not validate_ip(v):
                return False, rules.get("error_message", "Invalid IP address")
            return True, ""
        if custom == "validate_port":
            if not validate_port(v):
                return False, rules.get("error_message", "Port must be 1-65535")
            return True, ""
        if custom == "validate_url":
            if not validate_url(v):
                return False, rules.get("error_message", "Invalid URL format")
            return True, ""
        if custom == "validate_file_read":
            ok, _ = validate_file_read(v)
            if not ok:
                return False, rules.get("error_message", "File not found")
            return True, ""
        if custom == "validate_cidr_or_file":
            file_ok, _ = validate_file_read(v)
            if validate_cidr(v) or validate_ip(v) or file_ok:
                return True, ""
            return False, rules.get("error_message", "Invalid CIDR, IP, or file path")
        if custom == "validate_target":
            if validate_ip(v) or validate_hostname(v):
                return True, ""
            return False, rules.get("error_message", "Enter a valid IP or hostname")
        if custom == "validate_emails":
            parts = [e.strip() for e in v.replace('\n', ',').split(',') if e.strip()]
            if not parts:
                return False, "Enter at least one email"
            for e in parts:
                ok, _ = validate_email(e)
                if not ok:
                    return False, f"Invalid email: {e}"
            return True, ""
        pattern = rules.get("pattern", "")
        if pattern and not re.match(pattern, v):
            return False, rules.get("error_message", "Invalid format")
        min_len = rules.get("min_length", 0)
        max_len = rules.get("max_length", 0)
        if min_len and len(v) < min_len:
            return False, f"Minimum {min_len} characters"
        if max_len and len(v) > max_len:
            return False, f"Maximum {max_len} characters"
        try:
            min_v = rules.get("min")
            max_v = rules.get("max")
            if min_v is not None or max_v is not None:
                n = int(v)
                if min_v is not None and n < min_v:
                    return False, f"Minimum value: {min_v}"
                if max_v is not None and n > max_v:
                    return False, f"Maximum value: {max_v}"
        except Exception:
            pass
        return True, ""

# ── Display helpers ───────────────────────────────────────────────────────────
def show_banner() -> None:
    banner = textwrap.dedent(f"""\
    [bold cyan]\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
    \u2551         PocketSET v{VERSION}                  \u2551
    \u2551  Social-Engineer Toolkit \u2014 Interactive TUI   \u2551
    \u2551         Platform: {Platform.name():<14}   \u2551
    \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d[/]""")
    console.print()
    console.print(Panel(banner, border_style="cyan", box=box.DOUBLE_EDGE))
    console.print()

def show_error(title: str, message: str) -> None:
    console.print(Panel(f"[red]{message}[/]", title=f"[bold red]{title}[/]", border_style="red"))

def show_success(title: str, message: str) -> None:
    console.print(Panel(f"[green]{message}[/]", title=f"[bold green]{title}[/]", border_style="green"))

def show_warning(title: str, message: str) -> None:
    console.print(Panel(f"[yellow]{message}[/]", title=f"[bold yellow]{title}[/]", border_style="yellow"))

def show_info(message: str) -> None:
    console.print(f"[dim]\u2503[/] {message}")

def show_rule() -> None:
    console.print(Rule(style="dim"))

def prompt_text(label: str, default: str = "", password: bool = False,
                validate: Optional[Callable] = None,
                error_msg: str = "",
                history: Optional[list] = None) -> str:
    while True:
        d = f" [{default}]" if default else ""
        try:
            if password:
                val = Prompt.ask(f"[bold]{label}[/]{d}", password=True)
            else:
                val = Prompt.ask(f"[bold]{label}[/]{d}")
        except (EOFError, KeyboardInterrupt):
            return default or ""
        if not val and default:
            val = default
        if validate:
            ok, msg = validate(val.strip())
            if not ok:
                show_error("Validation Error", msg or error_msg)
                continue
        result = val.strip()
        if history is not None:
            h = [x for x in history if x != result]
            h.insert(0, result)
            history[:] = h[:CONFIG.get("history_size", 100)]
        return result

def prompt_confirm(label: str, default: bool = False) -> bool:
    try:
        return RichConfirm.ask(f"[bold]{label}[/]", default=default)
    except (EOFError, KeyboardInterrupt):
        return default

def prompt_choice(title: str, options: dict, prompt_text_str: str = "Select an option") -> str:
    console.print(f"\n[bold cyan]{title}[/]")
    show_rule()
    table = Table(box=box.SIMPLE, show_header=False, border_style="dim")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Option", style="white")
    for k, v in options.items():
        table.add_row(str(k), str(v))
    console.print(table)
    show_rule()
    while True:
        try:
            choice = Prompt.ask(f"[bold]{prompt_text_str}[/]")
        except (EOFError, KeyboardInterrupt):
            return "99"
        if choice in options:
            return choice
        show_error("Invalid Choice", f"Enter a valid option: {', '.join(options.keys())}")

def prompt_numbered_list(title: str, items: list, prompt_text_str: str = "Select an option") -> str:
    options = {str(i+1): item for i, item in enumerate(items)}
    return prompt_choice(title, options, prompt_text_str)

# ── Input history ─────────────────────────────────────────────────────────────
class InputHistory:
    _data: dict[str, list[str]] = {}

    @classmethod
    def load(cls) -> None:
        if INPUT_HIST_PATH.exists():
            try:
                cls._data = json.loads(INPUT_HIST_PATH.read_text())
            except Exception:
                cls._data = {}

    @classmethod
    def save(cls) -> None:
        INPUT_HIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            INPUT_HIST_PATH.write_text(json.dumps(cls._data, indent=2))
        except Exception:
            pass

    @classmethod
    def get(cls, key: str) -> list[str]:
        return cls._data.get(key, [])

    @classmethod
    def push(cls, key: str, value: str) -> None:
        h = cls._data.setdefault(key, [])
        h2 = [x for x in h if x != value]
        h2.insert(0, value)
        cls._data[key] = h2[:CONFIG.get("history_size", 100)]

InputHistory.load()

# ── Disclaimer ────────────────────────────────────────────────────────────────
class Disclaimer:
    DISCLAIMER_FILE = POCKETSET_DIR / "disclaimer_accepted"

    @classmethod
    def is_accepted(cls) -> bool:
        return cls.DISCLAIMER_FILE.exists()

    @classmethod
    def mark_accepted(cls) -> None:
        cls.DISCLAIMER_FILE.parent.mkdir(parents=True, exist_ok=True)
        cls.DISCLAIMER_FILE.write_text(f"accepted on {datetime.now().isoformat()}\n")

    @classmethod
    def show(cls) -> bool:
        if cls.is_accepted():
            return True
        console.clear()
        panel_text = (
            "[bold red]The Social-Engineer Toolkit (SET) is a penetration testing\n"
            "framework for AUTHORIZED security assessments ONLY.[/]\n\n"
            "By using PocketSET you agree that:\n\n"
            "  [white]\u2022 You have explicit written permission to test the\n"
            "    target systems, networks, and/or personnel\n"
            "  \u2022 You will not use SET for any illegal or unauthorized\n"
            "    purpose\n"
            "  \u2022 You accept full responsibility for any consequences\n"
            "    arising from your use of this tool\n"
            "  \u2022 You comply with all applicable local, state, federal,\n"
            "    and international laws[/]\n\n"
            "[bold red]Unauthorized use is a criminal offence.[/]\n\n"
            "[dim]This disclaimer is displayed once per session.[/]"
        )
        console.print(Panel(panel_text, border_style="red", title="[bold red]LEGAL DISCLAIMER[/]"))
        console.print()
        val = Prompt.ask("[bold red]Type I AGREE to accept, or anything else to exit[/]")
        if val.strip().upper() == "I AGREE":
            cls.mark_accepted()
            return True
        console.print("[red]Exiting. You must accept the disclaimer to use PocketSET.[/]")
        return False

# ── Dependency Checker ────────────────────────────────────────────────────────
class DependencyChecker:
    TERMUX_SET_PATHS = [
        "/data/data/com.termux/files/usr/local/bin/setoolkit",
        "/data/data/com.termux/files/usr/bin/setoolkit",
    ]

    @staticmethod
    def find_setoolkit() -> str:
        candidates = ["setoolkit", "seautomate", "./setoolkit"]
        if Platform.is_termux():
            candidates = DependencyChecker.TERMUX_SET_PATHS + candidates
        candidates += [
            "/usr/local/share/setoolkit/setoolkit",
            "/usr/local/bin/setoolkit",
            "/opt/setoolkit/setoolkit",
        ]
        for c in candidates:
            if "/" in c:
                p = Path(c)
                if p.is_file() and os.access(str(p), os.X_OK):
                    return str(p.resolve())
            else:
                found = shutil.which(c)
                if found:
                    return found
        return ""

    @staticmethod
    def check_setoolkit() -> bool:
        return bool(DependencyChecker.find_setoolkit())

    @staticmethod
    def check_metasploit() -> bool:
        if Platform.is_termux():
            paths = ["/data/data/com.termux/files/usr/bin/msfconsole",
                     "/data/data/com.termux/files/usr/local/bin/msfconsole"]
            for p in paths:
                if Path(p).is_file():
                    return True
        r = subprocess.run(["which", "msfconsole"], capture_output=True, text=True, timeout=30)
        return r.returncode == 0

    @staticmethod
    def check_pexpect() -> bool:
        return importlib.util.find_spec("pexpect") is not None

    @staticmethod
    def install_pexpect() -> bool:
        show_info("Installing pexpect...")
        from pip._internal.cli.main import main as pip_main
        r = subprocess.run([sys.executable, "-m", "pip", "install", "pexpect", "-q"],
                           capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            show_success("Success", "pexpect installed")
            return True
        show_error("Install Failed", f"Could not install pexpect:\n{r.stderr}")
        return False

    @staticmethod
    def check_docker() -> bool:
        r = subprocess.run(["which", "docker"], capture_output=True, text=True, timeout=10)
        return r.returncode == 0

# ── Auto-Update ───────────────────────────────────────────────────────────────
class AutoUpdater:
    @staticmethod
    def check() -> Optional[str]:
        if not CONFIG.get("auto_update", True):
            return None
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://api.github.com/repos/highoncomputers/PocketSET/releases/latest",
                headers={"User-Agent": "PocketSET/2.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                latest = data.get("tag_name", "").lstrip("v")
                if latest and latest > VERSION:
                    return latest
        except Exception:
            pass
        return None

    @staticmethod
    def update() -> bool:
        show_info("Updating PocketSET via git pull...")
        r = subprocess.run(["git", "-C", str(BASE_DIR), "pull", "--ff-only"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            show_success("Updated", "PocketSET updated. Please restart.")
            return True
        show_error("Update Failed", r.stderr[:500])
        return False

# ── Automate Script Builder ───────────────────────────────────────────────────
class AutomateScriptBuilder:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.script_path = TEMP_DIR / f"automate_{int(time.time())}.txt"

    def add(self, line: str) -> None:
        self.lines.append(line if line else "")

    def add_many(self, *lines: str) -> None:
        for l in lines:
            self.add(l)

    def add_blank(self) -> None:
        self.lines.append("")

    def write(self) -> Path:
        text = "\n".join(self.lines) + "\n"
        self.script_path.parent.mkdir(parents=True, exist_ok=True)
        self.script_path.write_text(text)
        return self.script_path

    def build_social_engineering(self, main_choice: str, sub_choice: str, params: dict) -> None:
        self.add("1")
        self.add(main_choice)
        attack_choice = sub_choice
        self.add(attack_choice)

        if main_choice == "2":
            source_choice = params.get("web_source", "2")
            self.add(source_choice)
            if source_choice == "2":
                self.add(params.get("url", ""))
            elif source_choice == "3":
                self.add(params.get("import_path", ""))
            self.add(params.get("lhost", ""))
        elif main_choice == "3":
            media_type = params.get("media_type", "1")
            self.add(media_type)
            if media_type == "1":
                self.add(params.get("lhost", ""))
        elif main_choice == "4":
            self.add(params.get("payload_type", "1"))
            self.add(params.get("meterpreter_payload", "2"))
            self.add(params.get("lhost", ""))
            self.add(params.get("lport", "443"))
            self.add(params.get("encoding", "4"))
        elif main_choice == "5":
            self.add("1")
            self.add(params.get("smtp_server", ""))
            self.add(params.get("from_email", ""))
            self.add(params.get("to_emails", ""))
            self.add(params.get("subject", ""))
            self.add(params.get("body", ""))
            if params.get("email_list_file"):
                self.add(params["email_list_file"])
            else:
                self.add("")
        elif main_choice == "6":
            self.add(sub_choice)
            tt = int(sub_choice)
            if tt in (1, 2, 3, 4, 5, 6, 12, 14):
                self.add(params.get("lhost", ""))
                self.add(params.get("lport", "443"))
        elif main_choice == "7":
            self.add(params.get("wireless_action", "1"))
            if params.get("wireless_action") == "1":
                self.add(params.get("ssid", "Free WiFi"))
                self.add(params.get("channel", "6"))
                self.add(params.get("interface", "wlan0"))
        elif main_choice == "8":
            self.add(params.get("qr_url", ""))
        elif main_choice == "9":
            self.add(sub_choice)
            pt = int(sub_choice)
            if pt in (1, 2, 3):
                self.add(params.get("lhost", ""))
                self.add(params.get("lport", "443"))
        elif main_choice == "1":
            pass  # attack_type already sent as attack_choice

    def build_fasttrack(self, main_choice: str, sub_choice: str, params: dict) -> None:
        self.add("2")
        self.add(main_choice)
        if main_choice == "1":
            self.add(sub_choice)
            if sub_choice == "1":
                self.add(params.get("scan_source", "1"))
                if params.get("scan_source") == "1":
                    self.add(params.get("target_cidr", ""))
                else:
                    self.add(params.get("target_file", ""))
                self.add(params.get("port", "1433"))
                self.add(params.get("wordlist", "default"))
                self.add(params.get("username", "sa"))
            else:
                self.add(params.get("target", ""))
                self.add(params.get("port", "1433"))
                self.add(params.get("username", "sa"))
                self.add(params.get("password", ""))
        elif main_choice == "2":
            self.add(sub_choice)
            self.add(params.get("target", ""))
            self.add(params.get("port", "445"))

    def get_preview(self) -> str:
        return "\n".join(self.lines)

# ── SET Executor with Live Output ─────────────────────────────────────────────
class SETExecutor:
    def __init__(self, script_path: Path, timeout: int = 600) -> None:
        self.script_path = script_path
        self.timeout = timeout
        self.output_lines: list[str] = []
        self.setoolkit_cmd = DependencyChecker.find_setoolkit() or "setoolkit"
        self._running = False

    def _resolve_cmd(self) -> str:
        cmd = self.setoolkit_cmd
        if "/" not in cmd and not cmd.startswith("./"):
            r = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                cmd = r.stdout.strip()
        return cmd

    def _run_pexpect_live(self, progress) -> tuple[str, bool]:
        import pexpect
        import pexpect.exceptions as pexcp
        child = None
        output: list[str] = []
        cmd = self._resolve_cmd()
        self._running = True
        try:
            child = pexpect.spawn(
                cmd,
                timeout=self.timeout,
                encoding="utf-8",
                codec_errors="replace",
                env={**os.environ, "TERM": "xterm-256color", "POCKETSET": "1"}
            )
            try:
                child.expect(r"99\) Exit the Social-Engineer Toolkit", timeout=120)
            except pexcp.TIMEOUT:
                return "\n".join(output) + "\n[!] Initial menu load timed out", True
            except pexcp.EOF:
                return "\n".join(output) + "\n[!] SET exited before menu loaded", True
            output.append(child.before or "")
            script_text = self.script_path.read_text()
            total_lines = len([l for l in script_text.split("\n") if l.strip()])
            sent = 0
            for line in script_text.split("\n"):
                if not self._running:
                    break
                child.sendline(line.strip() if line.strip() else "")
                sent += 1
                if progress:
                    progress.update(progress.task_ids[0] if progress.task_ids else None,
                                    description=f"[cyan]Sending SET commands... ({sent}/{total_lines})[/]")
                time.sleep(CONFIG.get("pexpect_delay", 0.3))
                try:
                    idx = child.expect([
                        r"99\) Exit the Social-Engineer Toolkit",
                        r"99\) Return back to the main menu",
                        pexcp.EOF,
                        pexcp.TIMEOUT,
                    ], timeout=15)
                    before = child.before or ""
                    after = child.after or ""
                    chunk = before + (str(after) if isinstance(after, str) else "")
                    if chunk:
                        output.append(chunk)
                        self.output_lines.append(chunk)
                    if idx == 2:
                        break
                except pexcp.EOF:
                    break
            try:
                child.expect(pexcp.EOF, timeout=120)
                output.append(child.before or "")
            except Exception:
                pass
        finally:
            self._running = False
            if child:
                try:
                    child.close(force=True)
                except Exception:
                    pass
        return "\n".join(output), False

    def _run_subprocess_live(self, progress) -> tuple[str, bool]:
        script_text = self.script_path.read_text()
        cmd = self._resolve_cmd()
        proc = None
        stdout_lines: list[str] = []
        self._running = True
        try:
            proc = subprocess.Popen(
                cmd if "/" in cmd else [cmd],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env={**os.environ, "TERM": "xterm-256color", "POCKETSET": "1"}
            )
            def reader() -> None:
                for line in proc.stdout:
                    stdout_lines.append(line)
                    self.output_lines.append(line)
            t = threading.Thread(target=reader, daemon=True)
            t.start()
            try:
                for line in script_text.split("\n"):
                    if not self._running:
                        break
                    proc.stdin.write(line + "\n")
                    proc.stdin.flush()
                    time.sleep(CONFIG.get("pexpect_delay", 0.3))
                proc.stdin.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                return "".join(stdout_lines) + "\n[red]Command timed out[/]", True
            t.join(timeout=5)
        finally:
            self._running = False
            if proc and proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
        return "".join(stdout_lines), False

    def execute(self, progress=None) -> str:
        try:
            if DependencyChecker.check_pexpect():
                output, _ = self._run_pexpect_live(progress)
                return output
            else:
                output, _ = self._run_subprocess_live(progress)
                return output
        except FileNotFoundError:
            return "ERROR: setoolkit not found. Install SET first."
        except Exception as e:
            LOG.exception("Execution error: %s", e)
            return f"ERROR: {e}"

    def stop(self) -> None:
        self._running = False

# ── Attack History ────────────────────────────────────────────────────────────
class AttackHistory:
    @staticmethod
    def record(attack_name: str, params: dict, output: str, success: bool) -> None:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "attack": attack_name,
            "params": {k: v for k, v in params.items() if k not in ("password",)},
            "success": success,
            "platform": Platform.detect(),
        }
        try:
            with open(str(HISTORY_PATH), "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    @staticmethod
    def view() -> None:
        if not HISTORY_PATH.exists():
            show_info("No attack history yet.")
            return
        try:
            entries = []
            with open(str(HISTORY_PATH)) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
            if not entries:
                show_info("No attack history yet.")
                return
            table = Table(title="Attack History", box=box.SIMPLE, border_style="dim")
            table.add_column("#", style="cyan", width=4)
            table.add_column("Time", style="yellow", width=20)
            table.add_column("Attack", style="white")
            table.add_column("Status", width=8)
            for i, e in enumerate(entries[-CONFIG.get("history_size", 100):], 1):
                status = "[green]OK[/]" if e.get("success") else "[red]FAIL[/]"
                table.add_row(str(i), e.get("timestamp", "?")[:19], e.get("attack", "?"), status)
            console.print(table)
        except Exception:
            show_error("Error", "Could not read history file.")

# ── Attack Presets ────────────────────────────────────────────────────────────
class AttackPreset:
    @staticmethod
    def save(name: str, attack_type: str, params: dict) -> None:
        PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        path = PRESETS_DIR / f"{name.replace(' ', '_').lower()}.json"
        data = {
            "name": name,
            "attack_type": attack_type,
            "params": {k: v for k, v in params.items() if k not in ("password",)},
            "created": datetime.now().isoformat(),
            "platform": Platform.detect(),
        }
        path.write_text(json.dumps(data, indent=2))
        show_success("Saved", f"Preset saved to {path.name}")

    @staticmethod
    def load() -> Optional[tuple[str, dict]]:
        PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        presets = sorted(PRESETS_DIR.glob("*.json"))
        if not presets:
            show_info("No presets found.")
            return None
        opts = {str(i+1): p.stem for i, p in enumerate(presets)}
        choice = prompt_choice("Load Preset", opts)
        if choice in opts:
            path = presets[int(choice) - 1]
            try:
                data = json.loads(path.read_text())
                show_success("Loaded", f"Preset: {data.get('name', path.stem)}")
                return data.get("attack_type", ""), data.get("params", {})
            except Exception as e:
                show_error("Error", f"Could not load preset: {e}")
        return None

    @staticmethod
    def list_presets() -> list[Path]:
        PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        return sorted(PRESETS_DIR.glob("*.json"))

# ── Schema-Driven Wizard ──────────────────────────────────────────────────────
class SchemaWizard:
    def __init__(self, menu_key: str) -> None:
        self.menu_key = menu_key
        self.params: dict[str, Any] = {}
        self.submenu = SCHEMA["menu_tree"].get(menu_key, {})

    def collect(self) -> dict:
        for param_key in self.submenu.get("params", []):
            rules = VAL_SCHEMA.get(param_key, {})
            val_type = rules.get("type", "string")
            label = rules.get("label", param_key)
            default = rules.get("default", "")
            required = rules.get("required", False)
            custom = rules.get("validation", {}).get("custom", "")
            error_msg = rules.get("error_message", "")
            pattern = rules.get("validation", {}).get("pattern", "")

            if val_type == "enum":
                opts = rules.get("options", {})
                if opts:
                    hist_key = f"enum_{param_key}"
                    choice = prompt_choice(label, opts)
                    self.params[param_key] = choice
                    InputHistory.push(hist_key, choice)
                    continue

            if val_type == "boolean":
                self.params[param_key] = prompt_confirm(label, default=default)
                continue

            if val_type == "password":
                val = prompt_text(label, password=True)
                self.params[param_key] = val
                continue

            if custom:
                validate_fn = lambda v: Validator.validate(
                    val_type, v,
                    {"custom": custom, "required": required,
                     "error_message": error_msg, "pattern": pattern}
                )
            else:
                validate_fn = None

            hist_key = f"input_{param_key}"
            hist = InputHistory.get(hist_key)
            val = prompt_text(label, default=str(default), validate=validate_fn,
                              error_msg=error_msg, history=hist)
            self.params[param_key] = val
            InputHistory.push(hist_key, val)

        return self.params

# ── Pre-Flight Checks ─────────────────────────────────────────────────────────
class PreFlight:
    @staticmethod
    def ping(host: str) -> bool:
        if not CONFIG.get("pre_flight_ping", True):
            return True
        try:
            r = subprocess.run(["ping", "-c1", "-W2", host],
                               capture_output=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    @staticmethod
    def port_open(host: str, port: int, timeout: float = 3.0) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            result = s.connect_ex((host, port))
            s.close()
            return result == 0
        except Exception:
            return False

    @staticmethod
    def check_all(params: dict) -> bool:
        targets = []
        if "target" in params:
            targets.append(params["target"])
        if "lhost" in params:
            targets.append(params["lhost"])
        if not targets:
            return True
        all_ok = True
        for t in set(targets):
            if validate_ip(t) or validate_hostname(t):
                if not PreFlight.ping(t):
                    show_warning("Unreachable", f"{t} did not respond to ping.")
                    if not prompt_confirm("Continue anyway?", True):
                        all_ok = False
        return all_ok

# ── Batch Attack Runner ───────────────────────────────────────────────────────
class BatchRunner:
    @staticmethod
    def run(attack_name: str, builder_fn, params_list: list[dict]) -> None:
        total = len(params_list)
        if total == 0:
            show_info("No targets to attack.")
            return
        show_info(f"Running batch attack on {total} target(s)...")
        for i, p in enumerate(params_list, 1):
            show_info(f"[{i}/{total}] Target: {p.get('target', p.get('lhost', '?'))}")
            builder = AutomateScriptBuilder()
            builder_fn(builder, p)
            script_path = builder.write()
            executor = SETExecutor(script_path)
            output = executor.execute()
            AttackHistory.record(f"{attack_name} [{i}/{total}]", p, output, "ERROR" not in output[:20])
        show_success("Batch Complete", f"Finished {total} attack(s)")

# ── Plugin System ─────────────────────────────────────────────────────────────
class Plugin:
    @staticmethod
    def discover() -> dict[str, dict]:
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        plugins: dict[str, dict] = {}
        for pf in PLUGINS_DIR.glob("*.json"):
            try:
                data = json.loads(pf.read_text())
                pid = data.get("name", pf.stem)
                plugins[pid] = data
            except Exception:
                pass
        return plugins

    @staticmethod
    def run(plugin: dict) -> None:
        show_banner()
        console.print(Panel(f"[bold]{plugin.get('name', 'Plugin')}[/]\n\n"
                            f"{plugin.get('description', '')}", border_style="cyan"))
        show_rule()
        params = {}
        for pdef in plugin.get("params", []):
            pkey = pdef.get("key", "")
            plabel = pdef.get("label", pkey)
            pdefault = pdef.get("default", "")
            val = prompt_text(plabel, default=pdefault)
            params[pkey] = val
        script_path = plugin.get("script_path", "")
        if script_path:
            r = subprocess.run([sys.executable, script_path] +
                               [f"--{k}={v}" for k, v in params.items()],
                               capture_output=True, text=True, timeout=plugin.get("timeout", 300))
            show_info(r.stdout[:2000])
            if r.returncode != 0:
                show_error("Plugin Error", r.stderr[:1000])

# ── Confirm and Execute ───────────────────────────────────────────────────────
def confirm_and_execute(builder: AutomateScriptBuilder, attack_name: str,
                        params: Optional[dict] = None) -> None:
    if params is None:
        params = {}
    script = builder.get_preview()
    console.clear()
    console.print(Panel(
        f"[bold]Attack:[/] {attack_name}\n\n"
        f"[bold]Command sequence that will be sent to setoolkit:[/]\n\n[dim]{escape(script)}[/]",
        title="[yellow]Confirm Attack[/]", border_style="yellow"))
    show_rule()
    show_warning("Warning", "This will execute a real penetration testing attack. Ensure you have authorization.")
    if not prompt_confirm("Proceed with execution?", default=False):
        show_info("Attack cancelled.")
        return

    if not PreFlight.check_all(params):
        show_info("Attack cancelled due to pre-flight checks.")
        return

    script_path = builder.write()
    console.clear()
    show_banner()
    show_info(f"Executing: {attack_name}")
    show_info("Starting SET...")
    executor = SETExecutor(script_path)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  BarColumn(), transient=False) as progress:
        task = progress.add_task("[cyan]Running SET attack...", total=None)
        try:
            output = executor.execute(progress)
        except Exception as e:
            output = f"ERROR: {e}"
            LOG.exception("Execution exception: %s", e)
        progress.update(task, visible=False)

    show_rule()
    success = "ERROR" not in output[:20] or not output.startswith("ERROR")
    if not success:
        show_error("Execution Failed", output)
        LOG.error("SET execution failed:\n%s", output)
    else:
        show_success("Execution Complete", "SET has finished processing.")
        console.print(Panel(output[:3000] if len(output) > 3000 else output,
                           title="[bold]Output[/]", border_style="green"))

    AttackHistory.record(attack_name, params, output, success)
    show_rule()

    if prompt_confirm("Save output to report?"):
        save_report(attack_name, output, params)

# ── Report Generation ─────────────────────────────────────────────────────────
def save_report(attack_name: str, output: str, params: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r'[^\w-]', '_', attack_name.lower())
    rpath = REPORTS_DIR / f"{safe_name}_{ts}.html"
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>PocketSET Report - {escape(attack_name)}</title>
<style>
  body {{ font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 2em; }}
  h1 {{ color: #00d4ff; }}
  .params {{ background: #16213e; padding: 1em; border-radius: 8px; margin: 1em 0; }}
  .output {{ background: #0f3460; padding: 1em; border-radius: 8px; white-space: pre-wrap; }}
  .meta {{ color: #888; font-size: 0.9em; }}
</style></head><body>
<h1>PocketSET Attack Report</h1>
<div class="meta">
  <p>Attack: {escape(attack_name)}</p>
  <p>Time: {datetime.now().isoformat()}</p>
  <p>Platform: {Platform.detect()}</p>
  <p>Version: {VERSION}</p>
</div>
<div class="params">
  <h2>Parameters</h2>
  <pre>{escape(json.dumps({k: v for k, v in params.items() if k != "password"}, indent=2))}</pre>
</div>
<div class="output">
  <h2>Output</h2>
  <pre>{escape(output[:10000])}</pre>
</div>
</body></html>"""
    rpath.write_text(html)
    show_success("Report Saved", f"Report: {rpath}")

# ── Main Menu Handler ─────────────────────────────────────────────────────────
def handle_main_menu_choice(choice: str) -> bool:
    wizard = AttackWizard()

    if choice == "1":
        return _handle_social_engineering(wizard)
    elif choice == "2":
        return _handle_fasttrack(wizard)
    elif choice == "3":
        builder = AutomateScriptBuilder()
        builder.add("3")
        confirm_and_execute(builder, "Third Party Modules", {})
        _safe_input("\n[dim]Press Enter to continue...[/]")
        return True
    elif choice == "4":
        builder = AutomateScriptBuilder()
        builder.add("4")
        confirm_and_execute(builder, "Update SET", {})
        _safe_input("\n[dim]Press Enter to continue...[/]")
        return True
    elif choice == "5":
        builder = AutomateScriptBuilder()
        builder.add("5")
        confirm_and_execute(builder, "Update SET Configuration", {})
        _safe_input("\n[dim]Press Enter to continue...[/]")
        return True
    elif choice == "6":
        _show_help()
        return True
    elif choice == "7":
        _handle_presets(wizard)
        return True
    elif choice == "8":
        _handle_plugins()
        return True
    elif choice == "9":
        AttackHistory.view()
        _safe_input("\n[dim]Press Enter to continue...[/]")
        return True
    elif choice == "99":
        return False

    return True

def _handle_social_engineering(wizard: "AttackWizard") -> bool:
    while True:
        console.clear()
        show_banner()
        soc_opts = MENU_TREE["social_engineering"]
        has_msf = DependencyChecker.check_metasploit()
        soc_menu: dict[str, str] = {}
        for k, v in soc_opts.items():
            label = v["label"]
            if v.get("requires_msf", False) and not has_msf:
                label = f"[dim]{label}  [requires Metasploit][/]"
            soc_menu[k] = label
        soc_menu["99"] = "Return to Main Menu"
        sub = prompt_choice("Social-Engineering Attacks", soc_menu)
        if sub == "99":
            break
        sub_label = soc_opts[sub]["label"]
        params: Optional[dict] = None
        needs_msf = soc_opts[sub].get("requires_msf", False)
        if needs_msf and not DependencyChecker.check_metasploit():
            show_error("Metasploit Required",
                       "This attack requires Metasploit (msfconsole) which was not found.\n"
                       "Install with: curl https://raw.githubusercontent.com/rapid7/"
                       "metasploit-omnibus/master/config/templates/"
                       "metasploit-framework-wrappers/msfupdate.erb | bash")
            _safe_input("\n[yellow]Press Enter to return to menu[/]")
            continue

        if sub == "1":
            params = wizard.run_spearphish()
        elif sub == "2":
            params = wizard.run_website_attack()
        elif sub == "3":
            params = wizard.run_infectious_media()
        elif sub == "4":
            params = wizard.run_payload_listener()
        elif sub == "5":
            params = wizard.run_mass_mailer()
        elif sub == "6":
            params = wizard.run_teensy()
        elif sub == "7":
            params = wizard.run_wireless()
        elif sub == "8":
            params = wizard.run_qrcode()
        elif sub == "9":
            params = wizard.run_powershell()
        elif sub == "10":
            builder = AutomateScriptBuilder()
            builder.build_social_engineering("10", "1", {})
            confirm_and_execute(builder, "Third Party Modules", {})
            _safe_input("\n[dim]Press Enter to continue...[/]")
            continue

        if params:
            builder = AutomateScriptBuilder()
            builder.build_social_engineering(sub, params.get("attack_type", params.get("attack_method", params.get("media_type", "1"))), params)
            confirm_and_execute(builder, sub_label, params)

        _safe_input("\n[dim]Press Enter to continue...[/]")
    return True

def _handle_fasttrack(wizard: "AttackWizard") -> bool:
    while True:
        console.clear()
        show_banner()
        ft_opts = MENU_TREE["fasttrack"]
        ft_menu: dict[str, str] = {}
        for k, v in ft_opts.items():
            ft_menu[k] = v["label"] if isinstance(v, dict) else str(v)
        ft_menu["99"] = "Return to Main Menu"
        sub = prompt_choice("Fast-Track Penetration Testing", ft_menu)
        if sub == "99":
            break
        label = ft_opts[sub]["label"] if isinstance(ft_opts[sub], dict) else str(ft_opts[sub])
        params: Optional[dict] = None

        if sub == "1":
            params = wizard.run_mssql()
        elif sub == "2":
            params = wizard.run_exploits()
        elif sub == "3":
            params = wizard.run_fasttrack_sccm()
        elif sub == "4":
            params = wizard.run_fasttrack_drac()
        elif sub == "5":
            params = wizard.run_fasttrack_ridenum()
        elif sub == "6":
            params = wizard.run_fasttrack_psexec()

        if params:
            builder = AutomateScriptBuilder()
            builder.build_fasttrack(sub, params.get("mssql_mode", params.get("exploit_type", "1")), params)
            confirm_and_execute(builder, label, params)

        _safe_input("\n[dim]Press Enter to continue...[/]")
    return True

def _handle_presets(wizard: "AttackWizard") -> None:
    console.clear()
    show_banner()
    action = prompt_numbered_list("Attack Presets", ["Load a preset", "Save current params", "Delete a preset"])
    if action == "1":
        result = AttackPreset.load()
        if result:
            attack_type, params = result
            show_info(f"Loaded preset for {attack_type}")
    elif action == "2":
        name = prompt_text("Preset name")
        if name:
            AttackPreset.save(name, "custom", {"note": "Custom saved preset"})
    elif action == "3":
        presets = AttackPreset.list_presets()
        if presets:
            opts = {str(i+1): p.stem for i, p in enumerate(presets)}
            choice = prompt_choice("Delete Preset", opts)
            if choice in opts:
                presets[int(choice)-1].unlink()
                show_success("Deleted", f"Preset {choice} deleted")
    _safe_input("\n[dim]Press Enter to continue...[/]")

def _handle_plugins() -> None:
    console.clear()
    show_banner()
    plugins = Plugin.discover()
    if not plugins:
        show_info("No plugins installed.")
        show_info(f"Drop .json plugin files in: {PLUGINS_DIR}")
        _safe_input("\n[dim]Press Enter to continue...[/]")
        return
    opts = {str(i+1): name for i, name in enumerate(plugins)}
    opts["99"] = "Back"
    choice = prompt_choice("Plugins", opts)
    if choice and choice != "99":
        name = opts[choice]
        Plugin.run(plugins[name])
    _safe_input("\n[dim]Press Enter to continue...[/]")

def _show_help() -> None:
    console.clear()
    show_banner()
    about_text = (
        f"[bold cyan]PocketSET v{VERSION}[/]\n\n"
        "[white]Interactive TUI wrapper for the Social-Engineer Toolkit[/]\n\n"
        f"[bold]Platform:[/] {Platform.name()}\n"
        "[bold]Original SET Author:[/] David Kennedy (ReL1K)\n"
        "[bold]SET Repository:[/] https://github.com/trustedsec/social-engineer-toolkit\n"
        "[bold]PocketSET:[/] https://github.com/highoncomputers/PocketSET\n\n"
        "[bold]Menu Guide:[/]\n"
        "  [cyan]1-5[/] Direct SET attack options\n"
        "  [cyan]6[/]   Help & About (this screen)\n"
        "  [cyan]7[/]   Attack Presets (save/load)\n"
        "  [cyan]8[/]   Plugins (extend with custom scripts)\n"
        "  [cyan]9[/]   Attack History (view past runs)\n"
        "  [cyan]99[/]  Exit\n\n"
        "[dim]PocketSET provides a beginner-friendly interface for SET,\n"
        "handling all menu navigation and parameter collection\n"
        "automatically. No terminal knowledge required.[/]"
    )
    console.print(Panel(about_text, title="[bold]Help & About[/]", border_style="cyan"))
    _safe_input("\n[dim]Press Enter to continue[/]")

# ── AttackWizard (parameter collection) ───────────────────────────────────────
class AttackWizard:
    def __init__(self) -> None:
        self.params: dict[str, Any] = {}

    def run_spearphish(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]Spear-Phishing Attack Vectors[/]\n\nCraft email messages with malicious payloads", border_style="cyan"))
        show_rule()
        attack_type = prompt_numbered_list(
            "Select attack type",
            ["Perform a Mass Email Attack", "Create a FileFormat Payload", "Create a Social-Engineering Template"]
        )
        self.params["attack_type"] = attack_type
        if attack_type in ("1", "2"):
            self.params["lhost"] = prompt_text(
                "LHOST (IP for reverse connection)",
                default=InputHistory.get("lhost")[0] if InputHistory.get("lhost") else "",
                validate=lambda v: Validator.validate("ip", v, {"custom": "validate_ip", "required": True}),
                error_msg="Invalid IP",
                history=InputHistory.get("lhost"))
            self.params["lport"] = prompt_text(
                "LPORT (Port for reverse connection)", default="443",
                validate=lambda v: Validator.validate("port", v, {"custom": "validate_port", "required": True}),
                error_msg="Invalid port",
                history=InputHistory.get("lport"))
        if attack_type == "1":
            self._collect_email_params()
        if attack_type in ("1", "2"):
            console.print("\n[bold cyan]Select FileFormat Exploit:[/]")
            show_rule()
            ff_opts = SCHEMA["payloads"]["fileformat_exploits"]
            ff_choice = prompt_choice("FileFormat Exploits", ff_opts)
            self.params["fileformat"] = ff_choice
        return self.params or None

    def _collect_email_params(self) -> None:
        self.params["smtp_server"] = prompt_text("SMTP Server (e.g. smtp.gmail.com:587)",
                                                  history=InputHistory.get("smtp_server"))
        self.params["from_email"] = prompt_text("From email", validate=validate_email,
                                                 history=InputHistory.get("from_email"))
        self.params["to_emails"] = prompt_text("Target emails (comma separated)",
                                                history=InputHistory.get("to_emails"))
        self.params["subject"] = prompt_text("Email subject",
                                              history=InputHistory.get("subject"))
        self.params["body"] = prompt_text("Email body",
                                           history=InputHistory.get("body"))
        use_file = prompt_confirm("Use email list file?", False)
        if use_file:
            self.params["email_list_file"] = prompt_text("Path to email list file",
                                                          validate=validate_file_read,
                                                          history=InputHistory.get("email_list_file"))
            InputHistory.push("email_list_file", self.params["email_list_file"])

    def run_website_attack(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]Website Attack Vectors[/]\n\nLaunch web-based attacks using cloned websites", border_style="cyan"))
        show_rule()
        methods = SCHEMA["menu_tree"]["website_attack"]["attack_methods"]
        self.params["attack_method"] = prompt_choice("Select Attack Method", methods)
        sources = SCHEMA["menu_tree"]["website_attack"]["web_sources"]
        self.params["web_source"] = prompt_choice("Select Web Source", sources)
        if self.params["web_source"] == "2":
            self.params["url"] = prompt_text("URL to clone", validate=lambda v: Validator.validate("url", v, {"custom": "validate_url", "required": True}),
                                              history=InputHistory.get("url"))
            InputHistory.push("url", self.params["url"])
        elif self.params["web_source"] == "3":
            self.params["import_path"] = prompt_text("Path to website folder (must have index.html)", validate=validate_file_read,
                                                      history=InputHistory.get("import_path"))
            InputHistory.push("import_path", self.params["import_path"])
        self.params["lhost"] = prompt_text("LHOST (IP address)", default=InputHistory.get("lhost")[0] if InputHistory.get("lhost") else "",
                                            validate=lambda v: Validator.validate("ip", v, {"custom": "validate_ip", "required": True}),
                                            error_msg="Invalid IP", history=InputHistory.get("lhost"))
        self.params["lport"] = prompt_text("LPORT (Port)", default="80",
                                            validate=lambda v: Validator.validate("port", v, {"custom": "validate_port", "required": True}),
                                            error_msg="Invalid port", history=InputHistory.get("lport"))
        self.params["ssl"] = "YES" if prompt_confirm("Enable SSL?", False) else "NO"
        self.params["nat"] = "YES" if prompt_confirm("Using NAT/Port Forwarding?", False) else "NO"
        if self.params["nat"] == "YES":
            self.params["external_ip"] = prompt_text("External IP address",
                                                      validate=lambda v: Validator.validate("ip", v, {"custom": "validate_ip", "required": True}),
                                                      history=InputHistory.get("external_ip"))
        return self.params or None

    def run_infectious_media(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]Infectious Media Generator[/]\n\nCreate USB/CD autorun with malicious payloads", border_style="cyan"))
        show_rule()
        media_type = prompt_numbered_list("Select media type", ["File-Format Exploits", "Standard Metasploit Executable"])
        self.params["media_type"] = media_type
        self.params["lhost"] = prompt_text("LHOST (IP for reverse connection)", default=InputHistory.get("lhost")[0] if InputHistory.get("lhost") else "",
                                            validate=lambda v: Validator.validate("ip", v, {"custom": "validate_ip", "required": True}),
                                            error_msg="Invalid IP", history=InputHistory.get("lhost"))
        self.params["lport"] = prompt_text("LPORT (Port)", default="443",
                                            validate=lambda v: Validator.validate("port", v, {"custom": "validate_port", "required": True}),
                                            error_msg="Invalid port", history=InputHistory.get("lport"))
        return self.params or None

    def run_payload_listener(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]Create a Payload and Listener[/]\n\nGenerate Metasploit payloads", border_style="cyan"))
        show_rule()
        payloads = SCHEMA["payloads"]["payload_menu_1"]
        self.params["payload_type"] = prompt_choice("Select Payload Type", payloads)
        msf_payloads = SCHEMA["payloads"]["payload_menu_2"]
        self.params["meterpreter_payload"] = prompt_choice("Select Meterpreter Payload", msf_payloads)
        self.params["lhost"] = prompt_text("LHOST (IP)", default=InputHistory.get("lhost")[0] if InputHistory.get("lhost") else "",
                                            validate=lambda v: Validator.validate("ip", v, {"custom": "validate_ip", "required": True}),
                                            error_msg="Invalid IP", history=InputHistory.get("lhost"))
        self.params["lport"] = prompt_text("LPORT (Port)", default="443",
                                            validate=lambda v: Validator.validate("port", v, {"custom": "validate_port", "required": True}),
                                            error_msg="Invalid port", history=InputHistory.get("lport"))
        encoders = SCHEMA["payloads"]["encoders"]
        self.params["encoding"] = prompt_choice("Select Encoding", encoders)
        return self.params or None

    def run_mass_mailer(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]Mass Mailer Attack[/]\n\nSend bulk emails via SMTP", border_style="cyan"))
        show_rule()
        self.params["smtp_server"] = prompt_text("SMTP Server (e.g. smtp.gmail.com:587)",
                                                  history=InputHistory.get("smtp_server"))
        InputHistory.push("smtp_server", self.params["smtp_server"])
        self.params["from_email"] = prompt_text("From email", validate=validate_email,
                                                 history=InputHistory.get("from_email"))
        InputHistory.push("from_email", self.params["from_email"])
        self.params["to_emails"] = prompt_text("Target emails (comma separated)",
                                                history=InputHistory.get("to_emails"))
        InputHistory.push("to_emails", self.params["to_emails"])
        self.params["subject"] = prompt_text("Email subject",
                                              history=InputHistory.get("subject"))
        InputHistory.push("subject", self.params["subject"])
        self.params["body"] = prompt_text("Email body",
                                           history=InputHistory.get("body"))
        InputHistory.push("body", self.params["body"])
        use_file = prompt_confirm("Use email list file?", False)
        if use_file:
            self.params["email_list_file"] = prompt_text("Path to email list file",
                                                          validate=validate_file_read,
                                                          history=InputHistory.get("email_list_file"))
            InputHistory.push("email_list_file", self.params["email_list_file"])
        return self.params or None

    def run_teensy(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]Arduino-Based Attack Vector[/]\n\nProgram Teensy USB devices for HID attacks", border_style="cyan"))
        show_rule()
        teensy_opts = SCHEMA["menu_tree"]["teensy"]
        self.params["teensy_type"] = prompt_choice("Select Teensy Attack", teensy_opts)
        tt = int(self.params["teensy_type"])
        if tt in (1, 2, 3, 4, 5, 6, 12, 14):
            self.params["lhost"] = prompt_text("LHOST (IP)", default=InputHistory.get("lhost")[0] if InputHistory.get("lhost") else "",
                                                validate=lambda v: Validator.validate("ip", v, {"custom": "validate_ip", "required": True}),
                                                error_msg="Invalid IP", history=InputHistory.get("lhost"))
            self.params["lport"] = prompt_text("LPORT (Port)", default="443",
                                                validate=lambda v: Validator.validate("port", v, {"custom": "validate_port", "required": True}),
                                                error_msg="Invalid port", history=InputHistory.get("lport"))
        return self.params or None

    def run_wireless(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        if Platform.is_termux():
            show_warning("Not Available", "Wireless AP attacks are not supported in Termux (no monitor mode).")
            _safe_input("\n[dim]Press Enter to continue[/]")
            return None
        console.print(Panel("[bold]Wireless Access Point Attack Vector[/]\n\nCreate a rogue access point with DNS spoofing", border_style="cyan"))
        show_rule()
        action = prompt_numbered_list("Select action", ["Start Access Point", "Stop Access Point"])
        self.params["wireless_action"] = action
        if action == "1":
            self.params["ssid"] = prompt_text("Access Point SSID", default="Free WiFi")
            self.params["channel"] = prompt_text("WiFi Channel", default="6")
            self.params["interface"] = prompt_text("Wireless interface", default="wlan0")
            dhcp_opts = {"1": "10.0.0.100-254", "2": "192.168.10.100-254"}
            self.params["dhcp_range"] = prompt_choice("DHCP Range", dhcp_opts)
        return self.params or None

    def run_qrcode(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]QRCode Generator[/]\n\nGenerate QR codes with malicious URLs", border_style="cyan"))
        show_rule()
        self.params["qr_url"] = prompt_text("URL for QR Code",
                                             validate=lambda v: Validator.validate("url", v, {"custom": "validate_url", "required": True}),
                                             history=InputHistory.get("qr_url"))
        InputHistory.push("qr_url", self.params["qr_url"])
        return self.params or None

    def run_powershell(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]PowerShell Attack Vectors[/]\n\nCreate PowerShell-based attacks", border_style="cyan"))
        show_rule()
        ps_opts = SCHEMA["menu_tree"]["powershell"]
        self.params["ps_type"] = prompt_choice("Select PowerShell Attack", ps_opts)
        pt = int(self.params["ps_type"])
        if pt in (1, 2, 3):
            self.params["lhost"] = prompt_text("LHOST (IP)", default=InputHistory.get("lhost")[0] if InputHistory.get("lhost") else "",
                                                validate=lambda v: Validator.validate("ip", v, {"custom": "validate_ip", "required": True}),
                                                error_msg="Invalid IP", history=InputHistory.get("lhost"))
            self.params["lport"] = prompt_text("LPORT (Port)", default="443",
                                                validate=lambda v: Validator.validate("port", v, {"custom": "validate_port", "required": True}),
                                                error_msg="Invalid port", history=InputHistory.get("lport"))
        return self.params or None

    def run_mssql(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]Microsoft SQL Bruter[/]\n\nBrute force MSSQL servers", border_style="cyan"))
        show_rule()
        mode = prompt_numbered_list("Select mode", ["Scan and Attack MSSQL", "Connect directly to MSSQL"])
        self.params["mssql_mode"] = mode
        if mode == "1":
            src = prompt_numbered_list("Target source", ["CIDR/IP address", "File with IP addresses"])
            self.params["scan_source"] = src
            if src == "1":
                self.params["target_cidr"] = prompt_text("CIDR or IP (e.g. 192.168.1.0/24)",
                                                          history=InputHistory.get("target_cidr"))
                InputHistory.push("target_cidr", self.params["target_cidr"])
            else:
                self.params["target_file"] = prompt_text("Path to IP list file", validate=validate_file_read,
                                                          history=InputHistory.get("target_file"))
                InputHistory.push("target_file", self.params["target_file"])
            self.params["wordlist"] = prompt_text("Wordlist path (leave empty for default)", default="",
                                                   history=InputHistory.get("wordlist"))
            if not self.params["wordlist"]:
                self.params["wordlist"] = "default"
            InputHistory.push("wordlist", self.params["wordlist"])
        else:
            self.params["target"] = prompt_text("Target IP/hostname", history=InputHistory.get("target"))
            InputHistory.push("target", self.params["target"])
        self.params["port"] = prompt_text("Port", default="1433", history=InputHistory.get("port"))
        InputHistory.push("port", self.params["port"])
        self.params["username"] = prompt_text("Username", default="sa", history=InputHistory.get("username"))
        InputHistory.push("username", self.params["username"])
        if mode == "2":
            self.params["password"] = prompt_text("Password", password=True)
        return self.params or None

    def run_exploits(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]Custom Exploits[/]\n\nLaunch Python-based exploits", border_style="cyan"))
        show_rule()
        exploit_opts = SCHEMA["menu_tree"]["exploits"]
        self.params["exploit_type"] = prompt_choice("Select Exploit", exploit_opts)
        self.params["target"] = prompt_text("Target IP/hostname", history=InputHistory.get("target"))
        InputHistory.push("target", self.params["target"])
        self.params["port"] = prompt_text("Port", default="445", history=InputHistory.get("port"))
        InputHistory.push("port", self.params["port"])
        return self.params or None

    def run_fasttrack_sccm(self) -> Optional[dict]:
        self.params: dict[str, Any] = {"target": prompt_text("Target SCCM server IP/hostname", history=InputHistory.get("target"))}
        InputHistory.push("target", self.params["target"])
        return self.params or None

    def run_fasttrack_drac(self) -> Optional[dict]:
        self.params: dict[str, Any] = {"target": prompt_text("Target DRAC IP/hostname", history=InputHistory.get("target"))}
        InputHistory.push("target", self.params["target"])
        return self.params or None

    def run_fasttrack_ridenum(self) -> Optional[dict]:
        self.params: dict[str, Any] = {"target": prompt_text("Target IP/hostname", history=InputHistory.get("target"))}
        InputHistory.push("target", self.params["target"])
        return self.params or None

    def run_fasttrack_psexec(self) -> Optional[dict]:
        self.params: dict[str, Any] = {
            "target": prompt_text("Target IP/hostname", history=InputHistory.get("target")),
            "username": prompt_text("Username", history=InputHistory.get("username")),
            "password": prompt_text("Password", password=True)
        }
        InputHistory.push("target", self.params["target"])
        InputHistory.push("username", self.params["username"])
        return self.params or None

# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    _ensure_dirs()
    LOG.info("PocketSET v%s started on %s", VERSION, Platform.detect())

    if not Disclaimer.show():
        sys.exit(1)

    # Auto-update check
    try:
        latest = AutoUpdater.check()
        if latest:
            show_info(f"Update available: v{latest}")
            if prompt_confirm(f"Upgrade PocketSET to v{latest}?"):
                AutoUpdater.update()
    except Exception:
        pass

    setoolkit_path = DependencyChecker.find_setoolkit()
    if not setoolkit_path:
        show_error("SET Not Found",
                   "Social-Engineer Toolkit is not installed.\n\n"
                   "Install with:\n"
                   "  git clone https://github.com/trustedsec/social-engineer-toolkit\n"
                   "  cd social-engineer-toolkit && pip install -e .\n\n"
                   "Then run: pocketset")
        if prompt_confirm("Open the SET GitHub page for install instructions?", False):
            import webbrowser
            webbrowser.open("https://github.com/trustedsec/social-engineer-toolkit")
        sys.exit(1)

    if not DependencyChecker.check_pexpect():
        show_warning("Missing Dependency",
                     "pexpect is not installed. Fallback to subprocess mode.\n"
                     "Install for better experience: pip install pexpect")
        if prompt_confirm("Install pexpect now?", True):
            DependencyChecker.install_pexpect()

    has_msf = DependencyChecker.check_metasploit()
    if not has_msf:
        show_warning("Metasploit Not Found",
                     "Metasploit (msfconsole) is not installed.\n"
                     "MSF-dependent attacks will be disabled.\n"
                     "Install with: apt install metasploit-framework")

    InputHistory.load()
    running = True

    while running:
        console.clear()
        show_banner()
        main_opts = MENU_TREE["main_menu"]
        display_opts: dict[str, str] = {}
        for k, v in main_opts.items():
            display_opts[k] = v["label"] if isinstance(v, dict) else str(v)
        display_opts["7"] = "Attack Presets (save/load)"
        display_opts["8"] = "Plugins"
        display_opts["9"] = "Attack History"
        display_opts["99"] = "Exit PocketSET"

        set_path_short = setoolkit_path if len(setoolkit_path) < 40 else "..." + setoolkit_path[-36:]
        show_info(f"SET: [green]{set_path_short}[/]")
        if has_msf:
            show_info("Metasploit: [green]Available[/]")
        else:
            console.print(Panel("[yellow]\u26a0 Metasploit not found \u2014 attack options 1-4 will be disabled[/]",
                                border_style="yellow", box=box.ROUNDED))
        show_rule()

        choice = prompt_choice("Main Menu", display_opts)

        if choice == "99":
            running = False
            console.print("[yellow]Exiting PocketSET...[/]")
            console.print("[yellow]Hack the Gibson...and remember...hugs are worth more than handshakes.[/]")
        else:
            try:
                running = handle_main_menu_choice(choice)
            except KeyboardInterrupt:
                console.print("\n[yellow]Returning to main menu...[/]")
                continue
            except Exception as e:
                LOG.exception("Unhandled error: %s", e)
                show_error("Unexpected Error",
                           f"An unexpected error occurred:\n{e}\n\n"
                           "Log saved to ~/.pocketset/logs/")
                _safe_input("\n[dim]Press Enter to continue...[/]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye! Hack the Gibson...[/]")
        sys.exit(0)
    except Exception as e:
        _log_error(f"Fatal error: {e}\n{traceback.format_exc()}")
        show_error("Fatal Error", f"{e}\n\nDetails logged to ~/.pocketset/logs/")
        sys.exit(1)
