# H.U.M.A.N.S

H.U.M.A.N.S is an early, Linux-based, AI-agent-oriented operating-system project. The first milestone targets a bootable Debian live USB for x86-64 PCs and virtual machines, with a distinct desktop concept and carefully scoped local agent control.

> Project status: early prototype. The current local ISO has booted in QEMU; this is not an installer, daily-driver OS, or production security boundary. The first-run information screen and model/theme setup still need to be checked together in the updated image.

## Goals

- Produce a bootable, flashable live ISO for x86-64, starting from Debian Live.
- Keep the desktop responsive and approachable, with an original visual identity.
- Add local-first AI assistance behind a replaceable model-provider interface; Ollama is the planned initial provider.
- Let agents use explicit, narrow tools. Never grant an LLM unrestricted root, whole-disk, arbitrary shell, or silent file-write access.
- Require clear user approval for consequential actions such as installing software, deleting or overwriting files, privileged commands, and sending data off-device.

## First-run setup prototype

On first boot, XFCE opens a H.U.M.A.N.S information page before the existing GTK 3 model and desktop setup. The separate Applications-menu entry reopens the settings page directly. It has three curated Ollama model profiles (general assistant, lighter coding, stronger coding), approximate model disk/RAM guidance based on the current machine, and an explicit model-install button. The setup can also select an existing local GGUF file for a future llama.cpp runtime; it does not download or execute that file.

The current image does not bundle Ollama or llama.cpp. If Ollama is absent, the model download button is disabled and the screen says the runtime is missing; no unverified privileged installer is run. The model download flow uses `ollama pull <curated-tag>` only after the user clicks Install and approximate RAM/home-folder free-space checks pass. Ollama may store models on a different service volume, so that destination must also be checked. The runtime, service availability, downloaded model performance, persistence across a live-session reboot, and actual hardware compatibility still need validation.

H.U.M.A.N.S Rose is the default GTK theme: warm dark surfaces with rose-red accents, applied by first-run setup to the real GTK 3 desktop session. Material-inspired and macOS-inspired remain optional original alternatives; neither is an official Material UI library or macOS, and no Apple assets or branding are used. These presets style GTK 3 apps and GTK-based XFCE elements; non-GTK apps may not follow them. The red-accented H.U.M.A.N.S Rose preset preserves the existing warm dark desktop look; hardware coverage still needs testing.

Gemini API access is an optional first agent prototype, separate from Google-account OAuth. The agent can be configured with a Gemini API key stored in the desktop Secret Service; it never writes the key to its configuration file. The current local ISO includes the agent and has booted in QEMU to the H.U.M.A.N.S setup screen.

### Agent MVP

The source adds a small interactive Gemini agent and a fixed local-tool broker. Configure it in a desktop session with `humans-agent configure` (the key is entered with hidden input); optionally edit your own local context with `humans-agent context-edit`. Each request tells you what will be sent to Google Gemini and asks before sending. The context is stored at `~/.config/humans-agent/context.txt` with owner-only permissions.

The local tools report Wi-Fi status, list visible installed desktop apps, and offer `set_wifi_enabled`, `launch_application`, and `youtube_search_public`. Wi-Fi changes and app launches require fresh confirmation; YouTube search also asks before sending the bounded plain-text query to YouTube, then opens its public results in the default browser. The YouTube URL is fixed and encoded locally; there is no Google sign-in, account/history access, playback control, YouTube-account likes or subscriptions, or result scraping. Wi-Fi uses fixed `nmcli` arguments and verifies the resulting state; app launch uses the app's listed desktop ID through `gtk-launch`. There is no model-provided shell, root access, or arbitrary file access.

`humans-agent recommend-ui` (also in the agent's desktop menu) opens a GTK picker; `humans-agent recommend` provides the same flow in a terminal. It asks what mood, topic, or purpose to use rather than guessing. Saving a preference is optional and local (`0600`). Before sending the entered text to Gemini, the user confirms; after ideas are generated, a separate confirmation shows the exact search phrases sent to YouTube's public search page. The app extracts real public video titles/channels from that page, shows an Open video button per result, and offers Surprise me to randomly select one. Opening a chosen video has its own confirmation and may record a view. It never reads watch history or signs into YouTube. Like/Not for me buttons save only the rated video title and channel locally; future public results are reordered on-device, and ratings are never sent to Gemini or YouTube. Clear the saved topic preference with `humans-agent forget-recommendation-preference`, or local ratings with `humans-agent forget-recommendation-feedback`; remove the Gemini key with `humans-agent forget-key`.

The previously rebuilt local ISO includes the app launcher and reaches the setup screen in QEMU. The public-video recommendation picker is source-only and has not been rebuilt into an ISO. The current source has 26 offline tests. No live Gemini request, real Secret Service operation, or real Wi-Fi radio change has been tested. The existing first-run preferences remain under `~/.config/corpse-os/`; the separate agent stores its settings under `~/.config/humans-agent/`.

## Optional local login PIN

The image build config adds an optional Linux-PAM path for a four- or five-digit local login/unlock PIN. PINs use a salted scrypt verifier in root-only storage, with a five-attempt lockout; the existing account password remains the recovery route. After enrollment by an administrator, the same login prompt can accept either credential. Enroll or disable with `sudo /usr/lib/corpse-os/corpse-pin-admin.py enroll` or `disable` (PINs are entered through a hidden prompt, never command arguments).

This is not TPM-backed Windows Hello or a disk-encryption/pre-boot PIN. No ISO or VM login has been verified, and live-session auto-login and storage persistence remain open; do not treat this as a proven boot-time login feature. See [PIN login notes](docs/pin-login.md).

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
./scripts/test-iso.sh build/humans-os-amd64.iso
```

This starts QEMU with a disposable 4 GiB RAM VM and no disk passthrough. Confirm the live desktop reaches the login/session screen. This is a manual smoke test, not proof of hardware compatibility.

For a GTK UI smoke test on a Debian test host with GTK 3 introspection and Xvfb installed, run `xvfb-run -a /usr/bin/python3 scripts/test-setup-ui.py`. The test uses a fake Ollama executable; it does not download a model or prove a live session works.

## Agent safety direction

The first agent prototype is intended to be local and permissioned. Model output is untrusted input, not authorization. Tool calls must be allow-listed, validated, logged, and run as an unprivileged account. Destructive changes and external communication must be previewed and approved by the user. See [the architecture notes](docs/architecture.md).

## Current limits

- No custom installer, OTA updater, hardware compatibility claim, or secure-boot claim yet.
- The current ISO has booted in QEMU; the first-run wizard and live XFCE session still need end-to-end verification in the updated build.
- No integrated agent service exists; the setup window does not yet install Ollama or llama.cpp itself.
- Gemini/Google sign-in is not configured; any future cloud provider must be optional and require explicit opt-in and data disclosure.
- No model is “trained on your machine” by default; local personalization should begin with user-controlled preferences and memory.

## Roadmap

See [the first milestones](docs/roadmap.md). Contributions should document what changed, why it matters, and what was actually tested.

---
