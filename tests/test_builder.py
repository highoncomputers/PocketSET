"""Tests for AutomateScriptBuilder."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from wrapper import AutomateScriptBuilder

class TestAutomateScriptBuilder:
    def test_empty_builder(self):
        b = AutomateScriptBuilder()
        assert b.get_preview() == ""

    def test_add_single_line(self):
        b = AutomateScriptBuilder()
        b.add("1")
        assert b.get_preview() == "1"

    def test_add_blank(self):
        b = AutomateScriptBuilder()
        b.add("1")
        b.add_blank()
        b.add("2")
        assert b.get_preview() == "1\n\n2"

    def test_add_many(self):
        b = AutomateScriptBuilder()
        b.add_many("1", "2", "3")
        assert b.get_preview() == "1\n2\n3"

    def test_social_engineering_mass_mailer(self):
        b = AutomateScriptBuilder()
        params = {
            "attack_type": "1",
            "smtp_server": "smtp.gmail.com:587",
            "from_email": "test@example.com",
            "to_emails": "target@example.com",
            "subject": "Test",
            "body": "Hello",
        }
        b.build_social_engineering("5", "1", params)
        script = b.get_preview()
        assert script.startswith("1\n5\n1")
        assert "smtp.gmail.com:587" in script
        assert "test@example.com" in script

    def test_social_engineering_website_clone(self):
        b = AutomateScriptBuilder()
        params = {
            "attack_method": "3",
            "web_source": "2",
            "url": "http://example.com",
            "lhost": "192.168.1.100",
            "lport": "80",
        }
        b.build_social_engineering("2", "3", params)
        script = b.get_preview()
        assert script.startswith("1\n2\n3")
        assert "http://example.com" in script
        assert "192.168.1.100" in script

    def test_social_engineering_powershell(self):
        b = AutomateScriptBuilder()
        params = {"ps_type": "1", "lhost": "10.0.0.1", "lport": "443"}
        b.build_social_engineering("9", "1", params)
        script = b.get_preview()
        assert script.startswith("1\n9\n1")
        assert "10.0.0.1" in script
        assert "443" in script

    def test_social_engineering_teensy(self):
        b = AutomateScriptBuilder()
        params = {"teensy_type": "1", "lhost": "10.0.0.1", "lport": "4444"}
        b.build_social_engineering("6", "1", params)
        script = b.get_preview()
        assert script.startswith("1\n6\n1")
        assert "10.0.0.1" in script
        assert "4444" in script

    def test_social_engineering_wireless(self):
        b = AutomateScriptBuilder()
        params = {"wireless_action": "1", "ssid": "TestNet", "channel": "6", "interface": "wlan0"}
        b.build_social_engineering("7", "1", params)
        script = b.get_preview()
        assert "TestNet" in script
        assert "wlan0" in script

    def test_fasttrack_mssql_scan(self):
        b = AutomateScriptBuilder()
        params = {"mssql_mode": "1", "scan_source": "1", "target_cidr": "10.0.0.0/8", "port": "1433", "wordlist": "default", "username": "sa"}
        b.build_fasttrack("1", "1", params)
        script = b.get_preview()
        assert script.startswith("2\n1\n1")
        assert "10.0.0.0/8" in script

    def test_fasttrack_direct_mssql(self):
        b = AutomateScriptBuilder()
        params = {"mssql_mode": "2", "target": "10.0.0.5", "port": "1433", "username": "sa", "password": "Pass123"}
        b.build_fasttrack("1", "2", params)
        script = b.get_preview()
        assert "10.0.0.5" in script
        assert "Pass123" in script

    def test_fasttrack_exploits(self):
        b = AutomateScriptBuilder()
        params = {"exploit_type": "1", "target": "10.0.0.5", "port": "445"}
        b.build_fasttrack("2", "1", params)
        script = b.get_preview()
        assert script.startswith("2\n2\n1")
        assert "10.0.0.5" in script

    def test_write_creates_file(self):
        b = AutomateScriptBuilder()
        b.add("99")
        path = b.write()
        assert path.exists()
        assert path.read_text() == "99\n"
        path.unlink()
