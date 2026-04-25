#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]; then
  echo "[-] This script must be run as root."
  echo "    Please run: sudo ./install_safe.sh"
  exit 1
fi

echo "[*] Phase 1: Cleaning up previous system-wide installation..."
# Attempt to uninstall using both flags to catch however it was installed
pip uninstall -y zygote_injection_toolkit --break-system-packages 2>/dev/null || true
pip uninstall -y zygote_injection_toolkit 2>/dev/null || true

# Explicitly remove the binary if pip didn't catch it
rm -f /usr/local/bin/zygote-punch
rm -f /usr/bin/zygote-punch

echo "[*] Phase 2: Setting up isolated environment..."
INSTALL_DIR="/opt/zygote-punch"

# Remove existing install dir if it exists
if [ -d "$INSTALL_DIR" ]; then
    echo "    Removing existing directory $INSTALL_DIR..."
    rm -rf "$INSTALL_DIR"
fi
mkdir -p "$INSTALL_DIR"

echo "    Copying project files to $INSTALL_DIR..."
# Copy current directory to /opt, excluding common clutter
rsync -av --exclude 'venv' --exclude 'build' --exclude 'dist' --exclude '*.egg-info' --exclude '.git' . "$INSTALL_DIR" > /dev/null 2>&1 || cp -r . "$INSTALL_DIR"

cd "$INSTALL_DIR"

echo "    Creating virtual environment..."
# Check for python3-venv functionality
if ! python3 -m venv venv; then
    echo "[-] Failed to create venv. Installing python3-venv might fix this (e.g., apt install python3-venv)."
    echo "    Attempting fallback to 'virtualenv'..."
    virtualenv venv
fi

echo "    Installing toolkit dependencies into venv..."
./venv/bin/pip install .

echo "[*] Phase 3: Creating launcher..."
WRAPPER_PATH="/usr/local/bin/zygote-punch"

cat <<EOF > "$WRAPPER_PATH"
#!/bin/bash
# Launcher for Zygote Injection Toolkit
exec "$INSTALL_DIR/venv/bin/zygote-punch" "\$@"
EOF

chmod +x "$WRAPPER_PATH"

# Ensure permissions are correct for all users
chmod -R a+rX "$INSTALL_DIR"

echo ""
echo "========================================================"
echo "[+] Installation Complete!"
echo "    The toolkit is now installed in an isolated environment at:"
echo "    $INSTALL_DIR"
echo ""
echo "    You can launch it simply by running:"
echo "    zygote-punch"
echo ""
echo "    (Note: ADB permissions still apply for non-root users)"
echo "========================================================"
