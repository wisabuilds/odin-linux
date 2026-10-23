#!/usr/bin/env bash
# Setup udev rules for Samsung Odin Linux
set -e

if [ "$EUID" -ne 0 ]; then
    echo "[!] Please run as root: sudo ./setup_udev_rules.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
RULE_FILE="/etc/udev/rules.d/60-odin4.rules"

echo "[+] Installing Samsung USB udev rule to $RULE_FILE..."
if [ -f "$SCRIPT_DIR/udev/60-odin4.rules" ]; then
    cp "$SCRIPT_DIR/udev/60-odin4.rules" "$RULE_FILE"
else
    cat << 'EOF' > "$RULE_FILE"
SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", ATTR{idProduct}=="685d", MODE="0666", GROUP="plugdev"
EOF
fi

chmod 644 "$RULE_FILE"

echo "[+] Reloading udev rules..."
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger 2>/dev/null || true

echo "[✔] Done! Samsung Download Mode devices will now be accessible without root."
