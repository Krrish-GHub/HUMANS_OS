# Initial milestones

- [x] Create a public project repository with scope, safety principles, and a Debian Live build scaffold.
- [x] Add a first-run GTK setup prototype with local-model profiles, compatibility checks, explicit Ollama pull, GGUF path selection, two GTK appearance presets, and optional welcome animation.
- [ ] Package a trusted Ollama runtime (and evaluate a supported llama.cpp runtime) so first-run model installation works in the image.
- [ ] Build the ISO on a clean Debian/Ubuntu x86-64 host and record the exact result and checksum.
- [ ] Boot it in QEMU without disk passthrough; capture a screenshot and note failures.
- [ ] Exercise model compatibility/install flows and both desktop presets in a running session, including low-RAM/disk and unavailable-runtime cases.
- [ ] Add a real, optional Gemini OAuth flow only after registering the client, implementing secure token storage/revocation, and disclosing what data leaves the device.
- [ ] Test on a spare USB only after VM smoke tests; never overwrite an internal drive.
- [ ] Prototype one unprivileged, allow-listed local action with a preview/approval flow.
- [ ] Add reproducible build metadata, release checksums, and a documented recovery path.

A checkbox is not evidence of completion unless the corresponding artifact or test result is recorded.
