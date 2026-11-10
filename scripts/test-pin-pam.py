#!/usr/bin/env python3
"""Isolated integration test for Corpse OS's actual pam_exec/PAM profile."""
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "config/includes.chroot/usr/lib/corpse-os"
AUTH = LIB / "corpse-pin-auth.py"
PROFILE = ROOT / "config/includes.chroot/usr/share/pam-configs/corpse-pin"
MODULE = Path("/usr/lib/x86_64-linux-gnu/security/pam_exec.so")

HARNESS = r'''#define _GNU_SOURCE
#include <security/pam_appl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static const char *answer;
static int converse(int n, const struct pam_message **msg, struct pam_response **resp, void *data) {
    (void)data;
    struct pam_response *r = calloc((size_t)n, sizeof(*r));
    if (!r) return PAM_BUF_ERR;
    for (int i = 0; i < n; ++i) {
        if (msg[i]->msg_style == PAM_PROMPT_ECHO_OFF || msg[i]->msg_style == PAM_PROMPT_ECHO_ON)
            r[i].resp = strdup(answer);
        else r[i].resp = strdup("");
        if (!r[i].resp) return PAM_BUF_ERR;
    }
    *resp = r;
    return PAM_SUCCESS;
}
int main(int argc, char **argv) {
    if (argc != 4) return 90;
    answer = argv[3];
    struct pam_conv conv = { converse, NULL };
    pam_handle_t *pamh = NULL;
    int rc = pam_start_confdir("corpse-pin-test", argv[2], &conv, argv[1], &pamh);
    if (rc == PAM_SUCCESS) rc = pam_authenticate(pamh, 0);
    if (pamh) pam_end(pamh, rc);
    printf("%d\n", rc);
    return rc == PAM_SUCCESS ? 0 : 1;
}
'''


def run_auth(binary, conf, username, token, expected):
    result = subprocess.run([str(binary), str(conf), username, token],
                            text=True, capture_output=True, timeout=20)
    if result.returncode != expected:
        raise AssertionError(f"PAM token {token!r}: expected exit {expected}, got {result.returncode}; stdout={result.stdout!r} stderr={result.stderr!r}")


def pam_exec_line(profile_text, args):
    lines = profile_text.splitlines()
    auth_index = lines.index("Auth:")
    row = " ".join(next(line.strip() for line in lines[auth_index + 1:] if line.strip()).split())
    expected = "sufficient pam_exec.so expose_authtok quiet /usr/lib/corpse-os/corpse-pin-auth.py"
    if row != expected:
        raise AssertionError(f"Unexpected PAM profile auth entry: {row!r}")
    # Build the same command from the packaged profile, appending only isolated temporary data paths.
    return f"auth sufficient {MODULE} expose_authtok quiet {AUTH} --credential-dir {args[0]} --state-dir {args[1]}"


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run with sudo: sudo python3 scripts/test-pin-pam.py (PAM files and credentials are temporary).")
    if not MODULE.is_file():
        raise SystemExit(f"PAM exec module not found at {MODULE}; cannot run isolated integration test")
    cc = shutil.which("cc")
    if not cc:
        raise SystemExit("C compiler not found; install build-essential to run isolated PAM integration test")
    uid = int(os.environ.get("SUDO_UID", "0"))
    if uid < 1000:
        raise SystemExit("Run via sudo from a normal local account so PAM can test its real account name")
    username = pwd.getpwuid(uid).pw_name
    with tempfile.TemporaryDirectory(prefix="corpse-pin-pam-") as td:
        root = Path(td)
        conf = root / "pam.d"
        conf.mkdir(mode=0o700)
        pin_dir, state_dir = root / "pins", root / "state"
        pin_dir.mkdir(mode=0o700)
        state_dir.mkdir(mode=0o700)
        fallback = root / "fallback.py"
        fallback.write_text("import sys\nsys.exit(0 if sys.stdin.buffer.read(256).rstrip(b'\\r\\n') == b'recovery-test-password' else 1)\n")
        pin_line = pam_exec_line(PROFILE.read_text(), (pin_dir, state_dir))
        service = "\n".join([
            pin_line,
            f"auth required {MODULE} expose_authtok quiet /usr/bin/python3 {fallback}",
            "account required pam_permit.so",
            "session required pam_permit.so",
            "",
        ])
        (conf / "corpse-pin-test").write_text(service)
        os.chmod(conf / "corpse-pin-test", 0o600)
        source, binary = root / "harness.c", root / "pam-harness"
        source.write_text(HARNESS)
        subprocess.run([cc, str(source), "-lpam", "-o", str(binary)], check=True, timeout=30)

        sys.path.insert(0, str(LIB))
        import corpse_pin
        corpse_pin.enroll_pin(pin_dir, uid, "0427")
        run_auth(binary, conf, username, "0427", 0)
        run_auth(binary, conf, username, "recovery-test-password", 0)
        run_auth(binary, conf, username, "0428", 1)
        for _ in range(corpse_pin.MAX_FAILURES):
            run_auth(binary, conf, username, "9999", 1)
        run_auth(binary, conf, username, "0427", 1)
        run_auth(binary, conf, username, "recovery-test-password", 0)
    print("Isolated PAM integration passed: packaged pam_exec profile accepts enrolled PIN; rejects wrong PIN; bounded lockout blocks PIN; existing password fallback remains usable. Temporary service/credentials removed.")

if __name__ == "__main__":
    main()
