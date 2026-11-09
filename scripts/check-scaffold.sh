#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for f in README.md docs/architecture.md docs/roadmap.md config/package-lists/corpse.list.chroot scripts/build-iso.sh scripts/test-iso.sh; do
  [[ -s "$ROOT/$f" ]] || { echo "Missing or empty: $f" >&2; exit 1; }
done
bash -n "$ROOT/scripts/build-iso.sh" "$ROOT/scripts/test-iso.sh"
if grep -RniE 'Gittu OS|Gittu-OS|Gittu_OS|Corps OS' "$ROOT" --exclude-dir=.git --exclude=check-scaffold.sh; then
  echo "Found obsolete project branding." >&2
  exit 1
fi
printf 'Scaffold checks passed. ISO build and VM boot remain unverified.\n'
