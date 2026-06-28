"""Shared fixtures for PocketSET tests."""
import sys, json, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

@pytest.fixture
def mock_schema(tmp_path):
    """Create a minimal schema.json for testing."""
    schema = {
        "menu_tree": {
            "main_menu": {
                "1": {"label": "Social-Engineering Attacks", "submenu": "social_engineering"},
                "2": {"label": "Fast-Track", "submenu": "fasttrack"},
                "3": {"label": "Third Party Modules"},
                "4": {"label": "Update SET"},
                "5": {"label": "Update Configuration"},
                "6": {"label": "Help"}
            },
            "social_engineering": {
                "1": {"label": "Spear-Phishing", "requires_msf": True, "params": ["lhost", "lport"]},
                "5": {"label": "Mass Mailer", "params": ["smtp_server", "from_email"]}
            },
            "fasttrack": {
                "1": {"label": "MSSQL Bruter", "params": ["target", "port"]}
            }
        },
        "payloads": {
            "fileformat_exploits": {"13": "Adobe PDF"},
            "payload_menu_1": {"1": "Meterpreter"},
            "payload_menu_2": {"2": "Reverse TCP"},
            "encoders": {"4": "Backdoor Exec"}
        }
    }
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema))
    return schema_path
