#!/usr/bin/python3
"""Enroll or remove this sudo-authorized user's local session PIN."""
import argparse
import getpass
import os
import pwd
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpse_pin

PIN_DIR = "/var/lib/corpse-os/pins"


def current_user():
    if os.geteuid() != 0:
        raise PermissionError("Run this command with sudo so the verifier stays root-only.")
    raw_uid = os.environ.get("SUDO_UID")
    if not raw_uid or not raw_uid.isdecimal():
        raise PermissionError("Use sudo from the account that will use this PIN.")
    user = pwd.getpwuid(int(raw_uid))
    if user.pw_uid < 1000 or user.pw_uid == 65534:
        raise PermissionError("PIN enrollment is limited to regular local user accounts.")
    return user


def main():
    parser = argparse.ArgumentParser(description="Manage the local H.U.M.A.N.S login/unlock PIN.")
    parser.add_argument("action", choices=("enroll", "disable"))
    args = parser.parse_args()
    try:
        user = current_user()
        if args.action == "disable":
            corpse_pin.remove_pin(PIN_DIR, user.pw_uid)
            print("Local PIN disabled. Your account password still works.")
            return 0
        first = getpass.getpass("New device-local PIN (4 or 5 digits): ")
        second = getpass.getpass("Confirm PIN: ")
        if first != second:
            raise ValueError("PIN entries did not match.")
        corpse_pin.enroll_pin(PIN_DIR, user.pw_uid, first)
        print("Local session PIN enrolled. The stronger account password remains available for recovery.")
        return 0
    except (OSError, ValueError, PermissionError) as exc:
        print(f"Could not update local PIN: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
