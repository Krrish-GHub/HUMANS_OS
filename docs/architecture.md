# Corpse OS: initial architecture and safety boundaries

## First milestone: live desktop

- Base: Debian Live, `amd64`, XFCE desktop.
- Delivery: hybrid ISO suitable for VM testing and, after verification, USB imaging.
- Scope: a live session only. Persistent storage and an installer are separate later milestones.
- Build inputs use Debian's configured repositories at build time. Reproducible package snapshots and signed release artifacts are future work.

## First-run setup prototype

The GTK 3 setup window runs as the logged-in desktop user and writes preferences under `~/.config/corpse-os/`. It offers three curated Ollama profiles and checks approximate RAM/free home-folder disk before enabling `ollama pull`; the user must click Install. Ollama may use a separate service-owned model directory, so the displayed free-space check is only a preflight and that actual destination still needs validation. It never invokes a shell or sudo. Ollama and llama.cpp runtimes are not bundled in this scaffold, so Ollama download stays disabled until a trusted runtime is installed. A chosen GGUF path is only stored as a preference; the file is neither copied nor executed.

The Material-inspired and macOS-inspired choices are original GTK CSS presets, applied to `~/.config/gtk-3.0/gtk.css`; they are not the official Material UI library or Apple's OS/assets, and don't style every toolkit. The short GTK welcome fade does not loop. Gemini is not connected: OAuth, secure token storage, privacy disclosures, and revocation are required before enabling a cloud account flow.

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

The current setup prototypes an animated introduction and two optional GTK 3 styling presets. They are intentionally modest, can be skipped, and do not replace a fully designed desktop shell. Future motion should respect reduced-motion settings and remain usable with assistive technology.
