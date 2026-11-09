#!/usr/bin/env python3
"""Corpse OS first-run setup and GTK theme chooser.

Runs as the logged-in desktop user. It never invokes a shell, sudo, or arbitrary
model-provided command. Ollama downloads require an explicit button click.
"""
import json
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

APP_NAME = "Corpse OS Setup"
CONFIG_DIR = Path.home() / ".config" / "corpse-os"
CONFIG_PATH = CONFIG_DIR / "setup.json"
MARKER_PATH = CONFIG_DIR / "first-run-complete"
MODEL_DIR = Path.home() / "Models"

CATALOG = {
    "qwen3:4b": {
        "title": "Qwen 3 · 4B · general assistant",
        "use": "Everyday questions, summaries and light coding; balanced first local model.",
        "disk_gb": 2.5,
        "ram_gb": 6,
    },
    "qwen2.5-coder:3b": {
        "title": "Qwen 2.5 Coder · 3B · coding",
        "use": "Code explanations and small programming tasks; lighter than the 7B option.",
        "disk_gb": 1.9,
        "ram_gb": 5,
    },
    "qwen2.5-coder:7b": {
        "title": "Qwen 2.5 Coder · 7B · stronger coding",
        "use": "More capable code generation/review; needs more RAM and storage.",
        "disk_gb": 4.7,
        "ram_gb": 10,
    },
}
THEMES = ("Material-inspired", "macOS-inspired")

CSS = {
    "Material-inspired": """/* Corpse OS Material-inspired GTK3 palette. */
@define-color corpse_bg #f4f3f8;
@define-color corpse_surface #ffffff;
@define-color corpse_text #20212a;
@define-color corpse_accent #6750a4;
@define-color corpse_accent_text #ffffff;
window, .background { background-color: @corpse_bg; color: @corpse_text; }
headerbar, .titlebar { background-color: @corpse_surface; color: @corpse_text; border: 0; box-shadow: 0 1px 4px alpha(#171526, 0.14); }
button { background-image: none; background-color: #e9e4f4; color: @corpse_text; border: 0; border-radius: 18px; padding: 8px 14px; }
button.suggested-action { background-color: @corpse_accent; color: @corpse_accent_text; }
entry, textview, combobox button { background-color: @corpse_surface; color: @corpse_text; border-radius: 10px; }
""",
    "macOS-inspired": """/* Generic macOS-inspired GTK3 styling; no Apple artwork or branding. */
@define-color corpse_bg #eceef2;
@define-color corpse_surface #f8f9fb;
@define-color corpse_text #20232a;
@define-color corpse_accent #4386d9;
@define-color corpse_accent_text #ffffff;
window, .background { background-color: @corpse_bg; color: @corpse_text; }
headerbar, .titlebar { background-color: @corpse_surface; color: @corpse_text; border: 0; box-shadow: 0 1px 5px alpha(#20232a, 0.12); }
button { background-image: none; background-color: #e5e8ee; color: @corpse_text; border: 1px solid #d4d8e0; border-radius: 7px; padding: 7px 12px; }
button.suggested-action { background-color: @corpse_accent; color: @corpse_accent_text; border-color: @corpse_accent; }
entry, textview, combobox button { background-color: @corpse_surface; color: @corpse_text; border-radius: 6px; }
""",
}


def load_config():
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return {}


def save_config(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temp = CONFIG_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temp, 0o600)
    temp.replace(CONFIG_PATH)


def system_memory_gb():
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) / 1024 / 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0.0


def model_disk_gb():
    try:
        return shutil.disk_usage(Path.home()).free / (1024 ** 3)
    except OSError:
        return 0.0


def installed_ollama_model(tag):
    if not shutil.which("ollama"):
        return False
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True,
                                timeout=5, check=False)
        return result.returncode == 0 and any(line.split() and line.split()[0] == tag
                                               for line in result.stdout.splitlines()[1:])
    except (OSError, subprocess.TimeoutExpired):
        return False


