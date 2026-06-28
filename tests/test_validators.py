"""Tests for PocketSET validators."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from wrapper import (
    validate_ip, validate_port, validate_url, validate_email,
    validate_file_read, validate_cidr, validate_hostname, Validator
)

class TestValidateIP:
    def test_valid_ips(self):
        assert validate_ip("192.168.1.1")
        assert validate_ip("10.0.0.1")
        assert validate_ip("172.16.0.1")
        assert validate_ip("255.255.255.255")
        assert validate_ip("0.0.0.0")

    def test_invalid_ips(self):
        assert not validate_ip("")
        assert not validate_ip("not.an.ip")
        assert not validate_ip("256.1.2.3")
        assert not validate_ip("1.2.3")
        assert not validate_ip("1.2.3.4.5")
        assert not validate_ip("1.2.3.-1")

class TestValidatePort:
    def test_valid_ports(self):
        assert validate_port("80")
        assert validate_port("443")
        assert validate_port("1")
        assert validate_port("65535")
        assert validate_port("8080")

    def test_invalid_ports(self):
        assert not validate_port("")
        assert not validate_port("0")
        assert not validate_port("65536")
        assert not validate_port("-1")
        assert not validate_port("not_a_port")

class TestValidateURL:
    def test_valid_urls(self):
        assert validate_url("http://example.com")
        assert validate_url("https://example.com")
        assert validate_url("http://192.168.1.1")
        assert validate_url("https://example.com/path?query=1")

    def test_invalid_urls(self):
        assert not validate_url("")
        assert not validate_url("not_a_url")
        assert not validate_url("ftp://example.com")
        assert not validate_url("http://")

class TestValidateEmail:
    def test_valid_emails(self):
        ok, msg = validate_email("user@example.com")
        assert ok
        ok, msg = validate_email("test@test.co.uk")
        assert ok

    def test_invalid_emails(self):
        ok, msg = validate_email("")
        assert not ok
        ok, msg = validate_email("not_an_email")
        assert not ok
        ok, msg = validate_email("@example.com")
        assert not ok

class TestValidateCIDR:
    def test_valid_cidrs(self):
        assert validate_cidr("192.168.1.0/24")
        assert validate_cidr("10.0.0.0/8")
        assert validate_cidr("172.16.0.0/16")
        assert validate_cidr("0.0.0.0/0")
        assert validate_cidr("255.255.255.255/32")

    def test_invalid_cidrs(self):
        assert not validate_cidr("")
        assert not validate_cidr("192.168.1.0")
        assert not validate_cidr("192.168.1.0/33")
        assert not validate_cidr("256.0.0.0/24")

class TestValidateHostname:
    def test_valid_hostnames(self):
        assert validate_hostname("example.com")
        assert validate_hostname("localhost")
        assert validate_hostname("my-server.local")
        assert validate_hostname("a.co")

    def test_invalid_hostnames(self):
        assert not validate_hostname("")
        assert not validate_hostname("-bad.com")
        assert not validate_hostname("bad-.com")

class TestValidator:
    def test_required_field_empty(self):
        ok, msg = Validator.validate("string", "", {"required": True})
        assert not ok
        assert "required" in msg.lower()

    def test_optional_field_empty(self):
        ok, msg = Validator.validate("string", "", {"required": False})
        assert ok

    def test_validate_ip_custom(self):
        ok, msg = Validator.validate("ip", "192.168.1.1", {"custom": "validate_ip", "required": True})
        assert ok
        ok, msg = Validator.validate("ip", "bad", {"custom": "validate_ip", "required": True})
        assert not ok

    def test_validate_port_custom(self):
        ok, msg = Validator.validate("port", "443", {"custom": "validate_port", "required": True})
        assert ok
        ok, msg = Validator.validate("port", "99999", {"custom": "validate_port", "required": True})
        assert not ok

    def test_min_length(self):
        ok, msg = Validator.validate("string", "ab", {"min_length": 3})
        assert not ok
        ok, msg = Validator.validate("string", "abc", {"min_length": 3})
        assert ok

    def test_max_length(self):
        ok, msg = Validator.validate("string", "toolong", {"max_length": 3})
        assert not ok
