# H.U.M.A.N.S boot splash

The live image uses a Plymouth script theme rather than trying to run the browser HTML during boot. The animation is recreated as low-cost PNG frames: an AMOLED black background, the H.U.M.A.N.S wordmark, a figure-eight orbit, and gold, red, and blue glow phases based on the supplied visual.

`config/package-lists/corpse-splash.list.chroot` installs Plymouth. The live chroot hook selects this theme and rebuilds its initramfs. The live kernel command line already includes `splash`. Plymouth messages and real boot progress are drawn over the animation; the source page's click hint and simulated status text are intentionally omitted.

Regenerate assets with `python3 scripts/generate_plymouth_splash.py`. The visual source is the owner's updated `corpse-os-boot-amoled.html` file.

This source integration is separate from building or flashing an image. Verify the theme in a freshly built ISO and VM before claiming visual boot success. No repository commit or push is part of that verification.
