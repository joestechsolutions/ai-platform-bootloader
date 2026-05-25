#!/usr/bin/env bash
#
# bootstrap.sh — Bootstrap the Hermes Infrastructure Suite Bootloader
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[bootstrap] Ensuring system dependencies..."
if ! command -v python3 >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq python3 python3-venv python3-pip git curl
fi

# Always install system_deps packages (system_deps plugin checks for them)
apt-get update -qq
apt-get install -y -qq \
    build-essential jq unzip iptables socat openssl curl wget git 2>/dev/null || \
apt-get install -y -qq \
    build-essential jq unzip iptables socat openssl curl wget git

cd "$SCRIPT_DIR"

echo "[bootstrap] Installing bootloader..."
pip install -e . --quiet --break-system-packages 2>/dev/null || pip install -e . --break-system-packages

echo "[bootstrap] Running bootloader CLI..."
python3 -m bootloader.cli "$@"