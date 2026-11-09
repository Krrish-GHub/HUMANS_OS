#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "Build this initial image on an x86_64 host." >&2
  exit 2
fi
if [[ "$EUID" -eq 0 ]]; then
  echo "Run this script as a normal user; live-build may request sudo when required." >&2
  exit 2
fi
command -v lb >/dev/null || { echo "Missing live-build; install it with your distribution package manager." >&2; exit 2; }
command -v xorriso >/dev/null || { echo "Missing xorriso; install it with your distribution package manager." >&2; exit 2; }

# Keep build output inside this repository; do not write to or format block devices.
mkdir -p build
if [[ ! -f config/common ]]; then
  lb config \
    --distribution trixie \
    --architectures amd64 \
    --binary-images iso-hybrid \
    --archive-areas "main contrib non-free-firmware" \
    --debian-installer live \
    --iso-application "Corpse OS" \
    --iso-publisher "Corpse OS contributors" \
    --iso-volume "CORPSE_OS"
fi
lb build
find . -maxdepth 1 -type f -name '*.iso' -exec mv -t build/ -- {} +
shopt -s nullglob
isos=(build/*.iso)
if (( ${#isos[@]} == 0 )); then
  echo "Build finished but no ISO was found; inspect the live-build log." >&2
  exit 1
fi
sha256sum "${isos[@]}" | tee build/SHA256SUMS
printf 'ISO ready for VM testing: %s\n' "${isos[@]}"
