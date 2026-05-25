"""
Systemd Services Plugin

Creates systemd user unit files for Hermes Gateway, OpenClaw Gateway,
and Open Design services. Enables and daemon-reloads.
"""

import os
import subprocess
from typing import Any, Dict


UNIT_DIR = "%h/.config/systemd/user"

UNIT_FILES = {
    "hermes-gateway.service": """[Unit]
Description=Hermes Gateway Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/.hermes/hermes-agent
Environment="PATH=%h/.hermes/hermes-agent/venv/bin:%h/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=%h/.hermes/hermes-agent/venv/bin/python -m hermes_agent server
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
""",
    "openclaw-gateway.service": """[Unit]
Description=OpenClaw Gateway Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/.openclaw/hermes-openclaw
Environment="PATH=%h/.openclaw/hermes-openclaw/venv/bin:%h/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=%h/.openclaw/hermes-openclaw/venv/bin/python -m openclaw
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
""",
    "open-design.service": """[Unit]
Description=Open Design Web UI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/srv/ai-stack/open-design
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/pnpm --dir /srv/ai-stack/open-design run dev
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
""",
}


def _get_unit_dir(context: Dict[str, Any]) -> str:
    user_home = context.get("USER_HOME", os.path.expanduser("~"))
    return os.path.join(user_home, ".config", "systemd", "user")


def hook_check_prerequisites(context: Dict[str, Any]) -> bool:
    unit_dir = _get_unit_dir(context)
    missing = [name for name in UNIT_FILES if not os.path.isfile(os.path.join(unit_dir, name))]
    if not missing:
        print("All systemd unit files already exist.")
    else:
        print(f"Installing systemd units: {', '.join(missing)}")
    return True


def hook_install(context: Dict[str, Any]) -> Dict[str, Any]:
    print("Installing systemd user service unit files...")

    unit_dir = _get_unit_dir(context)
    os.makedirs(unit_dir, exist_ok=True)

    for name, content in UNIT_FILES.items():
        unit_path = os.path.join(unit_dir, name)
        already_existed = os.path.isfile(unit_path)
        if already_existed:
            print(f"Unit file {name} already exists — skipping (idempotent).")
            continue
        with open(unit_path, "w") as f:
            f.write(content)
        print(f"Created unit file: {unit_path}")

    print("Running daemon-reload...")
    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)

    # Enable all services
    for name in UNIT_FILES:
        print(f"Enabling {name}...")
        subprocess.run(["systemctl", "--user", "enable", name], capture_output=True)

    return {
        "installed": True,
        "unit_dir": unit_dir,
        "units": list(UNIT_FILES.keys()),
    }


def hook_verify(context: Dict[str, Any]) -> bool:
    unit_dir = _get_unit_dir(context)
    errors = []
    for name in UNIT_FILES:
        unit_path = os.path.join(unit_dir, name)
        if not os.path.isfile(unit_path):
            errors.append(f"{name} not found at {unit_path}")
            continue
        # Try to parse via systemctl cat
        result = subprocess.run(
            ["systemctl", "--user", "cat", name],
            capture_output=True,
        )
        if result.returncode != 0:
            errors.append(f"{name} failed systemctl cat check")
    if errors:
        raise RuntimeError(f"Systemd service verification failed: {'; '.join(errors)}")
    print("All systemd unit files verified.")
    return True


def hook_cleanup(context: Dict[str, Any]) -> None:
    print("Cleaning up systemd services...")
    for name in UNIT_FILES:
        subprocess.run(["systemctl", "--user", "disable", name], capture_output=True)
        unit_dir = _get_unit_dir(context)
        unit_path = os.path.join(unit_dir, name)
        if os.path.isfile(unit_path):
            os.remove(unit_path)