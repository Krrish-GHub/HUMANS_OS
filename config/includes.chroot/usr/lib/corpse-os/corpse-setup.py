#!/usr/bin/env python3
"""H.U.M.A.N.S first-run setup and GTK theme chooser.

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

APP_NAME = "H.U.M.A.N.S Setup"
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
THEMES = ("H.U.M.A.N.S Rose", "Material-inspired", "macOS-inspired")

CSS = {
    "H.U.M.A.N.S Rose": """/* H.U.M.A.N.S default: dark warm surfaces with clear rose-red accents. */
@define-color corpse_bg #171115;
@define-color corpse_surface #241a20;
@define-color corpse_text #f6eef1;
@define-color corpse_accent #e66d82;
@define-color corpse_accent_text #241016;
window, .background { background-color: @corpse_bg; color: @corpse_text; }
headerbar, .titlebar { background-color: @corpse_surface; color: @corpse_text; border: 0; box-shadow: 0 1px 5px alpha(#080608, 0.4); }
button { background-image: none; background-color: #35262d; color: @corpse_text; border: 1px solid #57404a; border-radius: 10px; padding: 8px 14px; }
button:hover { background-color: #49323b; border-color: #9d5263; }
button.suggested-action { background-color: @corpse_accent; color: @corpse_accent_text; border-color: @corpse_accent; }
entry, textview, combobox button { background-color: @corpse_surface; color: @corpse_text; border: 1px solid #57404a; border-radius: 9px; }
*:selected, selection { background-color: #a94359; color: #fff5f6; }
checkbutton check, radiobutton radio { border-color: #9b7480; }
checkbutton check:checked, radiobutton radio:checked { background-color: @corpse_accent; }
progressbar progress, scale highlight { background-color: @corpse_accent; }
""",
    "Material-inspired": """/* H.U.M.A.N.S Material-inspired GTK3 palette. */
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
        self.pages = Gtk.Stack()
        self.pages.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.pages.set_transition_duration(160)
        outer.pack_start(self.pages, True, True, 0)

        # First-run opens on an OS information page; the existing local-model/theme
        # setup remains a separate next step and is also available directly in settings.
        self.info_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.info_page.set_border_width(24)
        self.welcome_hero = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.info_page.pack_start(self.welcome_hero, False, False, 0)
        self.info_mark = Gtk.Label(label="✦")
        self.info_mark.set_markup('<span size="32000" foreground="#e66d82">✦</span>')
        self.welcome_hero.pack_start(self.info_mark, False, False, 0)
        welcome_titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.welcome_hero.pack_start(welcome_titles, True, True, 0)
        welcome_title = Gtk.Label()
        welcome_title.set_markup("<span size='xx-large' weight='bold'>Welcome to H.U.M.A.N.S</span>")
        welcome_title.set_xalign(0)
        welcome_titles.pack_start(welcome_title, False, False, 0)
        welcome_subtitle = Gtk.Label(label="A Debian-based live desktop prototype for x86-64 PCs.")
        welcome_subtitle.set_xalign(0)
        welcome_subtitle.set_line_wrap(True)
        welcome_titles.pack_start(welcome_subtitle, False, False, 0)

        info_frame = Gtk.Frame(label="  About this system  ")
        self.info_page.pack_start(info_frame, False, False, 0)
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        info_box.set_border_width(16)
        info_frame.add(info_box)
        info_copy = (
            "H.U.M.A.N.S is an early Linux desktop project, designed around a live USB session "
            "and carefully scoped local AI tools.\n\n"
            "Booting this session from USB or ISO does not install it onto your internal drive.\n\n"
            "Next, you can review optional local-model and desktop appearance settings. A model "
            "download starts only if you choose Install; you can skip it and continue without a model."
        )
        info_text = Gtk.Label(label=info_copy)
        info_text.set_xalign(0)
        info_text.set_yalign(0)
        info_text.set_line_wrap(True)
        info_text.set_max_width_chars(76)
        info_box.pack_start(info_text, False, False, 0)
        info_note = Gtk.Label(label="Prototype status: some local AI runtime and agent features are still under development.")
        info_note.set_xalign(0)
        info_note.set_line_wrap(True)
        info_note.get_style_context().add_class("dim-label")
        info_box.pack_start(info_note, False, False, 0)
        self.pages.add_named(self.info_page, "information")

        self.setup_scroll = Gtk.ScrolledWindow()
        self.setup_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.setup_scroll.set_propagate_natural_height(False)
        self.setup_scroll.set_propagate_natural_width(False)
        self.setup_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.setup_scroll.add(self.setup_page)
        self.pages.add_named(self.setup_scroll, "setup")
        self.hero = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.setup_page.pack_start(self.hero, False, False, 0)
        self.mark = Gtk.Label(label="✦")
        self.mark.set_markup('<span size="24000" foreground="#e66d82">✦</span>')
        self.hero.pack_start(self.mark, False, False, 0)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.hero.pack_start(titles, True, True, 0)
        title = Gtk.Label()
        title.set_markup("<span size='xx-large' weight='bold'>Personalize H.U.M.A.N.S</span>")
        title.set_xalign(0)
        titles.pack_start(title, False, False, 0)
        subtitle = Gtk.Label(label="Choose local AI and desktop options. Nothing downloads until you ask.")
        subtitle.set_xalign(0)
        subtitle.set_line_wrap(True)
        titles.pack_start(subtitle, False, False, 0)

        model_frame = Gtk.Frame(label="  Local AI model  ")
        self.setup_page.pack_start(model_frame, False, False, 0)
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
        self.setup_page.pack_start(cloud_frame, False, False, 0)
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
        self.setup_page.pack_start(theme_frame, False, False, 0)
        theme_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        theme_box.set_border_width(12)
        theme_frame.add(theme_box)
        theme_text = Gtk.Label(label="H.U.M.A.N.S Rose is the default: warm dark surfaces with rose-red accents. You can switch to either original GTK preset. These are not macOS or an official Material UI package; they style GTK 3 apps and XFCE elements using GTK 3, not every third-party toolkit.")
        theme_text.set_xalign(0)
        theme_text.set_line_wrap(True)
        theme_box.pack_start(theme_text, False, False, 0)
        self.theme_combo = Gtk.ComboBoxText()
        for name in THEMES:
            self.theme_combo.append(name, name)
        saved_theme = self.config.get("theme", THEMES[0])
        if saved_theme in ("Corpse Rose", "Humans Rose", "H.U.M.A.N.S Rose"):
            saved_theme = "H.U.M.A.N.S Rose"
        self.theme_combo.set_active_id(saved_theme if saved_theme in THEMES else THEMES[0])
        theme_box.pack_start(self.theme_combo, False, False, 0)
        self.theme_combo.connect("changed", self.apply_theme)

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.navigation = bottom
        outer.pack_end(bottom, False, False, 0)
        self.back_button = Gtk.Button(label="Back")
        self.back_button.connect("clicked", self.show_information_page)
        bottom.pack_start(self.back_button, False, False, 0)
        self.status = Gtk.Label(label="")
        self.status.set_xalign(0)
        self.status.set_line_wrap(True)
        bottom.pack_start(self.status, True, True, 0)
        self.next_button = Gtk.Button(label="Continue to setup")
        self.next_button.get_style_context().add_class("suggested-action")
        self.next_button.connect("clicked", self.show_setup_page)
        bottom.pack_end(self.next_button, False, False, 0)
        self.done_button = Gtk.Button(label="Save choices and continue")
        self.done_button.get_style_context().add_class("suggested-action")
        self.done_button.connect("clicked", self.finish)
        bottom.pack_end(self.done_button, False, False, 0)

        if not settings_only:
            self.connect("realize", self.start_welcome_animation)
        self.connect("destroy", Gtk.main_quit)
        self.apply_theme()
        self.show_all()
        self.pages.set_visible_child_name("setup" if settings_only else "information")
        self.update_page_controls()

    def update_page_controls(self):
        information_page = self.pages.get_visible_child_name() == "information"
        self.back_button.set_visible(not information_page and not self.settings_only)
        self.next_button.set_visible(information_page)
        self.done_button.set_visible(not information_page)
        self.status.set_visible(not information_page)

    def show_setup_page(self, *_):
        self.pages.set_visible_child_name("setup")
        self.update_page_controls()

    def show_information_page(self, *_):
        if not self.settings_only:
            self.pages.set_visible_child_name("information")
            self.update_page_controls()

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
            legacy_blocks = (
                ("/* CORPSE OS PRESET BEGIN */", "/* CORPSE OS PRESET END */"),
                ("/* HUMANS OS PRESET BEGIN */", "/* HUMANS OS PRESET END */"),
                ("/* H.U.M.A.N.S OS PRESET BEGIN */", "/* H.U.M.A.N.S OS PRESET END */"),
            )
            begin, end = "/* HUMANS OS PALETTE BEGIN */", "/* HUMANS OS PALETTE END */"
            existing = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
            # Remove both the older branded block and the current one, preserving
            # any user CSS surrounding either managed section.
            for block_begin, block_end in (*legacy_blocks, (begin, end)):
                if block_begin in existing and block_end in existing:
                    prefix = existing.split(block_begin, 1)[0]
                    suffix = existing.split(block_end, 1)[1]
                    existing = prefix.rstrip() + "\n" + suffix.lstrip()
            block = begin + "\n/* H.U.M.A.N.S theme preset: " + theme + " */\n" + CSS[theme] + "\n" + end
            css_path.write_text(existing.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
            # Apply the selected preset to this running setup window immediately too.
            # The saved user stylesheet applies to other GTK 3 apps as they start.
            screen = Gdk.Screen.get_default()
            if screen is not None:
                if not hasattr(self, "_theme_provider"):
                    self._theme_provider = Gtk.CssProvider()
                    Gtk.StyleContext.add_provider_for_screen(
                        screen, self._theme_provider,
                        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                    )
                self._theme_provider.load_from_data(CSS[theme].encode("utf-8"))
            self.config["theme"] = theme
            save_config(self.config)
            self.status.set_text(f"Applied {theme} styling to GTK 3 apps. Restart other apps for full coverage.")
            self.queue_draw()
        except OSError as exc:
            self.status.set_text(f"Could not apply theme: {exc}")

    def start_welcome_animation(self, *_):
        # A brief optional fade; no looping motion and no impact on setup functionality.
        gtk_settings = Gtk.Settings.get_default()
        if gtk_settings and not gtk_settings.get_property("gtk-enable-animations"):
            return
        self.welcome_hero.set_opacity(0.15)
        state = {"step": 0}
        def tick():
            state["step"] += 1
            self.welcome_hero.set_opacity(min(1.0, 0.15 + state["step"] / 16.0))
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
            self.status.set_text("Choices saved. You can reopen H.U.M.A.N.S Setup from the Applications menu.")
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
