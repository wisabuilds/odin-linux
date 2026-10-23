<div align="center">

# Odin Linux

### Modern GTK4 & Libadwaita GUI for Samsung Odin4 CLI

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![GTK 4](https://img.shields.io/badge/GTK-4.0-4a86cf.svg?logo=gnome&logoColor=white)](https://www.gtk.org/)
[![Libadwaita](https://img.shields.io/badge/UI-Libadwaita-00c853.svg)](https://gnome.pages.gitlab.gnome.org/libadwaita/)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-FCC624.svg?logo=linux&logoColor=black)](https://kernel.org)

An authentic, modern desktop experience bringing official Samsung Odin firmware flashing capabilities natively to Linux desktops.

</div>

---

## ✨ Features

- **🎨 Modern Libadwaita & GTK4 Design**: Follows the GNOME Human Interface Guidelines (HIG) with dark/light theme support, responsive cards, and clean typography.
- **🔌 Real-Time USB Device Detection**: Constantly polls and detects Samsung devices in Download Mode without requiring manual interface restarts.
- **📦 Smart Archive Extraction & Auto-Discovery**: Open complete firmware `.zip` files directly; Odin Linux automatically extracts them and maps `BL`, `AP`, `CP`, `CSC`, and `HOME_CSC` to their designated slots.
- **🔄 Smart CSC Switcher**:
  - **Clean Flash (`CSC`)**: Performs a full factory wipe to resolve software bricks, bootloops, or region swaps.
  - **Data Preservation (`HOME_CSC`)**: Upgrades firmware while keeping user apps and files untouched.
- **🛡️ Pre-Flight Verification**: Confirmation safety modal prevents accidental flashing and verifies battery and cable readiness.
- **📊 5-Stage Stepper & Live Streaming Progress**:
  1. Pre-Flight Setup
  2. MD5 Archive Verification
  3. Handshake & PIT verification
  4. Flash writing to individual partitions (`super`, `boot`, `recovery`, `vbmeta`, etc.)
  5. Finalization and automatic reboot
- **📋 Live Console Utilities**: Monospace streaming terminal log with instant **Copy Log** and **Save Log** export features.

---

## 📸 Screenshots & Architecture

```
+-----------------------------------------------------------------------------------+
|  [ Load Firmware ]               Odin Linux                [ Recovery Guide ]     |
+------------------------------------------+----------------------------------------+
|  DEVICE STATUS                           |  FLASHING PIPELINE                     |
|  [📱] Samsung Device Connected           |  (1) Pre-Flight -> (2) MD5 -> ...      |
|      Download Mode (/dev/bus/usb/001/04) |                                        |
|                                          |  [======== 58% Writing: super.img ===] |
|  FIRMWARE PACKAGES                       |                                        |
|  [BL]  BL_A065FXXU1AXH7.tar.md5          |       [ Start Flashing ]  [ Cancel ]   |
|  [AP]  AP_A065FXXU1AXH7.tar.md5          |                                        |
|  [CP]  CP_A065FXXU1AXH7.tar.md5          +----------------------------------------+
|  [CSC] CSC_OXM_A065FXXU1AXH7.tar.md5     |  TERMINAL LOG        [Copy] [Save]     |
|                                          |  > Check file : AP_A065FXXU1...        |
|  OPTIONS                                 |  > Setup Connection (Thor Protocol)    |
|  [x] Clean Flash (Factory Reset)         |  > Writing partition: boot.img.lz4     |
|  [x] Auto Reboot                         |  > Writing partition: super.img.lz4    |
+------------------------------------------+----------------------------------------+
```

---

## 🚀 Installation

### Prerequisites

Ensure you have Python 3.10+ and the GTK4 / Libadwaita development packages installed:

**Debian / Ubuntu / Pop!_OS / Linux Mint:**
```bash
sudo apt update
sudo apt install -y python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 libusb-1.0-0
```

**Fedora / RHEL / Nobara:**
```bash
sudo dnf install -y python3 python3-gobject gtk4 libadwaita libusb1
```

**Arch Linux / Manjaro:**
```bash
sudo pacman -S --needed python-gobject gtk4 libadwaita libusb
```

---

### One-Line Install

Clone this repository and run the installer:

```bash
git clone https://github.com/wisabuilds/odin-linux.git
cd odin-linux

# System-wide installation (installs to /usr/local and sets up udev rules):
sudo ./install.sh

# Or install for current user only:
./install.sh
```

---

## ⚡ USB Access (udev Rules)

To enable Linux to communicate with Samsung Download Mode devices over USB without requiring root privileges:

```bash
sudo ./setup_udev_rules.sh
```

This creates `/etc/udev/rules.d/60-odin4.rules` with the Samsung USB IDs (`04e8:685d`) and reloads the udev daemon.

---

## 📖 How to Use

1. **Launch Odin Linux** from your desktop app menu or run `odin-linux` in your terminal.
2. **Boot your Samsung phone into Download Mode**:
   - Disconnect the USB cable.
   - Power off the phone completely (hold `Power` + `Vol Down` for 7 seconds if bootlooping).
   - Hold **Volume Up + Volume Down** simultaneously.
   - Connect the USB cable to your PC while holding both buttons.
   - When the teal warning screen appears, press **Volume Up** once.
   - The status badge in Odin Linux will turn **GREEN (CONNECTED)**.
3. Click **Load Firmware** to pick your `.zip` firmware package, or choose individual `BL`, `AP`, `CP`, and `CSC` tar archives.
4. Toggle **Clean Flash**:
   - `ON` (uses `CSC_*`) — Wipes data, recommended for unbricking or clean installs.
   - `OFF` (uses `HOME_CSC_*`) — Preserves user data and apps.
5. Click **Start Flashing**.

---

## 📂 Project Structure

```
odin-linux/
├── bin/
│   ├── odin-linux                   # Application launcher script
│   └── odin4                        # Samsung Odin4 engine binary
├── data/
│   ├── com.samsung.odin.linux.desktop
│   └── icons/hicolor/scalable/apps/
│       └── com.samsung.odin.linux.svg
├── odin_linux/
│   ├── __init__.py
│   └── app.py                       # Main GTK4 / Libadwaita application
├── udev/
│   └── 60-odin4.rules               # Udev USB permissions rule
├── .github/workflows/ci.yml         # Continuous integration
├── install.sh                       # One-click installer
├── uninstall.sh                     # Uninstaller
├── setup_udev_rules.sh              # Standalone udev setup
├── Makefile
├── pyproject.toml
└── README.md
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to open an issue or submit a pull request on [GitHub](https://github.com/wisabuilds/odin-linux).

---

## 📜 License

Distributed under the **GNU General Public License v3.0** (GPL-3.0). See [`LICENSE`](LICENSE) for details.
Samsung Odin engine (`odin4`) is proprietary software of Samsung Electronics Co., Ltd.
