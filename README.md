# Odin Linux

A native GTK4 / Libadwaita graphical frontend for Samsung's official `odin4` command-line flashing utility on Linux.

Samsung distributes an official 64-bit Linux binary of Odin (`odin4`), but it only provides a CLI interface with manual flags (`-b`, `-a`, `-c`, `-s`, `-d`). Flashing multi-gigabyte factory firmware archives across multiple partition files, handling tar extraction, choosing between `CSC` and `HOME_CSC`, and monitoring raw stdout in a terminal is tedious and easy to mess up.

**Odin Linux** wraps the `odin4` engine in a native desktop interface with automatic device detection, archive extraction, slot mapping, and real-time progress parsing.

---

## Features

- **Firmware Archive Auto-Discovery**: Select a stock firmware `.zip` or directory; files are automatically extracted and assigned to their respective partition slots (`BL`, `AP`, `CP`, `CSC`, `HOME_CSC`).
- **CSC Mode Switch**: One-click toggle between **Clean Flash** (`CSC_*`, wipes data / factory resets) and **Preserve Data** (`HOME_CSC_*`, upgrades system partitions while keeping user data).
- **USB Device Polling**: Automatically checks `/dev/bus/usb` for Samsung devices connected in Download Mode.
- **Progress Tracking**: Parses Odin's output stream in real-time, providing stage status (MD5 verification, handshake, partition write, reboot) and percentage progress bars.
- **Engine Flexibility**: Includes the official 64-bit `odin4` binary out of the box, with automatic fallback to any `odin4` in your system `$PATH` or custom `$ODIN4_BIN`.
- **Integrated Log Console**: Monospace output log with clipboard copy and file export options for troubleshooting.

---

## Requirements

The application requires Python 3.10+ with GTK4 and Libadwaita bindings.

### Ubuntu / Debian / Pop!_OS / Linux Mint
```bash
sudo apt update
sudo apt install -y python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 libusb-1.0-0
```

### Fedora / RHEL
```bash
sudo dnf install -y python3 python3-gobject gtk4 libadwaita libusb1
```

### Arch Linux / Manjaro
```bash
sudo pacman -S --needed python-gobject gtk4 libadwaita libusb
```

---

## Installation

### System-Wide Install
Installs the binary to `/usr/local/bin`, installs desktop shortcuts and icons to `/usr/local/share`, and configures udev rules:

```bash
git clone https://github.com/wisabuilds/odin-linux.git
cd odin-linux
sudo ./install.sh
```

### User-Only Install
To install without root to `~/.local`:

```bash
./install.sh
```
*(If installing as a regular user, you must still configure udev rules once using `sudo ./setup_udev_rules.sh` to allow USB access).*

### Running Without Installing
You can run the application directly from the repository folder:

```bash
./bin/odin-linux
```

---

## USB Permissions (udev rules)

By default, Linux requires root permissions to talk to raw USB devices in Download Mode. To allow flashing without running the GUI as root:

1. Create `/etc/udev/rules.d/60-odin4.rules`:
   ```udev
   SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", MODE="0666", GROUP="plugdev"
   SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", ATTR{idProduct}=="685d", MODE="0666", GROUP="plugdev"
   ```
2. Reload udev:
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

Or simply run the included script:
```bash
sudo ./setup_udev_rules.sh
```

---

## Partition Slots Reference

| Slot | File Prefix | Description |
| :--- | :--- | :--- |
| **BL** | `BL_*` | Bootloader components (`sbl1`, `aboot`, `tz`, `devcfg`, `param`) |
| **AP** | `AP_*` | System core (`boot.img`, `recovery.img`, `super.img`, `vbmeta.img`) |
| **CP** | `CP_*` | Baseband radio and modem firmware |
| **CSC** | `CSC_*` | Carrier configuration and PIT repartitioning. **Wipes all user data.** |
| **HOME_CSC** | `HOME_CSC_*` | Carrier configuration without wiping userdata. Used for regular upgrades. |

---

## Entering Download Mode

1. Unplug the phone from USB and power it off completely (if bootlooping, hold `Power` + `Volume Down` for ~7 seconds until screen turns off).
2. Press and hold both **Volume Up** and **Volume Down** buttons simultaneously.
3. While holding both buttons, plug the phone into your computer via USB.
4. When the teal warning screen appears, release all buttons and press **Volume Up** once.
5. The device status badge in Odin Linux will turn green and display **CONNECTED**.

---

## Uninstall

To remove installed files and shortcuts:

```bash
sudo ./uninstall.sh
```

---

## Disclaimer

Flashing firmware carries inherent risk. Ensure your device has adequate battery charge (at least 50%) and use a reliable USB cable and port. The authors are not responsible for bricked devices, lost data, or hardware damage.

This project is an independent community interface and is not affiliated with, maintained by, or endorsed by Samsung Electronics.

---

## License

This GUI wrapper is licensed under the [GNU General Public License v3.0](LICENSE) (GPL-3.0-or-later).  
The underlying `odin4` binary is proprietary software of Samsung Electronics Co., Ltd.
