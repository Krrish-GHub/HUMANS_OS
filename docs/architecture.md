# Corpse OS: initial architecture and safety boundaries

## First milestone: live desktop

- Base: Debian Live, `amd64`, XFCE desktop.
- Delivery: hybrid ISO suitable for VM testing and, after verification, USB imaging.
- Scope: a live session only. Persistent storage and an installer are separate later milestones.
- Build inputs are pinned to Debian's configured stable repositories at build time. Reproducible package snapshots and signed release artifacts are future work.

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

The visual direction can use calm dark surfaces, warm neutral accents, restrained motion, and a clear agent activity panel. This is a design direction, not a completed desktop shell. The project should remain usable without animation and with assistive technologies.
