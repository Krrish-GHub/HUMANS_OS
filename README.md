# Corpse OS

Corpse OS is an early, Linux-based, AI-agent-oriented operating-system project. The first milestone targets a bootable Debian live USB for x86-64 PCs and virtual machines, with a distinct desktop concept and carefully scoped local agent control.

> Project status: initial public scaffold. The live-build configuration and scripts are prepared, but an ISO has not yet been built or boot-tested. This is not an installer, daily-driver OS, or production security boundary.

## Goals

- Produce a bootable, flashable live ISO for x86-64, starting from Debian Live.
- Keep the desktop responsive and approachable, with a visual identity of its own rather than copying macOS or Windows.
- Add local-first AI assistance behind a replaceable model-provider interface; Ollama is the planned initial provider.
- Let agents use explicit, narrow tools. Never grant an LLM unrestricted root, whole-disk, arbitrary shell, or silent file-write access.
- Require clear user approval for consequential actions such as installing software, deleting or overwriting files, privileged commands, and sending data off-device.

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

## Agent safety direction

The first agent prototype is intended to be local and permissioned. Model output is untrusted input, not authorization. Tool calls should be allow-listed, validated, logged, and run as an unprivileged account. Destructive changes and external communication must be previewed and approved by the user. See [the architecture notes](docs/architecture.md).

## Current limits

- No custom installer, OTA updater, hardware compatibility claim, or secure-boot claim yet.
- No integrated agent service or full OS build has been validated yet.
- Gemini or other cloud models are not configured; a cloud provider would be optional and require explicit opt-in and data disclosure.
- No model is “trained on your machine” by default; local personalization should begin with user-controlled preferences and memory.

## Roadmap

See [the first milestones](docs/roadmap.md). Contributions should document what changed, why it matters, and what was actually tested.
