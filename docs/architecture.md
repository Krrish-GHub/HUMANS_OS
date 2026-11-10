# H.U.M.A.N.S: initial architecture and safety boundaries

## First milestone: live desktop

- Base: Debian Live, `amd64`, XFCE desktop.
- Delivery: hybrid ISO suitable for VM testing and, after verification, USB imaging.
- Scope: a live session only. Persistent storage and an installer are separate later milestones.
- Build inputs use Debian's configured repositories at build time. Reproducible package snapshots and signed release artifacts are future work.

## First-run setup prototype

The GTK 3 setup window runs as the logged-in desktop user and writes preferences under `~/.config/corpse-os/`. It offers three curated Ollama profiles and checks approximate RAM/free home-folder disk before enabling `ollama pull`; the user must click Install. Ollama may use a separate service-owned model directory, so the displayed free-space check is only a preflight and that actual destination still needs validation. It never invokes a shell or sudo. Ollama and llama.cpp runtimes are not bundled in this scaffold, so Ollama download stays disabled until a trusted runtime is installed. A chosen GGUF path is only stored as a preference; the file is neither copied nor executed.

H.U.M.A.N.S Rose is the default GTK CSS preset, applied by first-run setup to `~/.config/gtk-3.0/gtk.css`; it gives GTK 3 apps and GTK-based XFCE elements warm dark surfaces with rose-red accents. Material-inspired and macOS-inspired are optional original alternatives, not the official Material UI library or Apple's OS/assets. These presets do not style every toolkit. The short GTK welcome fade does not loop. Gemini is not connected: OAuth, secure token storage, privacy disclosures, and revocation are required before enabling a cloud account flow.

## Agent control: planned, not implemented

A later local agent service should have four distinct layers:

1. **Model adapter** — local Ollama first; a provider interface permits later alternatives without tying the OS shell to one model. Cloud providers must remain opt-in.
2. **Intent and plan** — convert a request into a proposed sequence of typed tool calls. Model text alone never executes.
3. **Policy broker** — validate each call against narrow scopes and ask the user before privileged, destructive, persistent, or network-disclosing actions.
4. **Tool runner** — invoke only named, allow-listed operations under an unprivileged account; record the request, decision, and result.

### Safety invariants

- No unrestricted root shell for a model.
- No arbitrary path access: expose scoped directories and reject traversal and symlink escapes.
- No silent delete, overwrite, package install, credential use, disk write, or data upload.
- Show the exact target and effect before asking for approval.
- Keep model-provider secrets out of prompts, logs, and the repository.
- Provide a visible stop/disable control and a human-operated recovery path.

## Desktop concept

The current setup includes an animated introduction and three GTK 3 styling presets, with H.U.M.A.N.S Rose as the default. They are intentionally modest, can be skipped, and do not replace a fully designed desktop shell. Future motion should respect reduced-motion settings and remain usable with assistive technology.

## Optional local PIN authentication

The image hook `config/hooks/live/0100-enable-corpse-pin.hook.chroot` enables the Debian PAM profile `corpse-pin` in the image's `common-auth` stack. It runs only inside the image-build chroot and must not change the build host's PAM setup. The profile invokes the root-executed `pam_exec.so` verifier in `common-auth`. XFCE screen locking has a dedicated PAM stack that asks `pam_unix` first to populate the entered token, then tests the device-local PIN; the account password remains the recovery path. Enrollment and removal are administrator-authorized CLI operations.

PIN verifiers use random-salted scrypt; verifier and lockout files are root-owned mode 0600 beneath `/var/lib/corpse-os/`. Five wrong PIN attempts in the tracked window trigger a 15-minute PIN lockout without disabling password recovery. This is password-equivalent session authentication, not TPM-backed Windows Hello, biometric login, disk encryption, or pre-boot unlock. See [PIN login notes](pin-login.md) for tests and deployment limitations.
