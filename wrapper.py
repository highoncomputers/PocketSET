#!/usr/bin/env python3
"""PocketSET v1.0 — Interactive TUI wrapper for the Social-Engineer Toolkit"""
import os, sys, re, json, shutil, signal, textwrap, time, subprocess, socket
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.layout import Layout
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.text import Text
    from rich.columns import Columns
    from rich import box
    from rich.prompt import Prompt, IntPrompt, Confirm as RichConfirm
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.syntax import Syntax
    from rich.rule import Rule
    from rich.align import Align
except ImportError as e:
    print(f"Error: rich is required. Install: pip install rich\n{e}")
    sys.exit(1)

try:
    BASE_DIR = Path(__file__).resolve().parent
except NameError:
    BASE_DIR = Path("/opt/PocketSET")
    if not BASE_DIR.exists():
        BASE_DIR = Path.cwd()
SCHEMA_PATH = BASE_DIR / "schema.json"
POCKETSET_DIR = Path.home() / ".pocketset"
LOGS_DIR = POCKETSET_DIR / "logs"
TEMP_DIR = POCKETSET_DIR / "temp"

console = Console()

VERSION = "1.0.0"

with open(str(SCHEMA_PATH)) as f:
    SCHEMA = json.load(f)

MENU_TREE = SCHEMA["menu_tree"]

def _load_validation():
    vpath = BASE_DIR / "validation.json"
    if vpath.exists():
        return json.loads(vpath.read_text())
    return {}

VAL_SCHEMA = _load_validation()

def _log_error(msg: str):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logfile = LOGS_DIR / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logfile.write_text(f"[{datetime.now().isoformat()}] {msg}\n")

def signal_handler(sig, frame):
    console.print("\n[yellow]Shutting down PocketSET...[/]")
    _cleanup_temp()
    console.print("[yellow]Hack the Gibson...and remember...hugs are worth more than handshakes.[/]")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def _cleanup_temp():
    if TEMP_DIR.exists():
        for f in TEMP_DIR.iterdir():
            try: f.unlink()
            except: pass
        try: TEMP_DIR.rmdir()
        except: pass

def _ensure_dirs():
    POCKETSET_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

