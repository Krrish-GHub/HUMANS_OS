#!/usr/bin/python3
"""GTK smoke tests for H.U.M.A.N.S Setup. Run under Xvfb on Debian with GTK3 GIR."""
import importlib.util
import os
from pathlib import Path
import tempfile
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


def main():
    Gtk.init([])
    with tempfile.TemporaryDirectory(prefix="corpse-setup-test-") as temp:
        os.environ["HOME"] = temp
        fake_bin = Path(temp) / "bin"
        fake_bin.mkdir()
        log = Path(temp) / "ollama-args.log"
        mock = fake_bin / "ollama"
        mock.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = list ]; then printf 'NAME ID SIZE MODIFIED\\n'; exit 0; fi\n"
            "if [ \"$1\" = pull ]; then printf '%s\\n' \"$*\" >> \"$OLLAMA_TEST_LOG\"; echo simulated-pull; exit 0; fi\n"
            "exit 2\n",
            encoding="utf-8",
        )
        mock.chmod(0o755)
        os.environ["OLLAMA_TEST_LOG"] = str(log)
        os.environ["PATH"] = str(fake_bin) + os.pathsep + os.environ.get("PATH", "/usr/bin:/bin")

        source = Path(__file__).resolve().parents[1] / "config/includes.chroot/usr/lib/corpse-os/corpse-setup.py"
        spec = importlib.util.spec_from_file_location("corpse_setup", source)
        app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app)

        assert app.APP_NAME == "H.U.M.A.N.S Setup"
        assert app.THEMES[0] == "H.U.M.A.N.S Rose"
        for name, css in app.CSS.items():
            provider = Gtk.CssProvider()
            provider.load_from_data(css.encode("utf-8"))
            print(f"GTK CSS parsed: {name}")

        css_path = Path(temp) / ".config/gtk-3.0/gtk.css"
        css_path.parent.mkdir(parents=True)
        css_path.write_text(
            "/* user CSS preserved */\n"
            "/* CORPSE OS PRESET BEGIN */\n/* old palette */\n/* CORPSE OS PRESET END */\n"
            "/* HUMANS OS PRESET BEGIN */\n/* previous palette */\n/* HUMANS OS PRESET END */\n"
            "/* H.U.M.A.N.S OS PRESET BEGIN */\n/* older dotted palette */\n/* H.U.M.A.N.S OS PRESET END */\n",
            encoding="utf-8",
        )

        first_run = app.Setup(settings_only=False)
        first_run.realize()
        while Gtk.events_pending():
            Gtk.main_iteration()
        assert first_run.get_size()[1] <= first_run.get_screen().get_height()
        assert first_run.navigation.get_mapped()
        assert first_run.next_button.get_mapped()
        assert first_run.pages.get_visible_child_name() == "information"
        assert first_run.next_button.get_visible()
        assert not first_run.done_button.get_visible()
        first_run.next_button.clicked()
        assert first_run.pages.get_visible_child_name() == "setup"
        assert first_run.back_button.get_visible()
        assert first_run.done_button.get_visible()
        first_run.back_button.clicked()
        assert first_run.pages.get_visible_child_name() == "information"
        first_run.hide()

        # Older Corpse/H.U.M.A.N.S Rose settings keep the same warm red palette under the new brand.
        app.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        app.CONFIG_PATH.write_text('{"theme": "Corpse Rose"}\n', encoding="utf-8")

        # First prove the control stays disabled without an Ollama runtime.
        original_which = app.shutil.which
        app.shutil.which = lambda name: None if name == "ollama" else original_which(name)
        app.system_memory_gb = lambda: 16.0
        app.model_disk_gb = lambda: 100.0
        offline = app.Setup(settings_only=True)
        assert offline.theme_combo.get_active_id() == "H.U.M.A.N.S Rose"
        assert offline.model_combo.get_model().iter_n_children(None) == 3
        assert not offline.install_button.get_sensitive()
        offline.hide()
        app.CONFIG_PATH.write_text('{"theme": "H.U.M.A.N.S Rose"}\n', encoding="utf-8")
        older_humans = app.Setup(settings_only=True)
        assert older_humans.theme_combo.get_active_id() == "H.U.M.A.N.S Rose"
        older_humans.hide()

        # Exercise the guarded, explicit install button using only a fake local Ollama executable.
        app.shutil.which = original_which
        online = app.Setup(settings_only=True)
        assert online.model_combo.get_active_id() == "qwen3:4b"
        assert online.theme_combo.get_active_id() == "H.U.M.A.N.S Rose"
        assert hasattr(online, "_theme_provider")
        assert online.install_button.get_sensitive()
        initial_css = css_path.read_text(encoding="utf-8")
        assert "H.U.M.A.N.S theme preset: H.U.M.A.N.S Rose" in initial_css
        assert "@define-color corpse_accent #e66d82;" in initial_css
        online.install_button.clicked()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            while Gtk.events_pending():
                Gtk.main_iteration()
            if log.exists() and "ollama_model" in app.load_config():
                break
            time.sleep(0.02)
        assert log.read_text(encoding="utf-8").strip() == "pull qwen3:4b"
        assert app.load_config()["ollama_model"] == "qwen3:4b"

        # An under-RAM profile must not offer installation.
        app.system_memory_gb = lambda: 1.0
        low_ram = app.Setup(settings_only=True)
        assert not low_ram.install_button.get_sensitive()
        low_ram.hide()

        # Preset switching replaces only its managed block and keeps user CSS intact.
        online.theme_combo.set_active_id("macOS-inspired")
        while Gtk.events_pending():
            Gtk.main_iteration()
        online.theme_combo.set_active_id("H.U.M.A.N.S Rose")
        while Gtk.events_pending():
            Gtk.main_iteration()
        written = css_path.read_text(encoding="utf-8")
        assert "/* user CSS preserved */" in written
        assert "CORPSE OS PRESET BEGIN" not in written
        assert "HUMANS OS PRESET BEGIN" not in written
        assert "H.U.M.A.N.S OS PRESET BEGIN" not in written
        assert written.count("HUMANS OS PALETTE BEGIN") == 1
        assert "H.U.M.A.N.S theme preset: H.U.M.A.N.S Rose" in written
        assert "@define-color corpse_accent #e66d82;" in written
        first_run.hide()
        offline.hide()
        online.hide()
        print("GTK setup smoke passed: information-first navigation, bounded setup scrolling, old-brand rose-theme migration, model profiles, disabled-runtime and low-RAM gates, explicit mock pull, and CSS preservation.")


if __name__ == "__main__":
    main()
