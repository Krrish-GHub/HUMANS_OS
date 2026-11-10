# H.U.M.A.N.S interaction research and PIN proposal

Status: design research and offline interaction mockup, with separate Linux PAM/local PIN and XFCE screen-lock integration in source. The HTML remains a visual-only demo; real lock/unlock verification in the disposable VM is still pending.

## What the guidance supports

This is a synthesis of published platform design guidance, not a user study or benchmark of macOS, Fedora, or Linux desktops. “Smoothest in the world” cannot be substantiated without building on target hardware and comparing measured, real user tasks.

- Apple’s Human Interface Guidelines say motion should explain state and feedback rather than exist for decoration; keep it brief and precise, optional, consistent with the gesture, and never block the next action. Frequent controls should not make people wait. Apple’s accessibility guidance recommends honoring Reduce Motion and replacing potentially disorienting spatial movement with calmer fades or color changes.
- Microsoft Fluent 2 likewise recommends purposeful motion that explains what changed or what comes next, natural quick durations, and a no-motion option. Avoid flashes and keep movement near the element receiving attention.
- Apple’s design principles emphasize consistency, clear feedback, predictable context, personalization, and usable fit and finish. Those are broadly useful principles, not proof that every user prefers the same style.

### H.U.M.A.N.S design direction

1. Make the desktop feel quick through responsiveness, clear hierarchy, stable layouts, and immediate control—not longer transition effects.
2. Give actions visible feedback, undo/cancel where feasible, and precise status; never make animation the only indicator.
3. Use short fades and small local transforms for rare context changes. Keep frequent clicks immediate; never make people wait for an intro.
4. Offer a real reduced-motion setting and follow the desktop preference. Avoid flashing, perpetual motion, parallax and large zoom/rotation effects.
5. Keep keyboard navigation, clear focus indicators, readable contrast, screen-reader labels, and adaptable window sizes in the core design.
6. Treat material-inspired and macOS-inspired presets as original styling directions—not copied artwork, icons, branding or a promise to reproduce an entire proprietary operating system. GTK presets also cannot change every toolkit.
7. Test the same tasks on a modest VM and target machines; measure input-to-feedback latency and frame pacing, then test onboarding, recovery and comprehension with people before making comparative claims.

## PIN: convenience, with an honest security boundary

Windows Hello for Business is not merely a short numeric password. Microsoft describes a PIN tied to a particular device and used to unlock a private key protected by a TPM; the TPM provides anti-hammering protections. A 4-digit code has only 10,000 combinations; a 5-digit code has 100,000. A basic Linux prompt that compares a PIN or stores it as a normal account password would not inherit Hello’s device binding or hardware protection.

A possible H.U.M.A.N.S design is a local convenience unlock for an already-booted desktop session:

- Allow choosing four or five numeric digits, confirm the entry, clearly label its scope (“this device”), and keep a separate strong password as recovery and for sensitive account changes.
- First establish the actual boot chain, disk-encryption behavior, user/session manager, and supported TPM state. Do not change an existing PAM stack or lock out the only administrator without a recoverable test environment.
- Never save the PIN in plaintext, logs, shell history, app settings, model prompts, or the repository. A production design needs a reviewed credential verifier/key arrangement; prefer TPM-backed, per-device key protection where the hardware and firmware support it.
- Add rate limiting/lockout with clear recovery and non-disclosing error behavior. PAM’s faillock is one relevant building block, but its stack placement/configuration must be reviewed for every login service; it is not, by itself, Windows Hello.
- Do not use a 4–5 digit PIN as the disk-encryption key or promise it can replace a pre-boot disk-encryption passphrase. Desktop unlock after boot and decrypting a powered-off device are separate security boundaries.
- Until these protections exist and are tested on a disposable VM, leave the current password login unchanged; keep PIN work as a mockup/implementation proposal.

## Interactive prototype

Open `ui-ux-prototype.html` locally in a modern browser. It contains an original H.U.M.A.N.S lock-screen concept, a 4/5-digit setup demo, and desktop sample, plus keyboard keypad input and a reduced-motion control. The demo uses only an in-memory sample code and does not write browser storage or authenticate against any operating system. Never enter a real PIN. Run `python3 scripts/test-ui-prototype.py` for offline, accessibility-marker, no-persistence, and JavaScript-syntax checks.

## Sources

- Apple Human Interface Guidelines, Motion: https://developer.apple.com/design/human-interface-guidelines/motion
- Apple Human Interface Guidelines, Accessibility: https://developer.apple.com/design/human-interface-guidelines/accessibility
- Apple Human Interface Guidelines, Design Principles: https://developer.apple.com/design/human-interface-guidelines/design-principles
- Microsoft Fluent 2, Motion: https://fluent2.microsoft.design/motion
- Microsoft Windows Hello for Business FAQ: https://learn.microsoft.com/en-us/windows/security/identity-protection/hello-for-business/faq
- Linux-PAM manual: https://man7.org/linux/man-pages/man8/pam.8.html
- `pam_faillock` manual: https://man.archlinux.org/man/pam_faillock.8.en
