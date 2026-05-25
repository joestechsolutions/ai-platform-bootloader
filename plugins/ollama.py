"""
Ollama Plugin

Installs and configures the Ollama service.
"""

import subprocess
from typing import Any, Dict


def command_exists(cmd: str) -> bool:
    """Check if a command exists in PATH."""
    try:
        subprocess.run(["which", cmd], capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def hook_check_prerequisites(context: Dict[str, Any]) -> bool:
    """
    Check if Ollama is already installed.

    Returns True if ollama command exists, False otherwise.
    """
    if command_exists("ollama"):
        print("Ollama is already installed.")
        return True
    print("Ollama is not installed.")
    return False


def hook_install(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Install Ollama, configure it to bind to 127.0.0.1, and enable/start the service.

    Returns:
        Dict with installation results.
    """
    print("Installing Ollama...")

    # Install Ollama using official script
    subprocess.run(
        ["curl", "-fsSL", "https://ollama.ai/install.sh", "-o", "/tmp/install_ollama.sh"],
        check=True
    )
    subprocess.run(["bash", "/tmp/install_ollama.sh"], check=True)

    # Configure Ollama to bind only to localhost
    # Create or update /etc/systemd/system/ollama.service drop-in
    print("Configuring Ollama to bind to 127.0.0.1...")
    service_dir = "/etc/systemd/system/ollama.service.d"
    subprocess.run(["mkdir", "-p", service_dir], check=True)

    dropin_content = """[Service]
Environment="OLLAMA_HOST=127.0.0.1:11434"
"""
    subprocess.run(
        ["sh", "-c", f"echo '{dropin_content}' > {service_dir}/bind.conf"],
        check=True
    )

    # Reload systemd, enable and start service
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "ollama"], check=True)
    subprocess.run(["systemctl", "start", "ollama"], check=True)

    return {
        "installed": True
    }


def hook_verify(context: Dict[str, Any]) -> bool:
    """
    Verify Ollama service is active.

    Returns True if systemctl is-active ollama returns 'active', raises otherwise.
    """
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "ollama"],
            capture_output=True,
            text=True,
            check=True
        )
        status = result.stdout.strip()
        if status == "active":
            print("Ollama service is active.")
            return True
        else:
            raise RuntimeError(f"Ollama service status is: {status}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ollama verification failed: {e}")


def hook_cleanup(context: Dict[str, Any]) -> None:
    """
    No cleanup needed for Ollama.
    """
    pass
