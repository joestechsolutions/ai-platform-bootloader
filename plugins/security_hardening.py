"""
Security Hardening Plugin

Sets restrictive file permissions on user dotdirs and applies
network-level hardening (iptables) on native Linux.
Skips iptables gracefully on WSL2 (command not available).
"""

import os
import stat
import subprocess
from typing import Any, Dict


# Directories to protect with mode 700
PROTECTED_DIRS = [
    ".hermes",
    ".hermes/sessions",
    ".hermes/logs",
    ".hermes/memories",
    ".hermes/checkpoints",
    ".openclaw",
    ".openclaw/workspace",
    ".mempalace",
]

# Files to protect with mode 600
PROTECTED_FILES = [
    ".hermes/config.yaml",
    ".hermes/.env",
    ".openclaw/config.yaml",
]


def _command_exists(cmd: str) -> bool:
    try:
        subprocess.run(["which", cmd], capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def _is_wsl() -> bool:
    """Detect WSL2 environment."""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except Exception:
        return False


def _chmod_recursive(path: str, mode: int) -> None:
    """Recursively set file permissions."""
    for root, dirs, files in os.walk(path):
        os.chmod(root, mode)
        for d in dirs:
            os.chmod(os.path.join(root, d), mode)
        for fname in files:
            fpath = os.path.join(root, fname)
            # For files, remove execute bit
            current = os.stat(fpath).st_mode
            os.chmod(fpath, current & 0o777 & ~0o111)


def hook_check_prerequisites(context: Dict[str, Any]) -> bool:
    """
    Always returns True — install applies hardening if needed.
    """
    user_home = context.get("USER_HOME", os.path.expanduser("~"))
    hermes = os.path.join(user_home, ".hermes")
    if not os.path.isdir(hermes):
        print("Hermes directory doesn't exist yet — will be created during install.")
    else:
        try:
            perms = os.stat(hermes).st_mode & 0o777
            if perms == 0o700:
                print("Hermes directory is already secured (mode 700).")
            else:
                print(f"Hermes directory has mode {oct(perms)} — will apply hardening.")
        except Exception as e:
            print(f"Could not check permissions: {e} — will apply hardening.")
    return True


def hook_install(context: Dict[str, Any]) -> Dict[str, Any]:
    print("Applying security hardening...")

    user_home = context.get("USER_HOME", os.path.expanduser("~"))
    applied = []
    skipped = []

    # Set restrictive permissions on directories
    for dir_name in PROTECTED_DIRS:
        dir_path = os.path.join(user_home, dir_name)
        if not os.path.isdir(dir_path):
            skipped.append(f"{dir_name} (not found)")
            continue
        _chmod_recursive(dir_path, 0o700)
        applied.append(dir_name)

    # Set restrictive permissions on config files
    for file_name in PROTECTED_FILES:
        file_path = os.path.join(user_home, file_name)
        if not os.path.isfile(file_path):
            skipped.append(f"{file_name} (not found)")
            continue
        os.chmod(file_path, 0o600)
        applied.append(file_name)

    # Network hardening — skip on WSL2
    if _is_wsl():
        print("WSL2 detected — skipping iptables network hardening.")
        skipped.append("iptables (WSL2)")
    elif _command_exists("iptables"):
        print("Applying iptables rules...")
        # Flush existing rules and set secure defaults
        rules = [
            ["iptables", "-F"],
            ["iptables", "-X"],
            ["iptables", "-P", "INPUT", "DROP"],
            ["iptables", "-A", "INPUT", "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT"],
            ["iptables", "-A", "INPUT", "-i", "lo", "-j", "ACCEPT"],
            ["iptables", "-A", "INPUT", "-p", "tcp", "--dport", "22", "-j", "ACCEPT"],
            ["iptables", "-A", "INPUT", "-s", "127.0.0.0/8", "-j", "ACCEPT"],
        ]
        for rule in rules:
            subprocess.run(rule, capture_output=True)
        applied.append("iptables rules")
    else:
        print("iptables not available — skipping network hardening.")
        skipped.append("iptables (not available)")

    print(f"Hardening applied: {applied}")
    if skipped:
        print(f"Skipped: {skipped}")
    return {"installed": True, "applied": applied, "skipped": skipped}


def hook_verify(context: Dict[str, Any]) -> bool:
    user_home = context.get("USER_HOME", os.path.expanduser("~"))
    errors = []

    for dir_name in PROTECTED_DIRS:
        dir_path = os.path.join(user_home, dir_name)
        if not os.path.isdir(dir_path):
            continue  # skip non-existent dirs in verify
        perms = os.stat(dir_path).st_mode & 0o777
        if perms != 0o700:
            errors.append(f"{dir_name} has mode {oct(perms)}, expected 0o700")

    for file_name in PROTECTED_FILES:
        file_path = os.path.join(user_home, file_name)
        if not os.path.isfile(file_path):
            continue  # skip non-existent files in verify
        perms = os.stat(file_path).st_mode & 0o777
        if perms != 0o600:
            errors.append(f"{file_name} has mode {oct(perms)}, expected 0o600")

    if errors:
        raise RuntimeError(f"Security hardening verification failed: {'; '.join(errors)}")
    print("Security hardening verified successfully.")
    return True


def hook_cleanup(context: Dict[str, Any]) -> None:
    # Cannot really undo file permissions without knowing originals
    print("Security hardening cleanup — file permissions are persistent.")
    # If WSL2 was hardened, restore iptables to ACCEPT
    if not _is_wsl() and _command_exists("iptables"):
        subprocess.run(["iptables", "-P", "INPUT", "ACCEPT"], capture_output=True)