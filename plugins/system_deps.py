"""
System Dependencies Plugin

Installs system dependencies via apt package manager.
"""

import subprocess
from typing import Any, Dict, List


# Commands to check for presence (used in hook_check_prerequisites and hook_verify)
# MUST be actual executables, not package names.
REQUIRED_COMMANDS = [
    "curl",
    "wget",
    "git",
    "python3",
    "pip",
    "make",        # from build-essential
    "gcc",         # from build-essential
    "iptables",
    "jq",
    "openssl",
    "socat",
    "unzip",
]

# Mapping from command to apt package(s) needed if command is missing.
_COMMAND_TO_PACKAGES = [
    ("curl", "curl"),
    ("wget", "wget"),
    ("git", "git"),
    ("python3", "python3"),
    ("pip", "python3-pip"),
    ("make", "build-essential"),
    ("gcc", "build-essential"),
    ("iptables", "iptables"),
    ("jq", "jq"),
    ("openssl", "openssl"),
    ("socat", "socat"),
    ("unzip", "unzip"),
]


def _is_wsl() -> bool:
    """Detect WSL2 environment."""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except Exception:
        return False


def command_exists(cmd: str) -> bool:
    """Check if a command exists in PATH."""
    try:
        subprocess.run(["which", cmd], capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def _missing_commands() -> List[str]:
    """Return list of required commands that are not in PATH."""
    missing = []
    for cmd in REQUIRED_COMMANDS:
        # WSL2 does not have iptables — skip check
        if cmd == "iptables" and _is_wsl():
            continue
        if not command_exists(cmd):
            missing.append(cmd)
    return missing


def hook_check_prerequisites(context: Dict[str, Any]) -> bool:
    """
    Check if all required system commands are already installed.

    Returns True if all commands exist, False otherwise.
    """
    missing = _missing_commands()
    if missing:
        print(f"Missing commands: {', '.join(missing)}")
        return False
    print("All system dependencies are already installed.")
    return True


def hook_install(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Install missing system dependencies via apt.

    Idempotent: if all commands are present, skips installation entirely.
    Maps commands to apt packages (e.g. gcc -> build-essential).
    """
    missing_cmds = _missing_commands()
    if not missing_cmds:
        print("All system dependencies already present — nothing to install.")
        return {"installed": True, "commands": [], "skipped": True}

    # Collect unique apt packages to install
    pkg_set = set()
    for cmd in missing_cmds:
        if cmd == "iptables" and _is_wsl():
            continue  # skip iptables on WSL2
        for c, pkg in _COMMAND_TO_PACKAGES:
            if c == cmd:
                pkg_set.add(pkg)
                break

    print(f"Installing missing system dependencies: {', '.join(sorted(pkg_set))}")
    subprocess.run(["apt-get", "update"], check=True)
    subprocess.run(["apt-get", "install", "-y"] + sorted(pkg_set), check=True)

    return {
        "installed": True,
        "commands": missing_cmds,
        "packages": sorted(pkg_set),
        "skipped": False,
    }


def hook_verify(context: Dict[str, Any]) -> bool:
    """
    Verify all required commands are accessible.

    Returns True if all commands exist, raises RuntimeError otherwise.
    """
    for cmd in REQUIRED_COMMANDS:
        if cmd == "iptables" and _is_wsl():
            continue
        if not command_exists(cmd):
            raise RuntimeError(f"Command verification failed: {cmd} not found")

    print("All packages verified successfully.")
    return True


def hook_cleanup(context: Dict[str, Any]) -> None:
    """Clean up apt cache."""
    print("Cleaning up apt cache...")
    subprocess.run(["apt-get", "clean"], check=True)