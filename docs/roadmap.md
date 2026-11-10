# Initial milestones

- [x] Create a public project repository with scope, safety principles, and a Debian Live build scaffold.
- [x] Add a first-run GTK setup prototype with local-model profiles, compatibility checks, explicit Ollama pull, GGUF path selection, three GTK appearance presets (H.U.M.A.N.S Rose is the default), and optional welcome animation.
- [ ] Package a trusted Ollama runtime (and evaluate a supported llama.cpp runtime) so first-run model installation works in the image.
- [ ] Build the ISO on a clean Debian/Ubuntu x86-64 host and record the exact result and checksum.
- [ ] Boot it in QEMU without disk passthrough; capture a screenshot and note failures.
- [ ] Exercise model compatibility/install flows and all three GTK desktop presets in a running session, including low-RAM/disk and unavailable-runtime cases.
- [ ] Add a real, optional Gemini OAuth flow only after registering the client, implementing secure token storage/revocation, and disclosing what data leaves the device.
- [ ] Test on a spare USB only after VM smoke tests; never overwrite an internal drive.
- [ ] Prototype one unprivileged, allow-listed local action with a preview/approval flow.
- [ ] Add reproducible build metadata, release checksums, and a documented recovery path.

- [x] Add an offline interaction concept for the lock screen, PIN setup confirmation, desktop surface, and reduced-motion behavior (`docs/ui-ux-prototype.html`). This is a visual prototype only; it is not system login or authentication.
- [x] Record motion/accessibility design research and the PIN security boundary (`docs/ui-ux-and-pin-design.md`).
- [ ] Conduct moderated usability and accessibility testing; measure responsiveness on VM and target hardware before making performance comparisons.
- [ ] Design and threat-model a per-device PIN credential flow, TPM-backed where supported, with throttling, recovery, password fallback, and non-disclosing errors. Do not treat a 4–5 digit PIN as a disk-encryption passphrase.
- [ ] Implement and test authentication only after the login/session manager, PAM stack, device/TPM support, encryption boundary, and recovery path are known. Keep the existing password login until VM tests prove recovery and lockout behavior.

A checkbox is not evidence of completion unless the corresponding artifact or test result is recorded.
