#!/usr/bin/env python3
"""Root-only PIN verifier helpers for the optional H.U.M.A.N.S PAM profile.

This is a device-local convenience credential, not disk encryption or TPM-backed
Windows Hello. The verifier directory and lockout state must remain root-owned.
"""
import fcntl
import hashlib
import hmac
import json
import os
import secrets
import stat
import struct
import time

PIN_MIN = 4
PIN_MAX = 5
SCRYPT_N = 1 << 15
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_BYTES = 32
MAX_PIN_FILE = 2048
MAX_FAILURES = 5
FAILURE_WINDOW = 15 * 60
LOCK_SECONDS = 15 * 60
_STATE = struct.Struct("!QQQ")


def valid_pin(pin):
    return isinstance(pin, str) and len(pin) in (PIN_MIN, PIN_MAX) and all("0" <= c <= "9" for c in pin)


def _secure_dir(path, create=False):
    path = os.fspath(path)
    if create:
        os.makedirs(path, mode=0o700, exist_ok=True)
    info = os.lstat(path)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
        raise PermissionError("PIN data directory is not a root-owned 0700 directory")
    return path


def _secure_read(path):
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
            raise PermissionError("PIN file is not a root-owned 0600 regular file")
        chunks = []
        size = 0
        while True:
            part = os.read(fd, 1024)
            if not part:
                break
            size += len(part)
            if size > MAX_PIN_FILE:
                raise ValueError("PIN file is unexpectedly large")
            chunks.append(part)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _atomic_write(directory, path, data):
    temp = os.path.join(directory, ".pin-tmp-" + secrets.token_hex(12))
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(temp, flags, 0o600)
    try:
        os.fchown(fd, 0, 0)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
        os.replace(temp, path)
        dfd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temp)
        except FileNotFoundError:
            pass


def credential_path(pin_dir, uid):
    return os.path.join(_secure_dir(pin_dir), f"{int(uid)}.json")


def state_path(state_dir, uid):
    return os.path.join(_secure_dir(state_dir), f"{int(uid)}.bin")


def enroll_pin(pin_dir, uid, pin):
    if os.geteuid() != 0:
        raise PermissionError("PIN enrollment requires administrator authorization")
    if not valid_pin(pin):
        raise ValueError("PIN must be exactly four or five digits")
    directory = _secure_dir(pin_dir, create=True)
    salt = os.urandom(16)
    verifier = hashlib.scrypt(pin.encode("ascii"), salt=salt, n=SCRYPT_N,
                              r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_BYTES,
                              maxmem=64 * 1024 * 1024)
    record = {
        "version": 1,
        "algorithm": "scrypt",
        "n": SCRYPT_N,
        "r": SCRYPT_R,
        "p": SCRYPT_P,
        "salt": salt.hex(),
        "verifier": verifier.hex(),
    }
    _atomic_write(directory, os.path.join(directory, f"{int(uid)}.json"),
                  (json.dumps(record, separators=(",", ":")) + "\n").encode("ascii"))


def remove_pin(pin_dir, uid):
    if os.geteuid() != 0:
        raise PermissionError("PIN removal requires administrator authorization")
    directory = _secure_dir(pin_dir, create=True)
    path = os.path.join(directory, f"{int(uid)}.json")
    try:
        info = os.lstat(path)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
            raise PermissionError("Refusing to remove an unsafe PIN file")
        os.unlink(path)
    except FileNotFoundError:
        pass


def _read_record(pin_dir, uid):
    try:
        raw = _secure_read(credential_path(pin_dir, uid))
        record = json.loads(raw.decode("ascii"))
        if (record.get("version") != 1 or record.get("algorithm") != "scrypt"
                or record.get("n") != SCRYPT_N or record.get("r") != SCRYPT_R
                or record.get("p") != SCRYPT_P):
            return None
        salt = bytes.fromhex(record["salt"])
        verifier = bytes.fromhex(record["verifier"])
        if len(salt) != 16 or len(verifier) != SCRYPT_BYTES:
            return None
        return salt, verifier
    except (OSError, ValueError, KeyError, TypeError, UnicodeError):
        return None


def _open_state(state_dir, uid):
    path = state_path(state_dir, uid)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
        os.close(fd)
        raise PermissionError("PIN lockout state is not a root-owned 0600 regular file")
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def _state_read(fd):
    raw = os.pread(fd, _STATE.size + 1, 0)
    if not raw:
        return 0, 0, 0
    if len(raw) != _STATE.size:
        # Fail closed if state was corrupted; a password can still recover the account.
        return MAX_FAILURES, 1, int(time.time()) + LOCK_SECONDS
    return _STATE.unpack(raw)


def _state_write(fd, failures, window_start, locked_until):
    raw = _STATE.pack(max(0, failures), max(0, window_start), max(0, locked_until))
    os.ftruncate(fd, 0)
    written = os.pwrite(fd, raw, 0)
    if written != len(raw):
        raise OSError("incomplete lockout state write")
    os.fsync(fd)


def authenticate(pin_dir, state_dir, uid, pin, now=None):
    """Return True for a valid PIN; record throttled failures otherwise."""
    if not valid_pin(pin):
        return False
    record = _read_record(pin_dir, uid)
    if record is None:
        return False
    now = int(time.time() if now is None else now)
    fd = _open_state(state_dir, uid)
    try:
        failures, window_start, locked_until = _state_read(fd)
        if now < locked_until:
            return False
        if locked_until:
            failures, window_start, locked_until = 0, 0, 0
        salt, expected = record
        candidate = hashlib.scrypt(pin.encode("ascii"), salt=salt, n=SCRYPT_N,
                                   r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_BYTES,
                                   maxmem=64 * 1024 * 1024)
        if hmac.compare_digest(candidate, expected):
            _state_write(fd, 0, 0, 0)
            return True
        if failures == 0 or now - window_start > FAILURE_WINDOW:
            failures, window_start = 1, now
        else:
            failures += 1
        if failures >= MAX_FAILURES:
            _state_write(fd, 0, 0, now + LOCK_SECONDS)
        else:
            _state_write(fd, failures, window_start, 0)
        return False
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
