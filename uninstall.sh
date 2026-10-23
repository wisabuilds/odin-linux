#!/usr/bin/env bash
# Odin Linux Uninstaller
set -e

if [ "$EUID" -eq 0 ]; then
    PREFIX="/usr/local"
    REMOVE_UDEV=true
else
    PREFIX="$HOME/.local"
    REMOVE_UDEV=false
fi

echo "[+] Removing Odin Linux files from $PREFIX..."
rm -f "$PREFIX/bin/odin-linux"
rm -f "$PREFIX/bin/odin4"
rm -rf "$PREFIX/share/odin-linux"
rm -f "$PREFIX/share/applications/com.samsung.odin.linux.desktop"
rm -f "$PREFIX/share/applications/odin-linux.desktop"
rm -f "$PREFIX/share/icons/hicolor/scalable/apps/com.samsung.odin.linux.svg"

if [ "$REMOVE_UDEV" = true ] && [ -f /etc/udev/rules.d/60-odin4.rules ]; then
    echo "[+] Removing udev rules..."
    rm -f /etc/udev/rules.d/60-odin4.rules
    udevadm control --reload-rules 2>/dev/null || true
    udevadm trigger 2>/dev/null || true
fi

# Refresh desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true
fi

echo "[✔] Odin Linux has been uninstalled."
