#!/usr/bin/env python3
"""Fast static regression checks for the first-run setup prototype."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
script = ROOT / "config/includes.chroot/usr/lib/corpse-os/corpse-setup.py"
source = script.read_text(encoding="utf-8")
ast.parse(source, filename=str(script))

for text in (
    '"qwen3:4b"', '"qwen2.5-coder:3b"', '"qwen2.5-coder:7b"',
    'subprocess.Popen(["ollama", "pull", tag]',
    'shutil.disk_usage(Path.home())', 'system_memory_gb()',
    '"Material-inspired"', '"macOS-inspired"',
    '"Choose existing GGUF"', 'Google OAuth client',
    'CORPSE OS PRESET BEGIN',  # removed when migrating the old user CSS block
    'HUMANS OS PRESET BEGIN',  # prior branded CSS marker is migrated too
    'HUMANS OS PALETTE BEGIN',
    'Welcome to H.U.M.A.N.S',
    'APP_NAME = \"H.U.M.A.N.S Setup\"',
    'Booting this session from USB or ISO does not install it onto your internal drive.',
):
    assert text in source, f"Missing required setup behavior: {text}"
assert source.index('self.pages.add_named(self.info_page, "information")') < source.index('model_frame = Gtk.Frame(label="  Local AI model  ")')
assert 'self.pages.set_visible_child_name("setup" if settings_only else "information")' in source
assert "shell=True" not in source
assert "sudo " not in source
assert "password" in source and "never asks for your Google password" in source

pkg = (ROOT / "config/package-lists/corpse.list.chroot").read_text()
for package in ("python3-gi", "gir1.2-gtk-3.0"):
    assert package in pkg.splitlines(), f"Missing image package: {package}"

app = ROOT / "config/includes.chroot/usr/share/applications/corpse-os-setup.desktop"
autostart = ROOT / "config/includes.chroot/etc/xdg/autostart/corpse-os-first-run.desktop"
assert app.is_file() and autostart.is_file()
assert "corpse-setup.py --settings" in app.read_text()
assert "corpse-setup.py" in autostart.read_text()
assert "H.U.M.A.N.S First Run" in autostart.read_text()
print("First-run setup static checks passed. GUI, Ollama runtime/model downloads, and ISO boot are not tested by this script.")
