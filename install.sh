#!/usr/bin/env bash
# Odin Linux Installer
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

if [ "$EUID" -eq 0 ]; then
    PREFIX="/usr/local"
    INSTALL_UDEV=true
else
    PREFIX="$HOME/.local"
    INSTALL_UDEV=false
    echo "[i] Installing in user mode to $PREFIX (run with sudo for system-wide install)"
fi

BIN_DIR="$PREFIX/bin"
APP_DIR="$PREFIX/share/odin-linux"
DESKTOP_DIR="$PREFIX/share/applications"
ICON_DIR="$PREFIX/share/icons/hicolor/scalable/apps"

echo "[+] Creating installation directories..."
mkdir -p "$BIN_DIR" "$APP_DIR" "$DESKTOP_DIR" "$ICON_DIR"

echo "[+] Copying application files..."
cp -r "$SCRIPT_DIR/odin_linux" "$APP_DIR/"
cp "$SCRIPT_DIR/bin/odin4" "$BIN_DIR/odin4"
chmod +x "$BIN_DIR/odin4"

# Create launcher wrapper in $BIN_DIR
cat << EOF > "$BIN_DIR/odin-linux"
#!/usr/bin/env bash
export PYTHONPATH="$APP_DIR:\$PYTHONPATH"
export ODIN4_BIN="\${ODIN4_BIN:-$BIN_DIR/odin4}"
exec python3 -m odin_linux.app "\$@"
EOF
chmod +x "$BIN_DIR/odin-linux"

echo "[+] Installing desktop application launcher and icon..."
cp "$SCRIPT_DIR/data/com.samsung.odin.linux.desktop" "$DESKTOP_DIR/com.samsung.odin.linux.desktop"
cp "$SCRIPT_DIR/data/com.samsung.odin.linux.desktop" "$DESKTOP_DIR/odin-linux.desktop"
cp "$SCRIPT_DIR/data/icons/hicolor/scalable/apps/com.samsung.odin.linux.svg" "$ICON_DIR/com.samsung.odin.linux.svg"
cp "$SCRIPT_DIR/data/icons/hicolor/scalable/apps/com.samsung.odin.linux.svg" "$ICON_DIR/odin-linux.svg"

# Update caches
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$PREFIX/share/icons/hicolor" 2>/dev/null || true
fi

# Install udev rules if root
if [ "$INSTALL_UDEV" = true ]; then
    echo "[+] Installing udev rules..."
    cp "$SCRIPT_DIR/udev/60-odin4.rules" /etc/udev/rules.d/60-odin4.rules
    udevadm control --reload-rules 2>/dev/null || true
    udevadm trigger 2>/dev/null || true
else
    echo "[!] To enable non-root USB access for Download Mode devices, run:"
    echo "    sudo ./setup_udev_rules.sh"
fi

echo ""
echo "=========================================================="
echo " [✔] Odin Linux installed successfully to $PREFIX!"
echo " Launch it via your app menu or run: odin-linux"
echo "=========================================================="
