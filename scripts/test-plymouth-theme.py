#!/usr/bin/env python3
"""Static integration checks for the H.U.M.A.N.S Plymouth boot splash."""
from pathlib import Path
import re
from PIL import Image

root = Path(__file__).resolve().parents[1]
theme = root / "config/includes.chroot/usr/share/plymouth/themes/corpse-os"
script = (theme / "corpse-os.script").read_text(encoding="utf-8")
config = (theme / "corpse-os.plymouth").read_text(encoding="utf-8")
hook = (root / "config/hooks/live/0200-enable-corpse-plymouth.hook.chroot").read_text(encoding="utf-8")
packages = (root / "config/package-lists/corpse-splash.list.chroot").read_text(encoding="utf-8")
frames = sorted((theme / "frames").glob("frame-*.png"))
assert len(frames) == 54, f"expected 54 animation frames, got {len(frames)}"
assert re.findall(r'frames\[(\d+)\] = Image\("frames/frame-(\d{3})\.png"\);', script)
assert len(re.findall(r'frames\[\d+\] = Image\("frames/frame-\d{3}\.png"\);', script)) == 54
assert "Window.SetBackgroundTopColor (0, 0, 0)" in script
assert "Window.SetBackgroundBottomColor (0, 0, 0)" in script
assert "Plymouth.SetRefreshFunction(refresh_callback)" in script
assert "Plymouth.SetBootProgressFunction(progress_callback)" in script
assert "ModuleName=script" in config and "corpse-os.script" in config
assert "Name=H.U.M.A.N.S" in config
# The wordmark is rasterized into every PNG animation frame, not drawn by Plymouth script text.
generator = (root / "scripts/generate_plymouth_splash.py").read_text(encoding="utf-8")
assert 'label = "H.U.M.A.N.S"' in generator
assert "text_draw.text((text_x, text_y), label" in generator
assert 'label = "Corpse OS"' not in generator
assert "plymouth-set-default-theme --rebuild-initrd corpse-os" in hook
assert "update-initramfs" not in hook or "initrd.img-" in hook
assert "plymouth" in packages.splitlines()
assert "corpse-os.script" in hook and "progress-track.png" in hook
for image_path in frames + [theme / "progress-track.png", theme / "progress-fill.png"]:
    with Image.open(image_path) as image:
        image.verify()
print("Plymouth source checks passed: theme wiring, 54 frames, black background, animation/progress callbacks, valid PNG assets.")