def validate_ip(ip: str) -> bool:
    m = re.match(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$', ip.strip())
    if not m: return False
    return all(0 <= int(g) <= 255 for g in m.groups())

def validate_port(p: str) -> bool:
    try:
        n = int(p.strip())
        return 1 <= n <= 65535
    except: return False

def validate_url(url: str) -> bool:
    u = url.strip()
    if not u.startswith(('http://', 'https://')):
        return False
    return bool(re.match(r'^https?://[^\s/$.?#].[^\s]*$', u))

def validate_email(e: str) -> bool:
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', e.strip()))

def validate_file_read(p: str) -> bool:
    return Path(p.strip()).expanduser().exists()

def validate_cidr(c: str) -> bool:
    c = c.strip()
    m = re.match(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/(\d{1,2})$', c)
    if not m: return False
    ip_ok = all(0 <= int(g) <= 255 for g in m.group(1).split('.'))
    prefix = int(m.group(2))
    return ip_ok and 0 <= prefix <= 32

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
            if not validate_file_read(v):
                return False, rules.get("error_message", "File not found")
            return True, ""
        if custom == "validate_cidr_or_file":
            if validate_cidr(v) or validate_ip(v) or validate_file_read(v):
                return True, ""
            return False, rules.get("error_message", "Invalid CIDR, IP, or file path")
        if custom == "validate_target":
            if validate_ip(v) or validate_url(f"http://{v}"):
                return True, ""
            return False, rules.get("error_message", "Enter a valid IP or hostname")
        if custom == "validate_emails":
            parts = [e.strip() for e in v.replace('\n', ',').split(',') if e.strip()]
            if not parts:
                return False, "Enter at least one email"
            for e in parts:
                if not validate_email(e):
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
        except: pass
        return True, ""

class Colors:
    HEADER = "bold cyan"
    SUCCESS = "bold green"
    ERROR = "bold red"
    WARNING = "bold yellow"
    INFO = "white"
    LABEL = "bold white"
    MUTED = "dim white"

def show_banner():
    banner = textwrap.dedent(f"""\
    [bold cyan]╔═══════════════════════════════════════════════╗
    ║         PocketSET v{VERSION}                  ║
    ║  Social-Engineer Toolkit — Interactive TUI   ║
    ╚═══════════════════════════════════════════════╝[/]""")
    console.print()
    console.print(Panel(banner, border_style="cyan", box=box.DOUBLE_EDGE))
    console.print()

def show_error(title: str, message: str):
    console.print(Panel(f"[red]{message}[/]", title=f"[bold red]{title}[/]", border_style="red"))

def show_success(title: str, message: str):
    console.print(Panel(f"[green]{message}[/]", title=f"[bold green]{title}[/]", border_style="green"))

def show_warning(title: str, message: str):
    console.print(Panel(f"[yellow]{message}[/]", title=f"[bold yellow]{title}[/]", border_style="yellow"))

def show_info(message: str):
    console.print(f"[dim]\\u2503[/] {message}")

def show_rule():
    console.print(Rule(style="dim"))

def prompt_text(label: str, default: str = "", password: bool = False, validate: Optional[Callable] = None, error_msg: str = "") -> str:
    while True:
        d = f" [{default}]" if default else ""
        if password:
            val = Prompt.ask(f"[bold]{label}[/]{d}", password=True)
        else:
            val = Prompt.ask(f"[bold]{label}[/]{d}")
        if not val and default:
            val = default
        if validate:
            ok, msg = validate(val.strip())
            if not ok:
                show_error("Validation Error", msg or error_msg)
                continue
        return val.strip()

def prompt_confirm(label: str, default: bool = False) -> bool:
    return RichConfirm.ask(f"[bold]{label}[/]", default=default)

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
        choice = Prompt.ask(f"[bold]{prompt_text_str}[/]")
        if choice in options:
            return choice
        show_error("Invalid Choice", f"Enter a valid option: {', '.join(options.keys())}")

def prompt_numbered_list(title: str, items: list, prompt_text_str: str = "Select an option") -> str:
    options = {str(i+1): item for i, item in enumerate(items)}
    return prompt_choice(title, options, prompt_text_str)

class Disclaimer:
    DISCLAIMER_FILE = POCKETSET_DIR / "disclaimer_accepted"

    @classmethod
    def is_accepted(cls) -> bool:
        return cls.DISCLAIMER_FILE.exists()

    @classmethod
    def mark_accepted(cls):
        cls.DISCLAIMER_FILE.parent.mkdir(parents=True, exist_ok=True)
        cls.DISCLAIMER_FILE.write_text(f"accepted on {datetime.now().isoformat()}\n")

    @classmethod
    def show(cls) -> bool:
        if cls.is_accepted():
            return True
        console.clear()
        text = textwrap.dedent("""\
        [bold red]╔══════════════════════════════════════════════════════════════╗
        ║                     LEGAL DISCLAIMER                         ║
        ╚══════════════════════════════════════════════════════════════╝[/]

        [yellow]The Social-Engineer Toolkit (SET) is a penetration testing
        framework for AUTHORIZED security assessments ONLY.[/]

        By using PocketSET you agree that:

        [white]  • You have explicit written permission to test the
            target systems, networks, and/or personnel
        • You will not use SET for any illegal or unauthorized
            purpose
        • You accept full responsibility for any consequences
            arising from your use of this tool
        • You comply with all applicable local, state, federal,
            and international laws[/]

        [bold red]Unauthorized use is a criminal offence.[/]

        [dim]This disclaimer is displayed once per session.
        Acceptance is recorded in ~/.pocketset/disclaimer_accepted[/]
        """)
        console.print(Panel(Markdown(text.replace('[bold red]', '**').replace('[/]', '').replace('[yellow]', '').replace('[white]', '').replace('[/bold red]', '')), border_style="red", title="[bold red]LEGAL DISCLAIMER[/]"))
        console.print()
        val = Prompt.ask("[bold red]Type I AGREE to accept, or anything else to exit[/]")
        if val.strip().upper() == "I AGREE":
            cls.mark_accepted()
            return True
        console.print("[red]Exiting. You must accept the disclaimer to use PocketSET.[/]")
        return False

class DependencyChecker:
    @staticmethod
    def find_setoolkit() -> str:
        candidates = [
            "setoolkit",
            "seautomate",
            "./setoolkit",
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
        r = subprocess.run(["which", "msfconsole"], capture_output=True, text=True)
        return r.returncode == 0

    @staticmethod
    def check_pexpect() -> bool:
        try:
            import pexpect
            return True
        except ImportError:
            return False

    @staticmethod
    def install_pexpect() -> bool:
        show_info("Installing pexpect...")
        r = subprocess.run([sys.executable, "-m", "pip", "install", "pexpect", "-q"],
                          capture_output=True, text=True)
        if r.returncode == 0:
            show_success("Success", "pexpect installed")
            return True
        show_error("Install Failed", f"Could not install pexpect:\n{r.stderr}")
        return False

class AutomateScriptBuilder:
    def __init__(self):
        self.lines = []
        self.script_path = TEMP_DIR / f"automate_{int(time.time())}.txt"

    def add(self, line: str):
        if line == "":
            self.lines.append("")
        else:
            self.lines.append(line)

    def add_many(self, *lines: str):
        for l in lines:
            self.add(l)

    def add_blank(self):
        self.lines.append("")

    def write(self) -> Path:
        text = "\n".join(self.lines)
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
            lh = params.get("lhost", "")
            self.add(lh)
        elif main_choice == "3":
            media_type = params.get("media_type", "1")
            self.add(media_type)
            if media_type == "1":
                self.add(params.get("lhost", ""))
        elif main_choice == "4":
            pt = params.get("payload_type", "1")
            self.add(pt)
            mp = params.get("meterpreter_payload", "2")
            self.add(mp)
            self.add(params.get("lhost", ""))
            self.add(params.get("lport", "443"))
            enc = params.get("encoding", "4")
            self.add(enc)
        elif main_choice == "5":
            self.add("1")
            self.add(params.get("smtp_server", ""))
            self.add(params.get("from_email", ""))
            self.add(params.get("to_emails", ""))
            self.add(params.get("subject", ""))
            self.add(params.get("body", ""))
        elif main_choice == "6":
            self.add(sub_choice)
        elif main_choice == "7":
            action = params.get("wireless_action", "1")
            self.add(action)
        elif main_choice == "8":
            self.add(params.get("qr_url", ""))
        elif main_choice == "1":
            spear_type = params.get("attack_type", "1")
            self.add(spear_type)

    def build_fasttrack(self, main_choice: str, sub_choice: str, params: dict) -> None:
        self.add("2")
        self.add(main_choice)
        if main_choice == "1":
            self.add(sub_choice)
            if sub_choice == "1":
                cidr_source = params.get("scan_source", "1")
                self.add(cidr_source)
                if cidr_source == "1":
                    self.add(params.get("target_cidr", ""))
                else:
                    self.add(params.get("target_file", ""))
                self.add(params.get("port", "1433"))
                wl = params.get("wordlist", "default")
                self.add(wl)
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

class SETExecutor:
    def __init__(self, script_path: Path, timeout: int = 600):
        self.script_path = script_path
        self.timeout = timeout
        self.output_lines = []
        self.setoolkit_cmd = DependencyChecker.find_setoolkit() or "setoolkit"

    def _run_pexpect(self):
        import pexpect
        import pexpect.exceptions as pexcp
        output = []
        setoolkit_cmd = self.setoolkit_cmd
        if "/" not in setoolkit_cmd and not setoolkit_cmd.startswith("./"):
            r = subprocess.run(["which", setoolkit_cmd], capture_output=True, text=True)
            if r.returncode == 0:
                setoolkit_cmd = r.stdout.strip()
        child = pexpect.spawn(
            setoolkit_cmd,
            timeout=self.timeout,
            encoding="utf-8",
            codec_errors="replace",
            env={**os.environ, "TERM": "xterm-256color", "POCKETSET": "1"}
        )
        # Wait for menu to load (proot may be slow - longer timeout)
        try:
            child.expect(r"99\) Exit the Social-Engineer Toolkit", timeout=120)
        except pexcp.TIMEOUT:
            output.append("[!] Initial menu load timed out (proot/termux may be slow)")
            child.close()
            return "\n".join(output)
        except pexcp.EOF:
            output.append("[!] SET exited before menu loaded")
            child.close()
            return "\n".join(output)
        output.append(child.before or "")
        # Send automate lines
        script_text = self.script_path.read_text()
        for line in script_text.split("\n"):
            if not line.strip():
                child.sendline("")
            else:
                child.sendline(line.strip())
            import time as _time
            _time.sleep(0.5)
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
        except: pass
        child.close()
        return "\n".join(output)

    def _run_subprocess(self):
        script_text = self.script_path.read_text()
        setoolkit_cmd = self.setoolkit_cmd
        proc = subprocess.Popen(
            setoolkit_cmd if "/" in setoolkit_cmd else [setoolkit_cmd],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={**os.environ, "TERM": "xterm-256color", "POCKETSET": "1"}
        )
        stdout_lines = []
        def reader():
            for line in proc.stdout:
                stdout_lines.append(line)
                self.output_lines.append(line)
        import threading
        t = threading.Thread(target=reader, daemon=True)
        t.start()
        try:
            proc.stdin.write(script_text + "\n")
            proc.stdin.flush()
            proc.stdin.close()
        except: pass
        try:
            proc.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            return "".join(stdout_lines) + "\n[red]Command timed out[/]"
        t.join(timeout=5)
        return "".join(stdout_lines)

    def execute(self):
        import importlib
        pexpect_avail = importlib.util.find_spec("pexpect") is not None
        try:
            if pexpect_avail:
                return self._run_pexpect()
            else:
                return self._run_subprocess()
        except FileNotFoundError:
            return "ERROR: setoolkit not found. Install SET first."
        except Exception as e:
            _log_error(f"Execution error: {e}")
            return f"ERROR: {e}"

class AttackWizard:
    def __init__(self):
        self.params = {}

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
            self.params["lhost"] = prompt_text("LHOST (IP for reverse connection)", validate=lambda v: Validator.validate("ip", v, {"custom": "validate_ip", "required": True}), error_msg="Invalid IP")
            self.params["lport"] = prompt_text("LPORT (Port for reverse connection)", default="443", validate=lambda v: Validator.validate("port", v, {"custom": "validate_port", "required": True}), error_msg="Invalid port")
        if attack_type == "1":
            self._collect_email_params()
        if attack_type == "1" or attack_type == "2":
            console.print("\n[bold cyan]Select FileFormat Exploit:[/]")
            show_rule()
            ff_opts = SCHEMA["payloads"]["fileformat_exploits"]
            ff_choice = prompt_choice("FileFormat Exploits", ff_opts)
            self.params["fileformat"] = ff_choice
        return self.params

    def _collect_email_params(self):
        self.params["smtp_server"] = prompt_text("SMTP Server (e.g. smtp.gmail.com:587)")
        self.params["from_email"] = prompt_text("From email", validate=validate_email)
        self.params["to_emails"] = prompt_text("Target emails (comma separated)")
        self.params["subject"] = prompt_text("Email subject")
        self.params["body"] = prompt_text("Email body")
        use_file = prompt_confirm("Use email list file?", False)
        if use_file:
            self.params["email_list_file"] = prompt_text("Path to email list file", validate=validate_file_read)

    def run_website_attack(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]Website Attack Vectors[/]\n\nLaunch web-based attacks using cloned websites", border_style="cyan"))
        show_rule()
        methods = SCHEMA["menu_tree"]["website_attack"]["attack_methods"]
        attack_method = prompt_choice("Select Attack Method", methods)
        self.params["attack_method"] = attack_method
        sources = SCHEMA["menu_tree"]["website_attack"]["web_sources"]
        web_source = prompt_choice("Select Web Source", sources)
        self.params["web_source"] = web_source
        if web_source == "2":
            self.params["url"] = prompt_text("URL to clone", validate=lambda v: Validator.validate("url", v, {"custom": "validate_url", "required": True}))
        elif web_source == "3":
            self.params["import_path"] = prompt_text("Path to website folder (must have index.html)", validate=validate_file_read)
        self.params["lhost"] = prompt_text("LHOST (IP address)", validate=lambda v: Validator.validate("ip", v, {"custom": "validate_ip", "required": True}))
        self.params["lport"] = prompt_text("LPORT (Port)", default="80", validate=lambda v: Validator.validate("port", v, {"custom": "validate_port", "required": True}))
        self.params["ssl"] = "YES" if prompt_confirm("Enable SSL?", False) else "NO"
        self.params["nat"] = "YES" if prompt_confirm("Using NAT/Port Forwarding?", False) else "NO"
        if self.params["nat"] == "YES":
            self.params["external_ip"] = prompt_text("External IP address", validate=lambda v: Validator.validate("ip", v, {"custom": "validate_ip", "required": True}))
        return self.params

    def run_infectious_media(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]Infectious Media Generator[/]\n\nCreate USB/CD autorun with malicious payloads", border_style="cyan"))
        show_rule()
        media_type = prompt_numbered_list("Select media type", ["File-Format Exploits", "Standard Metasploit Executable"])
        self.params["media_type"] = media_type
        self.params["lhost"] = prompt_text("LHOST (IP for reverse connection)", validate=lambda v: Validator.validate("ip", v, {"custom": "validate_ip", "required": True}))
        self.params["lport"] = prompt_text("LPORT (Port)", default="443", validate=lambda v: Validator.validate("port", v, {"custom": "validate_port", "required": True}))
        return self.params

    def run_payload_listener(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]Create a Payload and Listener[/]\n\nGenerate Metasploit payloads", border_style="cyan"))
        show_rule()
        payloads = SCHEMA["payloads"]["payload_menu_1"]
        self.params["payload_type"] = prompt_choice("Select Payload Type", payloads)
        msf_payloads = SCHEMA["payloads"]["payload_menu_2"]
        self.params["meterpreter_payload"] = prompt_choice("Select Meterpreter Payload", msf_payloads)
        self.params["lhost"] = prompt_text("LHOST (IP)", validate=lambda v: Validator.validate("ip", v, {"custom": "validate_ip", "required": True}))
        self.params["lport"] = prompt_text("LPORT (Port)", default="443", validate=lambda v: Validator.validate("port", v, {"custom": "validate_port", "required": True}))
        encoders = SCHEMA["payloads"]["encoders"]
        self.params["encoding"] = prompt_choice("Select Encoding", encoders)
        return self.params

    def run_mass_mailer(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]Mass Mailer Attack[/]\n\nSend bulk emails via SMTP", border_style="cyan"))
        show_rule()
        self.params["smtp_server"] = prompt_text("SMTP Server (e.g. smtp.gmail.com:587)")
        self.params["from_email"] = prompt_text("From email", validate=validate_email)
        self.params["to_emails"] = prompt_text("Target emails (comma separated)")
        self.params["subject"] = prompt_text("Email subject")
        self.params["body"] = prompt_text("Email body")
        return self.params

    def run_teensy(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]Arduino-Based Attack Vector[/]\n\nProgram Teensy USB devices for HID attacks", border_style="cyan"))
        show_rule()
        teensy_opts = SCHEMA["menu_tree"]["teensy"]
        self.params["teensy_type"] = prompt_choice("Select Teensy Attack", teensy_opts)
        tt = int(self.params["teensy_type"])
        if tt in (1,2,3,4,5,6,12,14):
            self.params["lhost"] = prompt_text("LHOST (IP)", validate=lambda v: Validator.validate("ip", v, {"custom": "validate_ip", "required": True}))
            self.params["lport"] = prompt_text("LPORT (Port)", default="443", validate=lambda v: Validator.validate("port", v, {"custom": "validate_port", "required": True}))
        return self.params

    def run_wireless(self) -> Optional[dict]:
        self.params = {}
        show_banner()
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
        return self.params

    def run_qrcode(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]QRCode Generator[/]\n\nGenerate QR codes with malicious URLs", border_style="cyan"))
        show_rule()
        self.params["qr_url"] = prompt_text("URL for QR Code", validate=lambda v: Validator.validate("url", v, {"custom": "validate_url", "required": True}))
        return self.params

    def run_powershell(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]PowerShell Attack Vectors[/]\n\nCreate PowerShell-based attacks", border_style="cyan"))
        show_rule()
        ps_opts = SCHEMA["menu_tree"]["powershell"]
        self.params["ps_type"] = prompt_choice("Select PowerShell Attack", ps_opts)
        pt = int(self.params["ps_type"])
        if pt in (1,2,3):
            self.params["lhost"] = prompt_text("LHOST (IP)", validate=lambda v: Validator.validate("ip", v, {"custom": "validate_ip", "required": True}))
            self.params["lport"] = prompt_text("LPORT (Port)", default="443", validate=lambda v: Validator.validate("port", v, {"custom": "validate_port", "required": True}))
        return self.params

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
                self.params["target_cidr"] = prompt_text("CIDR or IP (e.g. 192.168.1.0/24)")
            else:
                self.params["target_file"] = prompt_text("Path to IP list file", validate=validate_file_read)
            self.params["wordlist"] = prompt_text("Wordlist path (leave empty for default)", default="")
            if not self.params["wordlist"]:
                self.params["wordlist"] = "default"
        else:
            self.params["target"] = prompt_text("Target IP/hostname")
        self.params["port"] = prompt_text("Port", default="1433")
        self.params["username"] = prompt_text("Username", default="sa")
        if mode == "2":
            self.params["password"] = prompt_text("Password", password=True)
        return self.params

    def run_exploits(self) -> Optional[dict]:
        self.params = {}
        show_banner()
        console.print(Panel("[bold]Custom Exploits[/]\n\nLaunch Python-based exploits", border_style="cyan"))
        show_rule()
        exploit_opts = SCHEMA["menu_tree"]["exploits"]
        self.params["exploit_type"] = prompt_choice("Select Exploit", exploit_opts)
        self.params["target"] = prompt_text("Target IP/hostname")
        self.params["port"] = prompt_text("Port", default="445")
        return self.params

    def run_fasttrack_sccm(self) -> Optional[dict]:
        self.params = {"target": prompt_text("Target SCCM server IP/hostname")}
        return self.params

    def run_fasttrack_drac(self) -> Optional[dict]:
        self.params = {"target": prompt_text("Target DRAC IP/hostname")}
        return self.params

    def run_fasttrack_ridenum(self) -> Optional[dict]:
        self.params = {"target": prompt_text("Target IP/hostname")}
        return self.params

    def run_fasttrack_psexec(self) -> Optional[dict]:
        self.params = {
            "target": prompt_text("Target IP/hostname"),
            "username": prompt_text("Username"),
            "password": prompt_text("Password", password=True)
        }
        return self.params

def build_automate_script(menu_choice: str, sub_choice: str = "", params: dict = None) -> AutomateScriptBuilder:
    builder = AutomateScriptBuilder()
    if params is None:
        params = {}
    if menu_choice == "1":
        builder.build_social_engineering(sub_choice, params.get("attack_type", "1"), params)
    elif menu_choice == "2":
        builder.build_fasttrack(sub_choice, params.get("sub_type", "1"), params)
    elif menu_choice == "3":
        builder.add("3")
    elif menu_choice == "4":
        builder.add("4")
    elif menu_choice == "5":
        builder.add("5")
    elif menu_choice == "6":
        builder.add("6")
    return builder

def confirm_and_execute(builder: AutomateScriptBuilder, attack_name: str) -> None:
    script = builder.get_preview()
    console.clear()
    console.print(Panel(f"[bold]Attack:[/] {attack_name}\n\n[bold]Command sequence that will be sent to setoolkit:[/]\n\n[dim]{script}[/]",
                        title="[yellow]Confirm Attack[/]", border_style="yellow"))
    show_rule()
    show_warning("Warning", "This will execute a real penetration testing attack. Ensure you have authorization.")
    if not prompt_confirm("Proceed with execution?", default=False):
        show_info("Attack cancelled.")
        return
    script_path = builder.write()
    console.clear()
    show_banner()
    show_info(f"Executing: {attack_name}")
    show_info("Starting SET...")
    executor = SETExecutor(script_path)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        transient=False,
    ) as progress:
        task = progress.add_task("[cyan]Running SET attack...", total=None)
        try:
            output = executor.execute()
        except Exception as e:
            output = f"ERROR: {e}"
            _log_error(f"Execution exception: {e}")
        progress.update(task, visible=False)
    show_rule()
    if "ERROR" in output[:20]:
        show_error("Execution Failed", output)
        _log_error(f"SET execution failed:\n{output}")
    else:
        show_success("Execution Complete", "SET has finished processing.")
        console.print(Panel(output[:2000] if len(output) > 2000 else output,
                           title="[bold]Output[/]", border_style="green"))
    show_rule()

def handle_main_menu_choice(choice: str) -> bool:
    wizard = AttackWizard()
    if choice == "1":
        while True:
            console.clear()
            show_banner()
            soc_opts = MENU_TREE["social_engineering"]
            soc_menu = {k: v["label"] for k, v in soc_opts.items()}
            soc_menu["99"] = "Return to Main Menu"
            sub = prompt_choice("Social-Engineering Attacks", soc_menu)
            if sub == "99": break
            sub_label = soc_opts[sub]["label"]
            params = None
            needs_msf = soc_opts[sub].get("requires_msf", False)
            if needs_msf and not DependencyChecker.check_metasploit():
                show_error("Metasploit Required", "This attack requires Metasploit (msfconsole) which was not found.")
                continue
            if sub == "1":
                params = wizard.run_spearphish()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_social_engineering(sub, params.get("attack_type", "1"), params)
                    confirm_and_execute(builder, sub_label)
            elif sub == "2":
                params = wizard.run_website_attack()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_social_engineering(sub, params.get("attack_method", "1"), params)
                    confirm_and_execute(builder, sub_label)
            elif sub == "3":
                params = wizard.run_infectious_media()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_social_engineering(sub, params.get("media_type", "1"), params)
                    confirm_and_execute(builder, sub_label)
            elif sub == "4":
                params = wizard.run_payload_listener()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_social_engineering(sub, "1", params)
                    confirm_and_execute(builder, sub_label)
            elif sub == "5":
                params = wizard.run_mass_mailer()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_social_engineering(sub, "1", params)
                    confirm_and_execute(builder, sub_label)
            elif sub == "6":
                params = wizard.run_teensy()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_social_engineering(sub, params.get("teensy_type", "1"), params)
                    confirm_and_execute(builder, sub_label)
            elif sub == "7":
                params = wizard.run_wireless()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_social_engineering(sub, params.get("wireless_action", "1"), params)
                    confirm_and_execute(builder, sub_label)
            elif sub == "8":
                params = wizard.run_qrcode()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_social_engineering(sub, "1", params)
                    confirm_and_execute(builder, sub_label)
            elif sub == "9":
                params = wizard.run_powershell()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_social_engineering(sub, params.get("ps_type", "1"), params)
                    confirm_and_execute(builder, sub_label)
            elif sub == "10":
                builder = AutomateScriptBuilder()
                builder.build_social_engineering("10", "1", {})
                confirm_and_execute(builder, "Third Party Modules")
            console.print("\n[dim]Press Enter to continue...[/]", end="")
            input()
        return True

    elif choice == "2":
        while True:
            console.clear()
            show_banner()
            ft_opts = MENU_TREE["fasttrack"]
            ft_menu = {k: v["label"] if isinstance(v, dict) else v for k, v in ft_opts.items()}
            ft_menu["99"] = "Return to Main Menu"
            sub = prompt_choice("Fast-Track Penetration Testing", ft_menu)
            if sub == "99": break
            label = ft_opts[sub]["label"] if isinstance(ft_opts[sub], dict) else ft_opts[sub]
            if sub == "1":
                params = wizard.run_mssql()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_fasttrack(sub, params.get("mssql_mode", "1"), params)
                    confirm_and_execute(builder, label)
            elif sub == "2":
                params = wizard.run_exploits()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_fasttrack(sub, params.get("exploit_type", "1"), params)
                    confirm_and_execute(builder, label)
            elif sub == "3":
                params = wizard.run_fasttrack_sccm()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_fasttrack(sub, "1", params)
                    confirm_and_execute(builder, label)
            elif sub == "4":
                params = wizard.run_fasttrack_drac()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_fasttrack(sub, "1", params)
                    confirm_and_execute(builder, label)
            elif sub == "5":
                params = wizard.run_fasttrack_ridenum()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_fasttrack(sub, "1", params)
                    confirm_and_execute(builder, label)
            elif sub == "6":
                params = wizard.run_fasttrack_psexec()
                if params:
                    builder = AutomateScriptBuilder()
                    builder.build_fasttrack(sub, "1", params)
                    confirm_and_execute(builder, label)
            console.print("\n[dim]Press Enter to continue...[/]", end="")
            input()
        return True

    elif choice == "3":
        builder = AutomateScriptBuilder()
        builder.add("3")
        confirm_and_execute(builder, "Third Party Modules")
        console.print("\n[dim]Press Enter to continue...[/]", end="")
        input()
        return True

    elif choice == "4":
        builder = AutomateScriptBuilder()
        builder.add("4")
        confirm_and_execute(builder, "Update SET")
        console.print("\n[dim]Press Enter to continue...[/]", end="")
        input()
        return True

    elif choice == "5":
        builder = AutomateScriptBuilder()
        builder.add("5")
        confirm_and_execute(builder, "Update SET Configuration")
        console.print("\n[dim]Press Enter to continue...[/]", end="")
        input()
        return True

    elif choice == "6":
        console.clear()
        show_banner()
        about_text = textwrap.dedent(f"""\
        [bold cyan]PocketSET v{VERSION}[/]

        [white]Interactive TUI wrapper for the Social-Engineer Toolkit[/]

        [bold]Original SET Author:[/] David Kennedy (ReL1K)
        [bold]SET Repository:[/] https://github.com/trustedsec/social-engineer-toolkit
        [bold]PocketSET:[/] https://github.com/highoncomputers/PocketSET

        [dim]PocketSET provides a beginner-friendly interface for SET,
        handling all menu navigation and parameter collection
        automatically. No terminal knowledge required.[/]
        """)
        console.print(Panel(Markdown(about_text.replace('[bold cyan]', '**').replace('[white]', '').replace('[bold]', '**').replace('[/]', '').replace('[dim]', '*').replace('[/dim]', '*')), title="[bold]Help & About[/]", border_style="cyan"))
        console.print("\n[dim]Press Enter to continue...[/]", end="")
        input()
        return True

    elif choice == "99":
        return False

    return True

def main():
    _ensure_dirs()
    if not Disclaimer.show():
        sys.exit(1)
    setoolkit_path = DependencyChecker.find_setoolkit()
    if not setoolkit_path:
        show_error("SET Not Found", "Social-Engineer Toolkit is not installed.\n\nInstall with:\n  git clone https://github.com/trustedsec/social-engineer-toolkit\n  cd social-engineer-toolkit && pip install -e .\n\nThen run: pocketset")
        if prompt_confirm("Open the SET GitHub page for install instructions?", False):
            import webbrowser
            webbrowser.open("https://github.com/trustedsec/social-engineer-toolkit")
        sys.exit(1)
    if not DependencyChecker.check_pexpect():
        show_warning("Missing Dependency", "pexpect is not installed. Fallback to subprocess mode.\nInstall for better experience: pip install pexpect")
        if prompt_confirm("Install pexpect now?", True):
            DependencyChecker.install_pexpect()
    has_msf = DependencyChecker.check_metasploit()
    if not has_msf:
        show_warning("Metasploit Not Found", "Metasploit (msfconsole) is not installed. MSF-dependent attacks will be disabled.\nInstall with: apt install metasploit-framework")
    running = True
    while running:
        console.clear()
        show_banner()
        main_opts = MENU_TREE["main_menu"]
        display_opts = {k: v["label"] if isinstance(v, dict) else v for k, v in main_opts.items()}
        display_opts["99"] = "Exit PocketSET"
        set_path_short = setoolkit_path if len(setoolkit_path) < 40 else "..." + setoolkit_path[-36:]
        show_info(f"SET: [green]{set_path_short}[/]  |  Metasploit: {'[green]Available[/]' if has_msf else '[yellow]Not Found[/]'}")
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
                _log_error(f"Unhandled error: {e}\n{traceback.format_exc()}")
                show_error("Unexpected Error", f"An unexpected error occurred:\n{e}\n\nLog saved to ~/.pocketset/logs/")
                console.print("\n[dim]Press Enter to continue...[/]", end="")
                input()

if __name__ == "__main__":
    import traceback
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye! Hack the Gibson...[/]")
        sys.exit(0)
    except Exception as e:
        _log_error(f"Fatal error: {e}\n{traceback.format_exc()}")
        show_error("Fatal Error", f"{e}\n\nDetails logged to ~/.pocketset/logs/")
        sys.exit(1)
