#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 || ! -f "$1" ]]; then
  echo "Usage: $0 path/to/corpse-os-amd64.iso" >&2
  exit 2
fi
ISO="$(realpath "$1")"
command -v qemu-system-x86_64 >/dev/null || { echo "Install qemu-system-x86 to run the VM smoke test." >&2; exit 2; }
exec qemu-system-x86_64 \
  -m 4096 \
  -smp 2 \
  -boot d \
  -cdrom "$ISO" \
  -nic user,model=virtio-net-pci \
  -display gtk
