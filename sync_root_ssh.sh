#!/bin/bash

# Script to sync root's SSH key to the current user
ROOT_SSH="/root/.ssh/id_ed25519"
USER_SSH_DIR="$HOME/.ssh"

echo "[*] Ensuring $USER_SSH_DIR exists..."
mkdir -p "$USER_SSH_DIR"
chmod 700 "$USER_SSH_DIR"

if sudo [ -f "$ROOT_SSH" ]; then
    echo "[*] Copying SSH key from root..."
    sudo cp "$ROOT_SSH" "$USER_SSH_DIR/id_ed25519"
    sudo cp "${ROOT_SSH}.pub" "$USER_SSH_DIR/id_ed25519.pub"
    
    echo "[*] Fixing ownership and permissions..."
    sudo chown $USER:$USER "$USER_SSH_DIR/id_ed25519"*
    chmod 600 "$USER_SSH_DIR/id_ed25519"
    chmod 644 "$USER_SSH_DIR/id_ed25519.pub"
    
    echo "[*] Starting SSH agent and adding key..."
    eval "$(ssh-agent -s)"
    ssh-add "$USER_SSH_DIR/id_ed25519"
    
    echo "[*] Testing connection to GitHub..."
    ssh -o StrictHostKeyChecking=no -T git@github.com
else
    echo "[-] Error: Root SSH key not found at $ROOT_SSH"
    exit 1
fi
