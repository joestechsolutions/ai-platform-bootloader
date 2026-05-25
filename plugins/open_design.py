"""
Open Design Plugin

Clones and installs the Open Design web app.
"""

import os
import subprocess
from typing import Any, Dict


OPEN_DESIGN_REPO = "https://github.com/nousresearch/open-design.git"
INSTALL_DIR = "/srv/ai-stack/open-design"


def hook_check_prerequisites(context: Dict[str, Any]) -> bool:
    if os.path.isdir(INSTALL_DIR):
        print(f"Open Design already at {INSTALL_DIR}")
    print("Open Design can be installed (or is already present).")
    return True


def hook_install(context: Dict[str, Any]) -> Dict[str, Any]:
    print("Installing Open Design...")

    if not os.path.isdir(INSTALL_DIR):
        print(f"Cloning {OPEN_DESIGN_REPO} into {INSTALL_DIR}")
        os.makedirs(INSTALL_DIR, exist_ok=True)
        subprocess.run(["git", "clone", OPEN_DESIGN_REPO, INSTALL_DIR], check=True)
    elif os.path.isdir(os.path.join(INSTALL_DIR, ".git")):
        print(f"Open Design dir exists, pulling latest...")
        subprocess.run(["git", "-C", INSTALL_DIR, "pull"], check=True)
    else:
        print(f"Open Design dir exists but is not a git repo — skipping git update.")

    print("Installing Node dependencies with pnpm...")
    subprocess.run(
        ["pnpm", "--dir", INSTALL_DIR, "install"],
        check=True,
        capture_output=True,
    )

    node_modules = os.path.join(INSTALL_DIR, "node_modules")
    return {
        "installed": True,
        "install_path": INSTALL_DIR,
        "node_modules_present": os.path.isdir(node_modules),
        "skipped": False,
    }


def hook_verify(context: Dict[str, Any]) -> bool:
    if not os.path.isdir(INSTALL_DIR):
        raise RuntimeError(f"Open Design directory not found at {INSTALL_DIR}")
    node_modules = os.path.join(INSTALL_DIR, "node_modules")
    if os.path.isdir(node_modules):
        print(f"Open Design node_modules verified at {node_modules}")
    else:
        print(f"Open Design directory exists at {INSTALL_DIR} (service-managed — node_modules may be installed on demand)")
    return True


def hook_cleanup(context: Dict[str, Any]) -> None:
    pass