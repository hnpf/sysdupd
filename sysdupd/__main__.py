import gi
import os
import sys
import threading
import subprocess
import json
import datetime
import platform

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib
from .distro_utils import detect_distro_and_package_manager, check_for_updates, apply_updates, get_system_specs

class SysdupdApplication(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id="com.virex.Sysdupd", **kwargs)
        self.config_dir = os.path.expanduser("~/.config/sysdupd")
        self.config_path = os.path.join(self.config_dir, "config.json")
        self.history_path = os.path.join(self.config_dir, "history.log")
        self.load_config()
        self.connect("activate", self.on_activate)

    def load_config(self):
        defaults = {
            "exclude": [], 
            "check_flatpaks": True, 
            "notifications": True,
            "terminal": "kitty",
            "auto_update": False
        }
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                self.config = {**defaults, **json.load(f)}
        else:
            self.config = defaults
            os.makedirs(self.config_dir, exist_ok=True)
            self.save_config()

    def save_config(self):
        with open(self.config_path, "w") as f:
            json.dump(self.config, f)
            
    def log_history(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.history_path, "a") as f:
            f.write(f"[{timestamp}] {message}\n")

    def on_activate(self, app):
        self.win = self.props.active_window
        if not self.win:
            self.win = Adw.ApplicationWindow(application=app)
            self.win.set_default_size(950, 700)
            self.win.set_title("Sysdupd")
            self.win.set_icon_name("com.virex.sysdupd-symbolic")

            self.toast_overlay = Adw.ToastOverlay()
            self.win.set_content(self.toast_overlay)
            split_view = Adw.NavigationSplitView()
            self.toast_overlay.set_child(split_view)

            sidebar_toolbar = Adw.ToolbarView()
            sidebar_header = Adw.HeaderBar()
            sidebar_header.set_show_title(False)
            sidebar_toolbar.add_top_bar(sidebar_header)

            nav_list = Gtk.ListBox()
            nav_list.add_css_class("navigation-sidebar")
            self.rows = {
                "home": Adw.ActionRow(title="Home", icon_name="go-home-symbolic"),
                "updates": Adw.ActionRow(title="Updates", icon_name="software-update-available-symbolic"),
                "settings": Adw.ActionRow(title="Settings", icon_name="applications-system-symbolic")
            }
            for row in self.rows.values(): nav_list.append(row)
            sidebar_toolbar.set_content(nav_list)
            split_view.set_sidebar(Adw.NavigationPage.new(sidebar_toolbar, "Navigation"))

            content_toolbar = Adw.ToolbarView()
            self.content_header = Adw.HeaderBar()
            self.refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
            self.refresh_btn.connect("clicked", lambda b: self._refresh_updates())
            self.content_header.pack_end(self.refresh_btn)
            content_toolbar.add_top_bar(self.content_header)

            self.content_stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
            content_toolbar.set_content(self.content_stack)
            split_view.set_content(Adw.NavigationPage.new(content_toolbar, "Content"))
            
            nav_list.connect("row-selected", lambda l, r: self._switch_view(r))

            self.distro_info = detect_distro_and_package_manager()
            self.specs = get_system_specs()

            self._build_home()
            self._build_updates()
            self._build_settings()

            self.content_stack.set_visible_child_name("home_view")
            self._update_service_ui()
            self._refresh_updates()

        self.win.present()

    def _build_home(self):
        page = Adw.PreferencesPage()
        grp = Adw.PreferencesGroup()
        user = self.specs.get('user', 'User').capitalize()
        distro_name = self.distro_info[0] if self.distro_info else platform.system()
        status = Adw.StatusPage(title=f"Welcome, {user}", icon_name="computer-symbolic")
        status.set_description(f"{distro_name} Workstation")
        grp.add(status)
        page.add(grp)
        specs = Adw.PreferencesGroup(title="Hardware Info")
        specs.add(Adw.ActionRow(title="Processor", subtitle=self.specs.get("cpu", "Unknown")))
        specs.add(Adw.ActionRow(title="Graphics", subtitle=self.specs.get("gpu", "Unknown")))
        specs.add(Adw.ActionRow(title="Memory", subtitle=self.specs.get("ram", "Unknown")))
        page.add(specs)
        self.content_stack.add_named(page, "home_view")

    def _build_updates(self):
        page = Adw.PreferencesPage()
        self.upd_group = Adw.PreferencesGroup(title="System Status")
        self.empty_status = Adw.StatusPage(title="System Up To Date", icon_name="weather-clear-symbolic")
        self.empty_status.set_description("No updates found.")
        self.big_check_btn = Gtk.Button(label="Check for Updates", halign=Gtk.Align.CENTER)
        self.big_check_btn.add_css_class("pill")
        self.big_check_btn.connect("clicked", lambda b: self._refresh_updates())
        self.empty_status.set_child(self.big_check_btn)
        self.updates_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.updates_list.add_css_class("boxed-list")
        self.updates_list.set_visible(False)
        self.upd_group.add(self.empty_status)
        self.upd_group.add(self.updates_list)
        page.add(self.upd_group)
        self.action_group = Adw.PreferencesGroup(title="Actions")
        self.action_group.set_visible(False)
        row = Adw.ActionRow(title="Execute Update")
        self.apply_btn = Gtk.Button(label="Apply", valign=Gtk.Align.CENTER)
        self.apply_btn.add_css_class("suggested-action")
        self.apply_btn.connect("clicked", self._on_apply_clicked)
        row.add_suffix(self.apply_btn)
        self.action_group.add(row)
        page.add(self.action_group)
        self.content_stack.add_named(page, "updates_view")

    def _build_settings(self):
        page = Adw.PreferencesPage()
        auto = Adw.PreferencesGroup(title="Automation")
        self.inst_btn = Gtk.Button(label="...", valign=Gtk.Align.CENTER)
        svc_row = Adw.ActionRow(title="Background Service", subtitle="Systemd timer integration")
        svc_row.add_suffix(self.inst_btn)
        auto.add(svc_row)
        notif_sw = Adw.SwitchRow(title="Notifications", subtitle="Show desktop alerts")
        notif_sw.set_active(self.config["notifications"])
        notif_sw.connect("notify::active", lambda r, _: self._save_setting("notifications", r.get_active()))
        test_btn = Gtk.Button(icon_name="mail-send-symbolic", valign=Gtk.Align.CENTER)
        test_btn.add_css_class("flat")
        test_btn.connect("clicked", self._test_notification)
        notif_sw.add_suffix(test_btn)
        auto.add(notif_sw)
        # Danger toggle
        auto_sw = Adw.SwitchRow(title="Auto-Apply", subtitle="Apply updates in background (Risky!)")
        auto_sw.set_active(self.config.get("auto_update", False))
        auto_sw.connect("notify::active", lambda r, _: self._save_setting("auto_update", r.get_active()))
        auto.add(auto_sw)
        page.add(auto)

        conf = Adw.PreferencesGroup(title="Configuration")
        term_row = Adw.EntryRow(title="Terminal Emulator")
        term_row.set_text(self.config["terminal"])
        term_row.connect("notify::text", lambda r, _: self._save_setting("terminal", r.get_text()))
        conf.add(term_row)
        excl_row = Adw.EntryRow(title="Ignored Packages")
        excl_row.set_text(", ".join(self.config["exclude"]))
        excl_row.connect("notify::text", self._update_excl)
        conf.add(excl_row)
        # Desktop Entry
        desk_row = Adw.ActionRow(title="Desktop Integration", subtitle="Create .desktop entry")
        desk_btn = Gtk.Button(label="Create", valign=Gtk.Align.CENTER)
        desk_btn.connect("clicked", self._create_desktop_entry)
        desk_row.add_suffix(desk_btn)
        conf.add(desk_row)
        page.add(conf)

        hist = Adw.PreferencesGroup(title="Logs")
        hist_row = Adw.ActionRow(title="Update History")
        hist_btn = Gtk.Button(icon_name="document-open-symbolic", valign=Gtk.Align.CENTER)
        hist_btn.connect("clicked", self._show_history)
        hist_row.add_suffix(hist_btn)
        hist.add(hist_row)
        page.add(hist)
        self.content_stack.add_named(page, "settings_view")

    def _create_desktop_entry(self, btn):
        entry_path = os.path.expanduser("~/.local/share/applications/com.virex.sysdupd.desktop")
        script_path = os.path.abspath(sys.argv[0])
        content = f"[Desktop Entry]\nName=Sysdupd\nExec={sys.executable} {script_path}\nIcon=software-update-available-symbolic\nType=Application\nCategories=System;Settings;"
        os.makedirs(os.path.dirname(entry_path), exist_ok=True)
        with open(entry_path, "w") as f: f.write(content)
        self.toast_overlay.add_toast(Adw.Toast.new("Created! check your app menu 😋"))

    def _save_setting(self, key, value):
        self.config[key] = value
        self.save_config()

    def _update_excl(self, row, _):
        text = row.get_text()
        self.config["exclude"] = [x.strip() for x in text.split(",") if x.strip()]
        self.save_config()

    def _test_notification(self, btn):
        subprocess.run(["notify-send", "Sysdupd", "This is a test notification! ✌️🥹"])

    def _switch_view(self, row):
        for name, r in self.rows.items():
            if r == row:
                self.content_stack.set_visible_child_name(f"{name}_view")
                visible = (name == "updates" and self.updates_list.get_visible())
                self.refresh_btn.set_visible(visible)

    def _refresh_updates(self):
        self.refresh_btn.set_sensitive(False)
        self.big_check_btn.set_sensitive(False)
        self.empty_status.set_title("Checking...")
        self.empty_status.set_child(None)
        def run():
            upd = check_for_updates(self.distro_info)
            GLib.idle_add(self._show_upd, upd)
        threading.Thread(target=run, daemon=True).start()

    def _show_upd(self, upd):
        self.refresh_btn.set_sensitive(True)
        self.big_check_btn.set_sensitive(True)
        while c := self.updates_list.get_first_child(): self.updates_list.remove(c)
        filtered = [p for p in upd if p not in self.config["exclude"]]
        if filtered:
            self.empty_status.set_visible(False)
            self.updates_list.set_visible(True)
            self.action_group.set_visible(True)
            self.refresh_btn.set_visible(True)
            for line in filtered:
                parts = line.split()
                row = Adw.ActionRow(title=parts[0], subtitle=" ".join(parts[1:]))
                row.set_icon_name("package-x-generic-symbolic")
                self.updates_list.append(row)
        else:
            self.empty_status.set_title("System Up To Date")
            self.empty_status.set_child(self.big_check_btn)
            self.empty_status.set_visible(True)
            self.updates_list.set_visible(False)
            self.action_group.set_visible(False)
            self.refresh_btn.set_visible(False)

    def _on_apply_clicked(self, btn):
        self.apply_btn.set_sensitive(False)
        self.empty_status.set_visible(True)
        self.empty_status.set_title("Installing...")
        self.updates_list.set_visible(False)
        self.action_group.set_visible(False)
        def run():
            success, msg = apply_updates(self.distro_info)
            self.log_history(f"Update run: {'Success' if success else 'Failed'}")
            GLib.idle_add(self._done, success)
        threading.Thread(target=run, daemon=True).start()

    def _done(self, success):
        self._refresh_updates()
        self.toast_overlay.add_toast(Adw.Toast.new("Finished! 😋" if success else "Failed! 😭"))

    def _show_history(self, btn):
        win = Adw.Window(title="History", modal=True, transient_for=self.win)
        win.set_default_size(600, 450)
        tb_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        tb_view.add_top_bar(header)
        page = Adw.PreferencesPage()
        grp = Adw.PreferencesGroup()
        if os.path.exists(self.history_path):
            with open(self.history_path, "r") as f:
                logs = f.readlines()
            for log in reversed(logs[-20:]): grp.add(Adw.ActionRow(title=log.strip()))
        else:
            grp.add(Adw.ActionRow(title="No history found."))
        page.add(grp)
        tb_view.set_content(page)
        win.set_content(tb_view)
        win.present()

    def _update_service_ui(self):
        res = subprocess.run(["systemctl", "--user", "is-enabled", "sysdupd.timer"], capture_output=True, text=True)
        is_enabled = res.stdout.strip() == "enabled"
        self.inst_btn.set_label("Remove" if is_enabled else "Install")
        self.inst_btn.set_css_classes(["destructive-action"] if is_enabled else ["suggested-action"])
        try: self.inst_btn.disconnect_by_func(self._install_service); self.inst_btn.disconnect_by_func(self._remove_service)
        except: pass
        self.inst_btn.connect("clicked", self._remove_service if is_enabled else self._install_service)

    def _install_service(self, btn):
        user_config = os.path.expanduser("~/.config/systemd/user")
        os.makedirs(user_config, exist_ok=True)
        script = os.path.abspath(sys.argv[0])
        with open(os.path.join(user_config, "sysdupd.service"), "w") as f:
            f.write(f"[Unit]\nDescription=Sysdupd\n\n[Service]\nExecStart={sys.executable} {script} --service\nType=oneshot")
        with open(os.path.join(user_config, "sysdupd.timer"), "w") as f:
            f.write("[Unit]\nDescription=Daily Sysdupd\n\n[Timer]\nOnCalendar=daily\nPersistent=true\n\n[Install]\nWantedBy=timers.target")
        subprocess.run(["systemctl", "--user", "daemon-reload"])
        subprocess.run(["systemctl", "--user", "enable", "--now", "sysdupd.timer"])
        self._update_service_ui()
        self.toast_overlay.add_toast(Adw.Toast.new("Service active! ✌️🥹"))

    def _remove_service(self, btn):
        subprocess.run(["systemctl", "--user", "disable", "--now", "sysdupd.timer"])
        self._update_service_ui()
        self.toast_overlay.add_toast(Adw.Toast.new("Service disabled"))

def main():
    if "--service" in sys.argv:
        config_path = os.path.expanduser("~/.config/sysdupd/config.json")
        try:
            with open(config_path) as f: cfg = json.load(f)
        except: cfg = {"notifications": True, "auto_update": False}
        distro_info = detect_distro_and_package_manager()
        upd = check_for_updates(distro_info)
        if upd:
            if cfg.get("auto_update", False):
                apply_updates(distro_info)
                if cfg.get("notifications", True):
                    subprocess.run(["notify-send", "Sysdupd", "Background updates applied!"])
            elif cfg.get("notifications", True):
                subprocess.run(["notify-send", "Sysdupd", f"{len(upd)} updates ready!"])
    else:
        SysdupdApplication().run(sys.argv)

if __name__ == "__main__": main()