class Setup(Gtk.Window):
    def __init__(self, settings_only=False):
        super().__init__(title=APP_NAME)
        self.settings_only = settings_only
        self.set_default_size(760, 720)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(22)
        self.config = load_config()
        self.no_model_selected = False
        self._animation_source = None

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.add(outer)

        self.hero = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        outer.pack_start(self.hero, False, False, 0)
        self.mark = Gtk.Label(label="✦")
        self.mark.set_markup('<span size="24000" foreground="#70a884">✦</span>')
        self.hero.pack_start(self.mark, False, False, 0)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.hero.pack_start(titles, True, True, 0)
        title = Gtk.Label()
        title.set_markup("<span size='xx-large' weight='bold'>Welcome to Corpse OS</span>")
        title.set_xalign(0)
        titles.pack_start(title, False, False, 0)
        subtitle = Gtk.Label(label="A calm first-run setup. Choose what to install; nothing downloads until you ask.")
        subtitle.set_xalign(0)
        subtitle.set_line_wrap(True)
        titles.pack_start(subtitle, False, False, 0)

        model_frame = Gtk.Frame(label="  Local AI model  ")
        outer.pack_start(model_frame, False, False, 0)
        model_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        model_box.set_border_width(12)
        model_frame.add(model_box)

        intro = Gtk.Label(label="Pick a starter profile, or skip and set it up later. RAM and free disk are checked on this computer.")
        intro.set_xalign(0)
        intro.set_line_wrap(True)
        model_box.pack_start(intro, False, False, 0)

        self.model_combo = Gtk.ComboBoxText()
        for tag, meta in CATALOG.items():
            self.model_combo.append(tag, meta["title"])
        saved_tag = self.config.get("preferred_model", "qwen3:4b")
        self.model_combo.set_active_id(saved_tag if saved_tag in CATALOG else "qwen3:4b")
        model_box.pack_start(self.model_combo, False, False, 0)
        self.model_detail = Gtk.Label()
        self.model_detail.set_xalign(0)
        self.model_detail.set_line_wrap(True)
        model_box.pack_start(self.model_detail, False, False, 0)
        self.compat_label = Gtk.Label()
        self.compat_label.set_xalign(0)
        self.compat_label.set_line_wrap(True)
        model_box.pack_start(self.compat_label, False, False, 0)
        self.model_combo.connect("changed", self.on_model_change)

        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        model_box.pack_start(action_row, False, False, 0)
        self.install_button = Gtk.Button(label="Install selected model with Ollama")
        self.install_button.get_style_context().add_class("suggested-action")
        self.install_button.connect("clicked", self.install_model)
        action_row.pack_start(self.install_button, False, False, 0)
        self.skip_model = Gtk.Button(label="Use without a model for now")
        self.skip_model.connect("clicked", lambda *_: self.select_model(None))
        action_row.pack_start(self.skip_model, False, False, 0)
        self.refresh_model()

        llama_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        model_box.pack_start(llama_box, False, False, 0)
        self.gguf_label = Gtk.Label(label="llama.cpp: no GGUF model selected")
        self.gguf_label.set_xalign(0)
        self.gguf_label.set_line_wrap(True)
        llama_box.pack_start(self.gguf_label, True, True, 0)
        self.gguf_button = Gtk.Button(label="Choose existing GGUF")
        self.gguf_button.connect("clicked", self.choose_gguf)
        llama_box.pack_start(self.gguf_button, False, False, 0)
        if self.config.get("llama_cpp_model"):
            self.gguf_label.set_text("llama.cpp model: " + self.config["llama_cpp_model"])

        cloud_frame = Gtk.Frame(label="  Optional cloud AI  ")
        outer.pack_start(cloud_frame, False, False, 0)
        cloud_text = Gtk.Label(label=("Gemini is not connected in this prototype. A real Google OAuth client, consent screen, "
            "secure token storage, and data-sharing controls must be implemented before sign-in is offered. "
            "This screen never asks for your Google password or API key."))
        cloud_text.set_margin_start(12)
        cloud_text.set_margin_end(12)
        cloud_text.set_margin_top(12)
        cloud_text.set_margin_bottom(12)
        cloud_text.set_xalign(0)
        cloud_text.set_line_wrap(True)
        cloud_frame.add(cloud_text)

        theme_frame = Gtk.Frame(label="  Desktop appearance  ")
        outer.pack_start(theme_frame, False, False, 0)
        theme_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        theme_box.set_border_width(12)
        theme_frame.add(theme_box)
        theme_text = Gtk.Label(label="Choose one of the two bundled looks. These are original GTK styling presets, not macOS or an official Material UI package; they affect GTK 3 apps and XFCE elements that use GTK 3, not every third-party toolkit.")
        theme_text.set_xalign(0)
        theme_text.set_line_wrap(True)
        theme_box.pack_start(theme_text, False, False, 0)
        self.theme_combo = Gtk.ComboBoxText()
        for name in THEMES:
            self.theme_combo.append(name, name)
        saved_theme = self.config.get("theme", THEMES[0])
        self.theme_combo.set_active_id(saved_theme if saved_theme in THEMES else THEMES[0])
        theme_box.pack_start(self.theme_combo, False, False, 0)
        self.theme_combo.connect("changed", self.apply_theme)

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        outer.pack_end(bottom, False, False, 0)
        self.status = Gtk.Label(label="")
        self.status.set_xalign(0)
        self.status.set_line_wrap(True)
        bottom.pack_start(self.status, True, True, 0)
        self.done_button = Gtk.Button(label="Save choices and continue")
        self.done_button.get_style_context().add_class("suggested-action")
        self.done_button.connect("clicked", self.finish)
        bottom.pack_end(self.done_button, False, False, 0)

        if not settings_only:
            self.connect("realize", self.start_welcome_animation)
        self.connect("destroy", Gtk.main_quit)
        self.apply_theme()
        self.show_all()

    def on_model_change(self, *_):
        self.no_model_selected = False
        self.refresh_model()

    def refresh_model(self, *_):
        tag = self.model_combo.get_active_id()
        meta = CATALOG.get(tag)
        if not meta:
            return
        self.model_detail.set_text(f"{meta['use']} Approx. download: {meta['disk_gb']:.1f} GB; suggested RAM: {meta['ram_gb']} GB.")
        available_ram = system_memory_gb()
        free_disk = model_disk_gb()
        runtime = shutil.which("ollama") is not None
        notes = [f"Detected RAM: {available_ram:.1f} GB; free home-folder disk: {free_disk:.1f} GB. This is only a rough preflight: Ollama may store models on a different service volume, so verify that destination too."]
        machine = os.uname().machine
        notes.append(f"Architecture: {machine}; CPU/GPU throughput is not benchmarked (CPU-only inference may be slow).")
        architecture_ok = machine in ("x86_64", "aarch64", "arm64")
        ram_ok = available_ram >= meta["ram_gb"]
        disk_ok = free_disk >= meta["disk_gb"] * 1.25
        if not architecture_ok:
            notes.append("Unsupported architecture for these model profiles; installation disabled.")
        if not ram_ok:
            notes.append("Below the approximate suggested RAM; installation disabled for this profile. Choose a smaller model or skip.")
        else:
            notes.append("RAM meets this profile's approximate recommendation.")
        if not disk_ok:
            notes.append("Not enough safe free-space headroom for the estimated download; installation disabled.")
        if not runtime:
            notes.append("Ollama runtime is not included/installed in this image yet; model installation is unavailable here.")
        elif installed_ollama_model(tag):
            notes.append("This model appears installed in Ollama already.")
        self.compat_label.set_text(" ".join(notes))
        self.install_button.set_sensitive(bool(runtime and architecture_ok and ram_ok and disk_ok))
        if not runtime:
            self.install_button.set_tooltip_text("Install an OS-packaged Ollama runtime first; this prototype does not run an unverified root installer.")

    def select_model(self, tag):
        if tag is None:
            self.no_model_selected = True
            self.config.pop("preferred_model", None)
            self.status.set_text("No default model selected; you can choose one later.")
        else:
            self.no_model_selected = False
            self.config["preferred_model"] = tag
            self.status.set_text(f"Saved {tag} as your choice. It is not installed until you click Install.")
        save_config(self.config)

    def install_model(self, *_):
        tag = self.model_combo.get_active_id()
        if tag not in CATALOG:
            return
        if shutil.which("ollama") is None:
            self.status.set_text("Ollama isn't installed. Use a trusted OS package or wait for the runtime to be bundled; no privileged installer was run.")
            return
        meta = CATALOG[tag]
        machine = os.uname().machine
        if (machine not in ("x86_64", "aarch64", "arm64")
                or system_memory_gb() < meta["ram_gb"]
                or model_disk_gb() < meta["disk_gb"] * 1.25):
            self.status.set_text("Compatibility check failed. Choose a smaller model or free RAM/disk space before downloading.")
            return
        self.install_button.set_sensitive(False)
        self.status.set_text(f"Downloading {tag} via Ollama… This can use several gigabytes; you chose Install.")
        def worker():
            try:
                process = subprocess.Popen(["ollama", "pull", tag], stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT, text=True)
                for line in process.stdout:
                    GLib.idle_add(self.status.set_text, line.strip()[:300])
                code = process.wait()
                if code == 0:
                    self.config["ollama_model"] = tag
                    self.config["preferred_model"] = tag
                    save_config(self.config)
                    GLib.idle_add(self.status.set_text, f"Ollama reports {tag} downloaded. Verify it works in your local runtime before trusting its output.")
                else:
                    GLib.idle_add(self.status.set_text, f"Ollama download stopped with exit code {code}; no model was marked ready.")
            except (OSError, subprocess.TimeoutExpired) as exc:
                GLib.idle_add(self.status.set_text, f"Could not run Ollama: {exc}")
            GLib.idle_add(self.install_button.set_sensitive, True)
            GLib.idle_add(self.refresh_model)
        threading.Thread(target=worker, daemon=True).start()

    def choose_gguf(self, *_):
        dialog = Gtk.FileChooserDialog(title="Select a local GGUF file", parent=self,
            action=Gtk.FileChooserAction.OPEN,
            buttons=("Cancel", Gtk.ResponseType.CANCEL, "Choose", Gtk.ResponseType.ACCEPT))
        filt = Gtk.FileFilter()
        filt.set_name("GGUF model files")
        filt.add_pattern("*.gguf")
        dialog.add_filter(filt)
        response = dialog.run()
        filename = dialog.get_filename() if response == Gtk.ResponseType.ACCEPT else None
        dialog.destroy()
        if filename:
            path = Path(filename).resolve()
            if path.suffix.lower() != ".gguf" or not path.is_file():
                self.status.set_text("Choose an existing .gguf file only.")
                return
            self.config["llama_cpp_model"] = str(path)
            save_config(self.config)
            self.gguf_label.set_text("llama.cpp model selected: " + path.name + " (runtime still required)")
            self.status.set_text("Saved the local model path; no model file was copied or executed.")

    def apply_theme(self, *_):
        theme = self.theme_combo.get_active_id()
        if theme not in THEMES:
            return
        try:
            gtk_dir = Path.home() / ".config" / "gtk-3.0"
            gtk_dir.mkdir(parents=True, exist_ok=True)
            css_path = gtk_dir / "gtk.css"
            begin, end = "/* CORPSE OS PRESET BEGIN */", "/* CORPSE OS PRESET END */"
            existing = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
            if begin in existing and end in existing:
                prefix = existing.split(begin, 1)[0]
                suffix = existing.split(end, 1)[1]
                existing = prefix.rstrip() + "\n" + suffix.lstrip()
            block = begin + "\n/* Corpse OS theme preset: " + theme + " */\n" + CSS[theme] + "\n" + end
            css_path.write_text(existing.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
            self.config["theme"] = theme
            save_config(self.config)
            self.status.set_text(f"Applied {theme} styling to GTK 3 apps. Restart apps for full coverage.")
            self.queue_draw()
        except OSError as exc:
            self.status.set_text(f"Could not apply theme: {exc}")

    def start_welcome_animation(self, *_):
        # A brief optional fade; no looping motion and no impact on setup functionality.
        gtk_settings = Gtk.Settings.get_default()
        if gtk_settings and not gtk_settings.get_property("gtk-enable-animations"):
            return
        self.hero.set_opacity(0.15)
        state = {"step": 0}
        def tick():
            state["step"] += 1
            self.hero.set_opacity(min(1.0, 0.15 + state["step"] / 16.0))
            if state["step"] >= 16:
                self._animation_source = None
                return GLib.SOURCE_REMOVE
            return GLib.SOURCE_CONTINUE
        self._animation_source = GLib.timeout_add(35, tick)

    def finish(self, *_):
        theme = self.theme_combo.get_active_id()
        if theme in THEMES:
            self.config["theme"] = theme
        selected = self.model_combo.get_active_id()
        if self.no_model_selected:
            self.config.pop("preferred_model", None)
        elif selected in CATALOG:
            self.config["preferred_model"] = selected
        try:
            save_config(self.config)
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            MARKER_PATH.touch(mode=0o600, exist_ok=True)
            self.status.set_text("Choices saved. You can reopen Corpse OS Setup from the Applications menu.")
            self.done_button.set_label("Done")
            self.done_button.set_sensitive(False)
        except OSError as exc:
            self.status.set_text(f"Could not save setup: {exc}")


def main():
    settings_only = "--settings" in os.sys.argv
    if not settings_only and MARKER_PATH.exists():
        return
    Gtk.init(None)
    Setup(settings_only)
    Gtk.main()


if __name__ == "__main__":
    main()
