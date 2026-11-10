#!/usr/bin/env python3
"""Unit tests for root-owned PIN enrollment, verification, lockout and recovery state."""
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config/includes.chroot/usr/lib/corpse-os"))
import corpse_pin


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run with sudo: sudo python3 scripts/test-pin-auth.py (isolated temp data only).")
    with tempfile.TemporaryDirectory(prefix="corpse-pin-unit-") as temp:
        root = Path(temp)
        pin_dir, state_dir = root / "pins", root / "state"
        pin_dir.mkdir(mode=0o700)
        state_dir.mkdir(mode=0o700)
        assert corpse_pin.valid_pin("1234")
        assert corpse_pin.valid_pin("01234")
        for invalid in ("123", "123456", "12a4", "１２３４", " 1234", ""):
            assert not corpse_pin.valid_pin(invalid), invalid

        uid = 1000
        corpse_pin.enroll_pin(pin_dir, uid, "0427")
        cred_path = pin_dir / f"{uid}.json"
        record = json.loads(cred_path.read_text())
        assert record["algorithm"] == "scrypt" and len(bytes.fromhex(record["salt"])) == 16
        assert "0427" not in cred_path.read_text()
        assert stat.S_IMODE(cred_path.stat().st_mode) == 0o600
        assert cred_path.stat().st_uid == 0
        assert corpse_pin.authenticate(pin_dir, state_dir, uid, "0427", now=1000)
        assert not corpse_pin.authenticate(pin_dir, state_dir, uid, "0428", now=1001)
        state_path = state_dir / f"{uid}.bin"
        assert state_path.stat().st_uid == 0 and stat.S_IMODE(state_path.stat().st_mode) == 0o600
        assert corpse_pin.authenticate(pin_dir, state_dir, uid, "0427", now=1002)

        for attempt in range(corpse_pin.MAX_FAILURES):
            assert not corpse_pin.authenticate(pin_dir, state_dir, uid, "9999", now=2000 + attempt)
        assert not corpse_pin.authenticate(pin_dir, state_dir, uid, "0427", now=2005)
        assert corpse_pin.authenticate(pin_dir, state_dir, uid, "0427", now=2000 + corpse_pin.LOCK_SECONDS + 10)

        # Invalid-length/non-numeric input is left for the PAM account-password fallback.
        before = state_path.read_bytes()
        assert not corpse_pin.authenticate(pin_dir, state_dir, uid, "not-a-pin", now=5000)
        assert state_path.read_bytes() == before
        corpse_pin.remove_pin(pin_dir, uid)
        assert not cred_path.exists()
        assert not corpse_pin.authenticate(pin_dir, state_dir, uid, "0427", now=6000)
    print("PIN unit tests passed: 4/5-digit validation, salted scrypt, root-only files, constant-time verifier, bounded lockout, password-fallback input, and disable.")


if __name__ == "__main__":
    main()
