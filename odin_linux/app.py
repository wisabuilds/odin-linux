#!/usr/bin/env python3
"""
Odin Linux - Modern GTK4 / Libadwaita GUI for Samsung Odin4 CLI
https://github.com/wisabuilds/odin-linux

Features:
- Native Libadwaita / GTK4 interface conforming to GNOME HIG
- Real-time USB Download Mode polling and detection
- Direct ZIP file extraction and folder auto-discovery
- Smart CSC switcher (Clean Flash vs HOME_CSC data preservation)
- Pre-flight safety confirmation modal
- Streaming percentage progress bar and live terminal log
- One-click Copy Log and Save Log utilities
"""

import os
import sys
import re
import glob
import shutil
import zipfile
import subprocess
import threading
import time
from datetime import datetime
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
gi.require_version('GLib', '2.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk


def find_odin_binary():
    env_bin = os.environ.get("ODIN4_BIN")
    if env_bin and os.path.isfile(env_bin) and os.access(env_bin, os.X_OK):
        return env_bin

    which_bin = shutil.which("odin4")
    if which_bin:
        return which_bin

    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "odin4"),
        os.path.join(base_dir, "..", "bin", "odin4"),
        os.path.join(base_dir, "bin", "odin4"),
        "/usr/local/bin/odin4",
        "/usr/bin/odin4",
        os.path.expanduser("~/.local/bin/odin4"),
    ]
    for c in candidates:
        norm = os.path.normpath(c)
        if os.path.isfile(norm) and os.access(norm, os.X_OK):
            return norm

    return "odin4"


ODIN_PATH = find_odin_binary()

CUSTOM_CSS = """
/* Authentic Adwaita / GNOME Theme */
.odin-stage-badge {
    border-radius: 9999px;
    min-width: 24px;
    min-height: 24px;
    font-weight: 700;
    font-size: 11px;
    padding: 2px 6px;
}

.stage-pending {
    background-color: alpha(@window_fg_color, 0.1);
    color: alpha(@window_fg_color, 0.6);
}

.stage-active {
    background-color: @accent_bg_color;
    color: @accent_fg_color;
}

.stage-done {
    background-color: #2ec27e;
    color: #ffffff;
}

.stage-arrow {
    color: alpha(@window_fg_color, 0.25);
    font-size: 12px;
}

.slot-tag {
    border-radius: 6px;
    padding: 3px 8px;
    font-weight: 800;
    font-size: 11px;
    font-family: monospace;
    min-width: 34px;
}

.slot-tag-bl {
    background-color: rgba(229, 165, 10, 0.18);
    color: #f6d32d;
    border: 1px solid rgba(229, 165, 10, 0.35);
}

.slot-tag-ap {
    background-color: rgba(53, 132, 228, 0.18);
    color: #62a0ea;
    border: 1px solid rgba(53, 132, 228, 0.35);
}

.slot-tag-cp {
    background-color: rgba(145, 65, 172, 0.18);
    color: #c061cb;
    border: 1px solid rgba(145, 65, 172, 0.35);
}

.slot-tag-csc {
    background-color: rgba(46, 194, 126, 0.18);
    color: #57e389;
    border: 1px solid rgba(46, 194, 126, 0.35);
}

.device-badge-ok {
    background-color: rgba(46, 194, 126, 0.18);
    color: #57e389;
    border: 1px solid rgba(46, 194, 126, 0.35);
    border-radius: 9999px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}

.device-badge-missing {
    background-color: rgba(224, 27, 36, 0.18);
    color: #ff7b63;
    border: 1px solid rgba(224, 27, 36, 0.35);
    border-radius: 9999px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}

.odin-console-scrolled {
    background-color: #1a1a1a;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
}

.odin-console-view {
    background-color: transparent;
    color: #dcdcdc;
    font-family: monospace;
    font-size: 11.5px;
}

.odin-pipeline-card {
    background-color: @card_bg_color;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 18px 20px;
}
"""


class OdinApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.samsung.odin.linux",
            flags=Gio.ApplicationFlags.NON_UNIQUE
        )
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = OdinWindow(self)
        self.window.present()


class OdinWindow(Adw.Window):
    def __init__(self, app=None):
        super().__init__()
        if app:
            self.set_application(app)
        self.set_title("Odin Linux — Samsung Flash Utility")
        self.set_default_size(1080, 680)

        self.flash_process = None
        self.is_flashing = False
        self.connected_device = None

        # Discovered CSC candidates for smart toggle
        self.found_csc = None
        self.found_home_csc = None

        self.slot_rows = {}
        self.slot_descs = {}

        self.setup_css()
        self.setup_ui()
        self.check_device()

        # Poll USB connection every 2 seconds
        GLib.timeout_add_seconds(2, self.check_device)

    def setup_css(self):
        try:
            provider = Gtk.CssProvider()
            provider.load_from_data(CUSTOM_CSS.encode())
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
        except Exception:
            pass

    def setup_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(main_box)

        # Header bar
        header = Adw.HeaderBar()
        title_widget = Adw.WindowTitle(title="Odin Linux", subtitle="Samsung Firmware Flashing Suite")
        header.set_title_widget(title_widget)

        # Quick Load Firmware Button (Zip / Folder)
        load_btn = Gtk.Button(label="Load Firmware", icon_name="archive-extract-symbolic")
        load_btn.set_tooltip_text("Open a firmware .zip file or extracted folder")
        load_btn.connect("clicked", self.on_load_firmware_dialog)
        header.pack_start(load_btn)

        # Download Mode Button Guide
        guide_btn = Gtk.Button(label="Recovery Guide", icon_name="help-about-symbolic")
        guide_btn.set_tooltip_text("Instructions for entering Samsung Download Mode")
        guide_btn.connect("clicked", self.on_show_guide)
        header.pack_end(guide_btn)

        main_box.append(header)

        # Main two-column container
        columns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        columns_box.set_hexpand(True)
        columns_box.set_vexpand(True)
        columns_box.set_margin_start(16)
        columns_box.set_margin_end(16)
        columns_box.set_margin_top(14)
        columns_box.set_margin_bottom(14)
        main_box.append(columns_box)

        # LEFT COLUMN (Setup: Device, Packages, Options)
        left_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        left_column.set_hexpand(True)
        left_column.set_vexpand(True)
        left_column.set_size_request(480, -1)
        columns_box.append(left_column)

        # RIGHT COLUMN (Execution: Stepper, Status, Progress, Buttons, Console)
        right_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        right_column.set_hexpand(True)
        right_column.set_vexpand(True)
        right_column.set_size_request(520, -1)
        columns_box.append(right_column)

        # 1. Device Connection Status Card (Left Column)
        dev_group = Adw.PreferencesGroup(title="Device Status")
        left_column.append(dev_group)

        self.dev_row = Adw.ActionRow(
            title="Samsung Device Connection",
            subtitle="Searching for connected Samsung Download Mode device..."
        )
        self.dev_icon = Gtk.Image(icon_name="phone-symbolic")
        self.dev_icon.set_pixel_size(24)
        self.dev_row.add_prefix(self.dev_icon)

        self.dev_badge = Gtk.Label(label="NO DEVICE")
        self.dev_badge.set_css_classes(["device-badge-missing"])
        self.dev_badge.set_valign(Gtk.Align.CENTER)
        self.dev_row.add_suffix(self.dev_badge)

        self.dev_refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        self.dev_refresh_btn.set_valign(Gtk.Align.CENTER)
        self.dev_refresh_btn.set_tooltip_text("Refresh USB connection")
        self.dev_refresh_btn.connect("clicked", lambda b: self.check_device())
        self.dev_row.add_suffix(self.dev_refresh_btn)
        dev_group.add(self.dev_row)

        # 2. Firmware Slots (BL, AP, CP, CSC) (Left Column)
        files_group = Adw.PreferencesGroup(
            title="Firmware Packages (.tar / .tar.md5)",
            description="Select official Samsung archives for each partition"
        )
        left_column.append(files_group)

        self.file_paths = {
            "BL": "",
            "AP": "",
            "CP": "",
            "CSC": ""
        }
        slots = [
            ("BL", "Bootloader", "Bootloader archive (aboot, sbl1, tz, devcfg)"),
            ("AP", "System / Kernel", "Main system, recovery, boot, and super partitions"),
            ("CP", "Modem / Radio", "Cellular baseband modem radio (Skip for Wi-Fi only / cross-region)"),
            ("CSC", "CSC / Region", "Carrier customization and partition setup"),
        ]

        self.slot_clear_btns = {}
        for code, title, desc in slots:
            self.slot_descs[code] = desc
            row = Adw.ActionRow(title=f"{code} — {title}", subtitle=f"No file selected (optional)")
            row.set_activatable(True)
            row.connect("activated", lambda r, c=code: self.on_browse_slot(c))
            self.slot_rows[code] = row

            tag = Gtk.Label(label=code)
            tag.set_css_classes(["slot-tag", f"slot-tag-{code.lower()}"])
            row.add_prefix(tag)

            browse_btn = Gtk.Button(label="Select File")
            browse_btn.set_valign(Gtk.Align.CENTER)
            browse_btn.set_css_classes(["flat"])
            browse_btn.connect("clicked", lambda b, c=code: self.on_browse_slot(c))
            row.add_suffix(browse_btn)

            clear_btn = Gtk.Button(icon_name="edit-clear-symbolic")
            clear_btn.set_valign(Gtk.Align.CENTER)
            clear_btn.set_tooltip_text(f"Clear {code}")
            clear_btn.set_visible(False)
            clear_btn.connect("clicked", lambda b, c=code: self.clear_slot(c))
            row.add_suffix(clear_btn)
            self.slot_clear_btns[code] = clear_btn

            files_group.add(row)

        # 3. Flashing Options & Smart CSC Toggle (Left Column)
        opts_group = Adw.PreferencesGroup(title="Flashing Options")
        left_column.append(opts_group)

        self.clean_flash_switch = Adw.SwitchRow(
            title="Clean Flash (Factory Reset)",
            subtitle="ON: Uses CSC to wipe data and fix boot issues. OFF: Uses HOME_CSC to preserve user data."
        )
        self.clean_flash_switch.set_active(True)
        self.clean_flash_switch.connect("notify::active", self.on_csc_toggle_changed)
        opts_group.add(self.clean_flash_switch)

        self.reboot_switch = Adw.SwitchRow(
            title="Auto Reboot",
            subtitle="Automatically reboot phone into Android after flashing completes"
        )
        self.reboot_switch.set_active(True)
        opts_group.add(self.reboot_switch)

        # 4. Flashing Pipeline Card (Right Column)
        pipeline_group = Adw.PreferencesGroup(title="Flashing Pipeline")
        right_column.append(pipeline_group)

        pipeline_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        pipeline_card.set_css_classes(["odin-pipeline-card"])
        pipeline_group.add(pipeline_card)

        # 5-step Horizontal Stage Stepper
        stage_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        stage_box.set_halign(Gtk.Align.CENTER)
        stage_box.set_margin_top(4)
        stage_box.set_margin_bottom(2)
        pipeline_card.append(stage_box)

        self.stages = [
            ("1", "Pre-Flight"),
            ("2", "MD5 Check"),
            ("3", "Handshake"),
            ("4", "Flash Write"),
            ("5", "Reboot"),
        ]
        self.stage_widgets = []

        for i, (num, name) in enumerate(self.stages):
            item_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            badge = Gtk.Label(label=num)
            badge.set_css_classes(["odin-stage-badge", "stage-pending"])
            lbl = Gtk.Label(label=name)
            lbl.set_css_classes(["caption", "dim-label"])
            item_box.append(badge)
            item_box.append(lbl)
            stage_box.append(item_box)
            self.stage_widgets.append((badge, lbl))

            if i < len(self.stages) - 1:
                arrow = Gtk.Label(label="→")
                arrow.set_css_classes(["stage-arrow"])
                stage_box.append(arrow)

        # Dynamic Status Heading
        self.status_title = Gtk.Label(label="Ready to Flash Official Firmware")
        self.status_title.set_css_classes(["heading"])
        self.status_title.set_halign(Gtk.Align.CENTER)
        pipeline_card.append(self.status_title)

        # Progress Bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text("Ready")
        self.progress_bar.set_margin_start(8)
        self.progress_bar.set_margin_end(8)
        pipeline_card.append(self.progress_bar)

        # Action Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(4)
        pipeline_card.append(btn_box)

        self.start_btn = Gtk.Button(label="Start Flashing")
        self.start_btn.set_css_classes(["suggested-action", "pill"])
        self.start_btn.set_size_request(190, 44)
        self.start_btn.connect("clicked", self.on_start_flash_clicked)
        btn_box.append(self.start_btn)

        self.stop_btn = Gtk.Button(label="Cancel")
        self.stop_btn.set_css_classes(["destructive-action", "pill"])
        self.stop_btn.set_size_request(110, 44)
        self.stop_btn.set_sensitive(False)
        self.stop_btn.connect("clicked", self.on_cancel_flash)
        btn_box.append(self.stop_btn)

        # 5. Live Terminal Console & Utilities (Right Column)
        log_group = Adw.PreferencesGroup(title="Flashing Log")
        right_column.append(log_group)

        # Log toolbar (Copy / Save / Clear)
        log_tool_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        log_tool_box.set_halign(Gtk.Align.END)
        log_tool_box.set_margin_bottom(6)

        copy_log_btn = Gtk.Button(label="Copy Log", icon_name="edit-copy-symbolic")
        copy_log_btn.connect("clicked", self.on_copy_log)
        log_tool_box.append(copy_log_btn)

        save_log_btn = Gtk.Button(label="Save Log", icon_name="document-save-symbolic")
        save_log_btn.connect("clicked", self.on_save_log)
        log_tool_box.append(save_log_btn)

        clear_log_btn = Gtk.Button(label="Clear", icon_name="user-trash-symbolic")
        clear_log_btn.connect("clicked", self.on_clear_log)
        log_tool_box.append(clear_log_btn)

        log_group.add(log_tool_box)

        log_scrolled = Gtk.ScrolledWindow()
        log_scrolled.set_min_content_height(240)
        log_scrolled.set_vexpand(True)
        log_scrolled.set_css_classes(["odin-console-scrolled"])

        self.log_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView(buffer=self.log_buffer)
        self.log_view.set_editable(False)
        self.log_view.set_monospace(True)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.set_margin_start(10)
        self.log_view.set_margin_end(10)
        self.log_view.set_margin_top(10)
        self.log_view.set_margin_bottom(10)
        self.log_view.set_css_classes(["odin-console-view"])

        log_scrolled.set_child(self.log_view)
        log_group.add(log_scrolled)

        global ODIN_PATH
        self.append_log(f"Odin Linux initialized.\nUsing flash engine: {ODIN_PATH}\n\n")

    def set_stage(self, active_step):
        for i, (badge, lbl) in enumerate(self.stage_widgets, 1):
            if i < active_step:
                badge.set_label("✓")
                badge.set_css_classes(["odin-stage-badge", "stage-done"])
                lbl.set_css_classes(["caption"])
            elif i == active_step:
                badge.set_label(str(i))
                badge.set_css_classes(["odin-stage-badge", "stage-active"])
                lbl.set_css_classes(["caption", "heading"])
            else:
                badge.set_label(str(i))
                badge.set_css_classes(["odin-stage-badge", "stage-pending"])
                lbl.set_css_classes(["caption", "dim-label"])
        return False

    def on_show_guide(self, btn):
        self.show_alert(
            "Samsung Download Mode Guide",
            "1. Disconnect USB cable from phone.\n\n"
            "2. Turn off the phone completely (hold Power + Vol Down for 7s if bootlooping).\n\n"
            "3. Press and hold Volume Up AND Volume Down together.\n\n"
            "4. While holding both buttons, connect the USB cable to your computer.\n\n"
            "5. When the turquoise/teal warning screen appears, press Volume Up once.\n\n"
            "6. The status badge will switch to green CONNECTED."
        )

    def _format_size(self, path):
        try:
            sz = os.path.getsize(path)
            if sz >= 1024 * 1024 * 1024:
                return f"{sz / (1024*1024*1024):.2f} GB"
            elif sz >= 1024 * 1024:
                return f"{sz / (1024*1024):.1f} MB"
            return f"{sz / 1024:.0f} KB"
        except Exception:
            return ""

    def update_slot_ui(self, slot, path):
        self.file_paths[slot] = path if path else ""
        row = self.slot_rows.get(slot)
        desc = self.slot_descs.get(slot, "")
        clear_btn = self.slot_clear_btns.get(slot)
        if row:
            if path and os.path.isfile(path):
                sz = self._format_size(path)
                fname = os.path.basename(path)
                row.set_subtitle(f"<b>{fname}</b> ({sz})")
                if clear_btn:
                    clear_btn.set_visible(True)
            else:
                row.set_subtitle(f"No file selected — {desc}")
                if clear_btn:
                    clear_btn.set_visible(False)

    def append_log(self, text):
        def _append():
            end_iter = self.log_buffer.get_end_iter()
            self.log_buffer.insert(end_iter, text)
            mark = self.log_buffer.create_mark(None, self.log_buffer.get_end_iter(), False)
            self.log_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
            return False
        GLib.idle_add(_append)

    def check_device(self):
        if self.is_flashing:
            return True

        def _detect():
            dev = None
            try:
                res = subprocess.run([ODIN_PATH, "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
                lines = [l.strip() for l in res.stdout.splitlines() if l.strip().startswith("/dev/")]
                if lines:
                    dev = lines[0]
            except Exception:
                pass

            GLib.idle_add(self._update_device_status, dev)

        threading.Thread(target=_detect, daemon=True).start()
        return True

    def _update_device_status(self, dev):
        self.connected_device = dev
        if dev:
            self.dev_icon.set_from_icon_name("phone-symbolic")
            self.dev_row.set_title("Samsung Device Connected")
            self.dev_row.set_subtitle(f"Download Mode ({dev})")
            self.dev_badge.set_label("CONNECTED")
            self.dev_badge.set_css_classes(["device-badge-ok"])
            if not self.is_flashing:
                self.set_stage(1)
        else:
            self.dev_icon.set_from_icon_name("phone-symbolic")
            self.dev_row.set_title("No Samsung Device Detected")
            self.dev_row.set_subtitle("Power off, hold Vol Up+Down & plug USB cable")
            self.dev_badge.set_label("NO DEVICE")
            self.dev_badge.set_css_classes(["device-badge-missing"])
            if not self.is_flashing:
                self.set_stage(0)
        return False

    def clear_slot(self, slot):
        self.update_slot_ui(slot, "")
        if slot == "CSC":
            self.found_csc = None
            self.found_home_csc = None

    def on_browse_slot(self, slot):
        dialog = Gtk.FileDialog()
        dialog.set_title(f"Select {slot} Firmware Archive")
        
        filter_tar = Gtk.FileFilter()
        filter_tar.set_name("Samsung Firmware (*.tar, *.tar.md5)")
        filter_tar.add_pattern("*.tar")
        filter_tar.add_pattern("*.tar.md5")
        
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_tar)
        dialog.set_filters(filters)

        dialog.open(self, None, self._on_slot_file_chosen, slot)

    def _on_slot_file_chosen(self, dialog, result, slot):
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                self.update_slot_ui(slot, path)
                self.append_log(f"Selected {slot}: {os.path.basename(path)}\n")
        except Exception:
            pass

    def on_load_firmware_dialog(self, btn):
        dialog = Gtk.FileDialog()
        dialog.set_title("Open Firmware Zip or Folder")
        
        filter_all = Gtk.FileFilter()
        filter_all.set_name("Firmware Zip or Folder (*.zip)")
        filter_all.add_pattern("*.zip")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_all)
        dialog.set_filters(filters)

        dialog.open(self, None, self._on_firmware_file_or_dir_chosen)

    def _on_firmware_file_or_dir_chosen(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if not file:
                return
            path = file.get_path()
            if os.path.isfile(path) and path.lower().endswith(".zip"):
                self.extract_and_populate_zip(path)
            elif os.path.isdir(path):
                self.populate_from_folder(path)
        except Exception as e:
            self.append_log(f"Error loading selection: {e}\n")

    def extract_and_populate_zip(self, zip_path):
        out_dir = os.path.join(os.path.dirname(zip_path), "extracted_firmware")
        os.makedirs(out_dir, exist_ok=True)

        self.append_log(f"\n[INFO] Extracting firmware zip: {os.path.basename(zip_path)}...\n")
        self.progress_bar.set_text("Extracting Firmware Zip...")
        self.progress_bar.set_fraction(0.1)

        def _unzip_thread():
            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(out_dir)
                GLib.idle_add(self._on_zip_extracted, out_dir)
            except Exception as e:
                GLib.idle_add(self.append_log, f"[ERROR] Failed to extract zip: {e}\n")

        threading.Thread(target=_unzip_thread, daemon=True).start()

    def _on_zip_extracted(self, out_dir):
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("Ready to Flash")
        self.append_log(f"[SUCCESS] Zip extracted to: {out_dir}\n")
        self.populate_from_folder(out_dir)

    def populate_from_folder(self, folder_path):
        self.append_log(f"Scanning directory: {folder_path}\n")
        matches = {"BL": None, "AP": None, "CP": None}
        self.found_csc = None
        self.found_home_csc = None

        for f in glob.glob(os.path.join(folder_path, "*")):
            basename = os.path.basename(f)
            lower = basename.lower()
            if not (lower.endswith(".tar.md5") or lower.endswith(".tar")):
                continue
            if basename.startswith("BL_"):
                matches["BL"] = f
            elif basename.startswith("AP_"):
                matches["AP"] = f
            elif basename.startswith("CP_"):
                matches["CP"] = f
            elif basename.startswith("CSC_"):
                self.found_csc = f
            elif basename.startswith("HOME_CSC_"):
                self.found_home_csc = f

        for slot, path in matches.items():
            if path:
                self.update_slot_ui(slot, path)
                self.append_log(f"  ✔ {slot}: {os.path.basename(path)}\n")

        # Set CSC according to clean flash switch
        self.update_csc_slot_text()

    def on_csc_toggle_changed(self, switch, gparam):
        self.update_csc_slot_text()

    def update_csc_slot_text(self):
        is_clean = self.clean_flash_switch.get_active()
        chosen = self.found_csc if is_clean else (self.found_home_csc or self.found_csc)
        if chosen:
            self.update_slot_ui("CSC", chosen)
            label = "Clean CSC" if is_clean else "HOME_CSC"
            self.append_log(f"  ✔ CSC set to ({label}): {os.path.basename(chosen)}\n")

    def on_start_flash_clicked(self, btn):
        if not self.connected_device:
            self.show_alert(
                "No Device in Download Mode Detected",
                "Cannot start flash because no Samsung phone was detected on USB in Download Mode.\n\n"
                "How to enter Download Mode:\n"
                "1. Turn off your phone.\n"
                "2. Hold Volume Up + Volume Down buttons together.\n"
                "3. Connect the USB cable while holding both buttons.\n"
                "4. When the teal warning screen appears, press Volume Up once.\n\n"
                "Once the top status bar turns green, click Start Flashing."
            )
            return

        cmd = [ODIN_PATH]

        selected_slots = []
        for slot, flag in [("BL", "-b"), ("AP", "-a"), ("CP", "-c"), ("CSC", "-s")]:
            val = self.file_paths.get(slot, "").strip()
            if val and os.path.isfile(val):
                cmd.extend([flag, val])
                selected_slots.append((slot, os.path.basename(val)))

        if not selected_slots:
            self.show_alert("No Firmware Selected", "Please select at least one firmware file (BL, AP, CP, or CSC).")
            return

        cmd.extend(["-d", self.connected_device])

        if self.reboot_switch.get_active():
            cmd.append("--reboot")

        device_str = self.connected_device
        slots_str = "\n".join([f"• <b>{slot}</b>: {name}" for slot, name in selected_slots])
        body_text = (
            f"<b>Target Device:</b> {device_str}\n\n"
            f"<b>Selected Partitions:</b>\n{slots_str}\n\n"
            "⚠️ <b>Important:</b> Ensure the phone has at least 50% battery and do not unplug the USB cable during flashing."
        )

        confirm_dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Confirm Firmware Flash",
            body=body_text
        )
        confirm_dialog.set_body_use_markup(True)
        confirm_dialog.add_response("cancel", "Cancel")
        confirm_dialog.add_response("flash", "Start Flash")
        confirm_dialog.set_response_appearance("flash", Adw.ResponseAppearance.SUGGESTED)

        def _on_confirm(dialog, response):
            if response == "flash":
                self._execute_flash(cmd)

        confirm_dialog.connect("response", _on_confirm)
        confirm_dialog.present()

    def _execute_flash(self, cmd):
        self.is_flashing = True
        self.start_btn.set_sensitive(False)
        self.stop_btn.set_sensitive(True)
        self.set_stage(2)
        self.status_title.set_label("Verifying Firmware Archives (MD5)...")
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("Verifying Archives...")

        self.append_log("\n" + "="*56 + "\n")
        self.append_log(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Launching Odin Flash Engine\n")
        self.append_log(f"Target Device: {self.connected_device}\n")
        self.append_log(f"Command: {' '.join(cmd)}\n")
        self.append_log("="*56 + "\n")

        threading.Thread(target=self._flash_worker, args=(cmd,), daemon=True).start()

    def on_cancel_flash(self, btn):
        if self.flash_process and self.is_flashing:
            self.append_log("\n[WARNING] User requested flash cancellation...\n")
            try:
                self.flash_process.terminate()
            except Exception as e:
                self.append_log(f"Error terminating: {e}\n")

    def _flash_worker(self, cmd):
        try:
            self.flash_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            pct_pattern = re.compile(r'\((\d+)%\)')
            phase = "verifying"
            current_target = "MD5"

            for line in self.flash_process.stdout:
                self.append_log(line)

                if "Check file :" in line:
                    phase = "verifying"
                    parts = line.split("Check file :")
                    if len(parts) > 1:
                        current_target = os.path.basename(parts[1].strip())
                        if current_target.startswith(("AP_", "BL_", "CP_", "CSC_", "HOME_CSC_")):
                            current_target = current_target[:4]
                    GLib.idle_add(self._update_progress, 0.0, f"Verifying integrity: {current_target}...")
                    GLib.idle_add(self.set_stage, 2)
                    GLib.idle_add(self.status_title.set_label, f"Verifying Archive Integrity ({current_target})")

                elif "Setup Connection" in line or "initializeConnection" in line:
                    phase = "connecting"
                    GLib.idle_add(self._update_progress, 0.01, "Connecting to Device...")
                    GLib.idle_add(self.set_stage, 3)
                    GLib.idle_add(self.status_title.set_label, "Connecting to Device Handshake (Thor)")

                elif "Receive PIT Info" in line or "getpit" in line:
                    GLib.idle_add(self._update_progress, 0.03, "Checking Partition Table (PIT)...")
                    GLib.idle_add(self.set_stage, 3)

                elif "Upload Binaries" in line:
                    phase = "flashing"
                    GLib.idle_add(self._update_progress, 0.05, "Writing: Bootloader...")
                    GLib.idle_add(self.set_stage, 4)
                    GLib.idle_add(self.status_title.set_label, "Writing Partitions to Device")

                elif phase == "flashing" and ".lz4" in line:
                    partition_name = line.strip().split()[0] if line.strip() else ""
                    if partition_name:
                        GLib.idle_add(self._update_progress, None, f"Writing partition: {partition_name}")
                        GLib.idle_add(self.status_title.set_label, f"Writing partition: {partition_name}")

                elif "Close Connection" in line:
                    GLib.idle_add(self._update_progress, 1.0, "Finalizing Flash & Rebooting...")
                    GLib.idle_add(self.set_stage, 5)
                    GLib.idle_add(self.status_title.set_label, "Finalizing Flash & Rebooting...")

                matches = pct_pattern.findall(line)
                if matches:
                    val = int(matches[-1])
                    frac = val / 100.0
                    if phase == "verifying":
                        GLib.idle_add(self._update_progress, frac, f"Verifying {current_target}: {val}%")
                    elif phase == "flashing":
                        GLib.idle_add(self._update_progress, frac, f"Flashing to Device: {val}%")

            rc = self.flash_process.wait()
            GLib.idle_add(self._flash_finished, rc)

        except Exception as e:
            self.append_log(f"\nExecution error: {e}\n")
            GLib.idle_add(self._flash_finished, -1)

    def _update_progress(self, frac, text):
        if frac is not None:
            self.progress_bar.set_fraction(frac)
        if text:
            self.progress_bar.set_text(text)
        return False

    def _flash_finished(self, returncode):
        self.is_flashing = False
        self.start_btn.set_sensitive(True)
        self.stop_btn.set_sensitive(False)

        if returncode == 0:
            self.set_stage(5)
            self.status_title.set_label("PASS! Firmware Flashed Successfully")
            self.progress_bar.set_fraction(1.0)
            self.progress_bar.set_text("PASS! Flashing Complete")
            self.append_log("\n[SUCCESS] Flashing complete! (PASS) Device rebooting into Android.\n")
            self.show_alert("Flashing Successful! 🎉", "Firmware was flashed successfully (PASS!).\nThe device is rebooting into Android.")
        else:
            self.set_stage(1)
            self.status_title.set_label("Flashing Failed")
            self.progress_bar.set_text(f"FAIL (Code {returncode})")
            err_msg = f"Odin engine reported an error (Exit code: {returncode})."
            if returncode == 6:
                err_msg += "\n\nTip: Check if the device is securely in Download Mode and verify cable connection."
            self.append_log(f"\n[FAIL] Flashing failed with exit code {returncode}.\n")
            self.show_alert("Flashing Failed", err_msg)

        return False

    def on_copy_log(self, btn):
        bounds = self.log_buffer.get_bounds()
        text = self.log_buffer.get_text(bounds[0], bounds[1], False)
        clipboard = self.get_display().get_clipboard()
        clipboard.set(text)
        self.progress_bar.set_text("Log Copied to Clipboard!")

    def on_save_log(self, btn):
        bounds = self.log_buffer.get_bounds()
        text = self.log_buffer.get_text(bounds[0], bounds[1], False)
        filename = f"odin_flash_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        save_path = os.path.join(os.path.expanduser("~"), filename)
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(text)
            self.show_alert("Log Saved", f"Log successfully written to:\n{save_path}")
        except Exception as e:
            self.show_alert("Save Error", f"Could not save log: {e}")

    def on_clear_log(self, btn):
        self.log_buffer.set_text("")

    def show_alert(self, title, msg):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=title,
            body=msg
        )
        dialog.add_response("ok", "OK")
        dialog.present()


def main():
    Adw.init()
    if os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        try:
            app = OdinApp()
            return app.run(sys.argv)
        except Exception:
            pass

    loop = GLib.MainLoop()
    win = OdinWindow()
    win.connect("close-request", lambda w: (loop.quit(), False)[1])
    win.present()
    loop.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
