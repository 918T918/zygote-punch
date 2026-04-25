#!/bin/bash
set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "[-] This script must be run as root to install system-wide."
  echo "    Please run: sudo ./install_system_wide.sh"
  exit 1
fi

echo "[*] Installing Zygote Injection Toolkit system-wide..."

# Ensure created files are readable/executable by everyone
umask 0022

# Install the package using pip in the current directory
# --break-system-packages is needed on some modern distros (Debian/Ubuntu/Arch) 
# that enforce PEP 668, unless using a virtualenv. 
# Since the user specifically asked for "system wide", we attempt to force it or fallback.

if pip install . --break-system-packages 2>/dev/null; then
    echo "[+] Successfully installed with --break-system-packages."
else
    echo "[*] Retrying with standard pip install..."
    pip install .
fi

# Locate and fix permissions for the binary just in case
BIN_PATH=$(which zygote-punch || echo "")
if [ -n "$BIN_PATH" ]; then
    echo "[*] Setting permissions for $BIN_PATH..."
    chmod a+rx "$BIN_PATH"
fi

echo ""
echo "========================================================"
echo "[+] Installation complete!"
echo "    You can now run the toolkit from anywhere using:"
echo "    zygote-punch"
echo ""
echo "    NOTE: To use this tool as a normal user, ensure your user"
echo "    is in the 'plugdev' or 'adbusers' group to access ADB devices."
echo "    Example: sudo usermod -aG plugdev \$USER"
echo "========================================================"
