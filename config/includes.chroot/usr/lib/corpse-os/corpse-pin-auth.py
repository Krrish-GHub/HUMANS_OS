#!/usr/bin/python3
"""pam_exec verifier. Exit success only for a configured local 4/5-digit PIN."""
import argparse
import os
import pwd
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpse_pin

PIN_DIR = "/var/lib/corpse-os/pins"
STATE_DIR = "/var/lib/corpse-os/pin-state"


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--credential-dir", default=PIN_DIR)
    parser.add_argument("--state-dir", default=STATE_DIR)
    args = parser.parse_args()
    # pam_exec exposes the current PAM authtok on stdin. Do not print, log, or persist it.
    if os.geteuid() != 0 or os.environ.get("PAM_TYPE") != "auth":
        return 1
    username = os.environ.get("PAM_USER", "")
    try:
        account = pwd.getpwnam(username)
    except (KeyError, TypeError, ValueError):
        return 1
    if account.pw_uid < 1000 or account.pw_uid == 65534:
        return 1
    try:
        raw = sys.stdin.buffer.read(4096)
        if len(raw) >= 4096:
            return 1
        pin = raw.decode("ascii").rstrip("\r\n")
        return 0 if corpse_pin.authenticate(args.credential_dir, args.state_dir,
                                             account.pw_uid, pin) else 1
    except (OSError, ValueError, UnicodeError, PermissionError):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
