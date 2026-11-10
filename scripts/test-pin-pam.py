#!/usr/bin/env python3
"""Isolated integration test for H.U.M.A.N.S's actual pam_exec/PAM profile."""
import os
from pathlib import Path
import pwd
import secrets
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
LAUNCHER_SOURCE = ROOT / "scripts/corpse-pin-auth-launcher.c"

HARNESS = r'''#define _GNU_SOURCE
#include <security/pam_appl.h>
#include <pwd.h>
#include <grp.h>
#include <unistd.h>
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
    if (argc != 5) return 90;
    answer = argv[4];
    struct passwd *account = getpwnam(argv[3]);
    if (!account || setresgid(account->pw_gid, account->pw_gid, account->pw_gid) != 0 ||
        setresuid(account->pw_uid, account->pw_uid, account->pw_uid) != 0) return 91;
    struct pam_conv conv = { converse, NULL };
    pam_handle_t *pamh = NULL;
    int rc = pam_start_confdir(argv[2], argv[3], &conv, argv[1], &pamh);
    if (rc == PAM_SUCCESS) rc = pam_authenticate(pamh, 0);
    if (pamh) pam_end(pamh, rc);
    printf("%d\n", rc);
    return rc == PAM_SUCCESS ? 0 : 1;
}
'''


def run_auth(binary, conf, service, username, token, expected):
    result = subprocess.run([str(binary), str(conf), service, username, token],
                            text=True, capture_output=True, timeout=20)
    if result.returncode != expected:
        raise AssertionError(f"PAM token {token!r}: expected exit {expected}, got {result.returncode}; stdout={result.stdout!r} stderr={result.stderr!r}")


def pam_exec_line(profile_text, args):
    lines = profile_text.splitlines()
    auth_index = lines.index("Auth:")
    row = " ".join(next(line.strip() for line in lines[auth_index + 1:] if line.strip()).split())
    expected = "sufficient pam_exec.so expose_authtok quiet /usr/lib/corpse-os/corpse-pin-auth"
    if row != expected:
        raise AssertionError(f"Unexpected PAM profile auth entry: {row!r}")
    return f"auth sufficient {MODULE} expose_authtok quiet {args[2]}"


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run with sudo: sudo python3 scripts/test-pin-pam.py (PAM files and credentials are temporary).")
    if not MODULE.is_file():
        raise SystemExit(f"PAM exec module not found at {MODULE}; cannot run isolated integration test")
    if not LAUNCHER_SOURCE.is_file():
        raise SystemExit(f"PIN launcher source not found at {LAUNCHER_SOURCE}")
    cc = shutil.which("cc")
    if not cc:
        raise SystemExit("C compiler not found; install build-essential to run isolated PAM integration test")
    uid = int(os.environ.get("SUDO_UID", "0"))
    if uid < 1000:
        raise SystemExit("Run via sudo from a normal local account so PAM can test its real account name")
    username = pwd.getpwuid(uid).pw_name
    with tempfile.TemporaryDirectory(prefix="corpse-pin-pam-") as td:
        root = Path(td)
        os.chmod(root, 0o755)
        conf = root / "pam.d"
        conf.mkdir(mode=0o755)
        pin_dir, state_dir = root / "pins", root / "state"
        pin_dir.mkdir(mode=0o700)
        state_dir.mkdir(mode=0o700)
        fallback = root / "fallback.py"
        fallback.write_text("import sys\nsys.exit(0 if sys.stdin.buffer.read(256).rstrip(b'\\r\\n') == b'recovery-test-password' else 1)\n")
        launcher = root / "corpse-pin-auth"
        compile_args = [
            cc, "-O2", "-Wall", "-Wextra", "-Werror",
            f'-DCORPSE_PIN_AUTH_SCRIPT="{AUTH}"',
            f'-DCORPSE_PIN_CREDENTIAL_DIR="{pin_dir}"',
            f'-DCORPSE_PIN_STATE_DIR="{state_dir}"',
            str(LAUNCHER_SOURCE), "-o", str(launcher),
        ]
        subprocess.run(compile_args, check=True, timeout=30)
        os.chown(launcher, 0, 0)
        os.chmod(launcher, 0o4755)
        pin_line = pam_exec_line(PROFILE.read_text(), (pin_dir, state_dir, launcher))
        common_auth = "\n".join([
            pin_line,
            f"auth required {MODULE} expose_authtok quiet /usr/bin/python3 {fallback}",
            "",
        ])
        (conf / "corpse-pin-test").write_text(common_auth)

        # Mirror the image's Xfce service override. pam_unix prompts first and
        # saves PAM_AUTHTOK; the PIN verifier then sees that same value via
        # pam_exec expose_authtok. Run the test process with the locker's real
        # real unprivileged user session; the narrow setuid launcher alone may
        # read the root-only credential directory. Password success skips the
        # PIN and deny rules.
        xfce_auth = "\n".join([
            "auth [success=2 default=ignore] pam_unix.so try_first_pass",
            pin_line,
            "auth requisite pam_deny.so",
            "auth required pam_permit.so",
            "",
        ])
        (conf / "xfce4-screensaver").write_text(xfce_auth)
        for name in ("corpse-pin-test", "xfce4-screensaver"):
            os.chmod(conf / name, 0o644)

        source, binary = root / "harness.c", root / "pam-harness"
        source.write_text(HARNESS)
        subprocess.run([cc, str(source), "-lpam", "-o", str(binary)], check=True, timeout=30)
        sys.path.insert(0, str(LIB))
        import corpse_pin
        corpse_pin.enroll_pin(pin_dir, uid, "0427")
        run_auth(binary, conf, "corpse-pin-test", username, "0427", 0)
        run_auth(binary, conf, "corpse-pin-test", username, "recovery-test-password", 0)
        run_auth(binary, conf, "corpse-pin-test", username, "0428", 1)

        # pam_unix reads the host's shadow database, so use a disposable account
        # with a temporary password instead of changing the invoking user's password.
        test_user = "cpin-" + secrets.token_hex(4)
        test_password = "Recovery-" + secrets.token_hex(8)
        subprocess.run(["useradd", "-M", "-s", "/usr/sbin/nologin", test_user], check=True)
        try:
            subprocess.run(["chpasswd"], input=f"{test_user}:{test_password}\n", text=True,
                           check=True, stdout=subprocess.DEVNULL)
            test_uid = pwd.getpwnam(test_user).pw_uid
            corpse_pin.enroll_pin(pin_dir, test_uid, "0427")
            run_auth(binary, conf, "xfce4-screensaver", test_user, "0427", 0)
            run_auth(binary, conf, "xfce4-screensaver", test_user, test_password, 0)
            run_auth(binary, conf, "xfce4-screensaver", test_user, "0428", 1)
            for _ in range(corpse_pin.MAX_FAILURES):
                run_auth(binary, conf, "xfce4-screensaver", test_user, "9999", 1)
            run_auth(binary, conf, "xfce4-screensaver", test_user, "0427", 1)
            run_auth(binary, conf, "xfce4-screensaver", test_user, test_password, 0)
        finally:
            subprocess.run(["userdel", test_user], check=False, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    print("Isolated PAM integration passed: enrolled PIN and account password authenticate through the Xfce lock stack; wrong/locked PINs fail, and password recovery remains available. Temporary account, service files, and credentials removed.")

if __name__ == "__main__":
    main()
