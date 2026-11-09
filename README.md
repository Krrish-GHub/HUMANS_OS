# Corpse OS

Corpse OS is an early, Linux-based, AI-agent-oriented operating-system project. The first milestone targets a bootable Debian live USB for x86-64 PCs and virtual machines, with a distinct desktop concept and carefully scoped local agent control.

> Project status: early public scaffold with a first-run GTK setup prototype. The image configuration and scripts are prepared, but an ISO has not yet been built or boot-tested. This is not an installer, daily-driver OS, or production security boundary.

## Goals

- Produce a bootable, flashable live ISO for x86-64, starting from Debian Live.
- Keep the desktop responsive and approachable, with an original visual identity.
- Add local-first AI assistance behind a replaceable model-provider interface; Ollama is the planned initial provider.
- Let agents use explicit, narrow tools. Never grant an LLM unrestricted root, whole-disk, arbitrary shell, or silent file-write access.
- Require clear user approval for consequential actions such as installing software, deleting or overwriting files, privileged commands, and sending data off-device.

## First-run setup prototype

On an image built with the current configuration, XFCE launches a first-run GTK 3 setup window. It has three curated Ollama model profiles (general assistant, lighter coding, stronger coding), approximate model disk/RAM guidance based on the current machine, and an explicit model-install button. A separate Applications-menu entry reopens setup later. The setup can also select an existing local GGUF file for a future llama.cpp runtime; it does not download or execute that file.

The current image does not bundle Ollama or llama.cpp. If Ollama is absent, the model download button is disabled and the screen says the runtime is missing; no unverified privileged installer is run. The model download flow uses `ollama pull <curated-tag>` only after the user clicks Install and approximate RAM/home-folder free-space checks pass. Ollama may store models on a different service volume, so that destination must also be checked. The runtime, service availability, downloaded model performance, persistence across a live-session reboot, and actual hardware compatibility still need validation.

Two original GTK styling presets are offered: Material-inspired and macOS-inspired. They are not an official Material UI library or macOS, and use no Apple assets or branding. Their CSS targets GTK 3 apps and GTK-based XFCE elements; non-GTK apps may not follow them. A brief, non-looping fade introduces the window; the setup remains usable without it.

Gemini is shown only as a future optional cloud integration. Google OAuth client registration, consent flow, token storage, privacy/data-transfer disclosures, and revocation controls are not implemented. The prototype does not ask for a Google password or API key and cannot sign in.

Preferences are stored per-user under `~/.config/corpse-os/`. Choosing a profile is not the same as installing its model. AI agent execution is not implemented in this prototype; the setup itself grants no AI process access to files or elevated privileges.

## Build the live image

On a Debian or Ubuntu x86-64 build host, install the prerequisites and run:

```bash
sudo apt-get update
sudo apt-get install -y live-build debootstrap xorriso squashfs-tools
./scripts/build-iso.sh
```

The resulting ISO should appear under `build/`. You can verify its checksum with:

```bash
sha256sum build/*.iso
```

Test the image in a VM before writing it to removable media. The build script will refuse to write to a disk device; it only creates an ISO file. Do not flash it to an internal drive.

## Test in a virtual machine

After a successful build, run:

```bash
./scripts/test-iso.sh build/corpse-os-amd64.iso
```

This starts QEMU with a disposable 4 GiB RAM VM and no disk passthrough. Confirm the live desktop reaches the login/session screen. This is a manual smoke test, not proof of hardware compatibility.

For a GTK UI smoke test on a Debian test host with GTK 3 introspection and Xvfb installed, run `xvfb-run -a /usr/bin/python3 scripts/test-setup-ui.py`. The test uses a fake Ollama executable; it does not download a model or prove a live session works.

## Agent safety direction

The first agent prototype is intended to be local and permissioned. Model output is untrusted input, not authorization. Tool calls must be allow-listed, validated, logged, and run as an unprivileged account. Destructive changes and external communication must be previewed and approved by the user. See [the architecture notes](docs/architecture.md).

## Current limits

- No custom installer, OTA updater, hardware compatibility claim, or secure-boot claim yet.
- No ISO has been built or boot-validated, and the setup UI has not been exercised in a running XFCE session.
- No integrated agent service exists; the setup window does not yet install Ollama or llama.cpp itself.
- Gemini/Google sign-in is not configured; any future cloud provider must be optional and require explicit opt-in and data disclosure.
- No model is “trained on your machine” by default; local personalization should begin with user-controlled preferences and memory.

## Roadmap

See [the first milestones](docs/roadmap.md). Contributions should document what changed, why it matters, and what was actually tested.

---
