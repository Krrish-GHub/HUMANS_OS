#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for f in README.md docs/architecture.md docs/roadmap.md config/package-lists/corpse.list.chroot scripts/build-iso.sh scripts/test-iso.sh config/includes.chroot/usr/lib/humans-agent/agent.py config/includes.chroot/usr/bin/humans-agent config/includes.chroot/usr/share/applications/humans-agent.desktop scripts/test-agent.py; do
  [[ -s "$ROOT/$f" ]] || { echo "Missing or empty: $f" >&2; exit 1; }
done
bash -n "$ROOT/scripts/build-iso.sh" "$ROOT/scripts/test-iso.sh"
python3 -m py_compile "$ROOT/config/includes.chroot/usr/lib/humans-agent/agent.py" "$ROOT/scripts/test-agent.py"
python3 "$ROOT/scripts/test-agent.py"
if grep -RniE 'Gittu OS|Gittu-OS|Gittu_OS|Corps OS' \
    "$ROOT/README.md" "$ROOT/docs" "$ROOT/config/package-lists" \
    "$ROOT/config/includes.chroot" "$ROOT/config/hooks" "$ROOT/scripts" \
    --exclude-dir=.git --exclude-dir=__pycache__ --exclude=check-scaffold.sh; then
  echo "Found obsolete project branding." >&2
  exit 1
fi
printf 'Scaffold and agent tests passed; this script does not rebuild or boot the ISO.\n'
