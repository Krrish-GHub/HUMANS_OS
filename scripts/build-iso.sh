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
command -v cc >/dev/null || { echo "Missing a C compiler (cc); install it with your distribution package manager." >&2; exit 2; }

# Build a narrowly scoped setuid launcher so PAM can verify PINs without exposing root-only hashes.
PIN_AUTH_BIN="$ROOT/config/includes.chroot/usr/lib/corpse-os/corpse-pin-auth"
cc -O2 -Wall -Wextra -Werror "$ROOT/scripts/corpse-pin-auth-launcher.c" -o "$PIN_AUTH_BIN"
chmod 0755 "$PIN_AUTH_BIN"
trap 'rm -f "$PIN_AUTH_BIN"' EXIT

# Keep build output inside this repository; do not write to or format block devices.
mkdir -p build
sudo lb config \
    --distribution trixie \
    --architectures amd64 \
    --binary-images iso-hybrid \
    --archive-areas "main contrib non-free-firmware" \
    --debian-installer live \
    --iso-application "H.U.M.A.N.S" \
    --iso-publisher "H.U.M.A.N.S contributors" \
    --iso-volume "H.U.M.A.N.S"
sudo lb build
find . -maxdepth 1 -type f -name '*.iso' -exec mv -t build/ -- {} +
if [[ -f build/live-image-amd64.hybrid.iso ]]; then
  mv build/live-image-amd64.hybrid.iso build/H.U.M.A.N.S-amd64.iso
fi
shopt -s nullglob
isos=(build/*.iso)
if (( ${#isos[@]} == 0 )); then
  echo "Build finished but no ISO was found; inspect the live-build log." >&2
  exit 1
fi
sha256sum "${isos[@]}" | tee build/SHA256SUMS
printf 'ISO ready for VM testing: %s\n' "${isos[@]}"
