# H.U.M.A.N.S local PIN login

## What is implemented

The image build includes an optional Debian PAM profile for a device-local 4- or 5-digit numeric PIN. The build hook enables the profile only inside the image chroot; it does not edit the host's PAM configuration. A successful PIN can authenticate through `pam_exec`; an unsuccessful or unavailable PIN falls through to the existing account-password module. Password recovery remains available when PIN attempts are locked out.

An administrator can enroll or disable the current local user's PIN after authenticating with that account's existing `sudo` policy:

```sh
sudo /usr/lib/corpse-os/corpse-pin-admin.py enroll
sudo /usr/lib/corpse-os/corpse-pin-admin.py disable
```

Enrollment asks for the PIN twice through a hidden prompt; it is not passed on the command line. The verifier is a random-salted scrypt hash, stored in a root-owned mode-0600 file under `/var/lib/corpse-os/`. PIN lockout state is also root-owned and protected; five failed attempts in the tracked 15-minute window lock PIN authentication for 15 minutes. The account password is not blocked by that PIN lockout.

## Security boundary and deployment status

This is local PAM session authentication, not TPM-backed Windows Hello, biometric authentication, disk encryption, or pre-boot unlock. A four- or five-digit PIN is not suitable as an encryption key. No graphical enrollment/settings screen is included.

The isolated PAM integration test exercises the packaged verifier with the real `pam_exec.so` module under a temporary PAM service; its password fallback is a test-only helper, not the host's `pam_unix`. Neither `/etc/pam.d` on the host nor the host's login configuration is changed by the test.

The image installs `xfce4-screensaver`, configures XFCE session locking to call `xfce4-screensaver-command --lock`, and supplies a dedicated `xfce4-screensaver` PAM stack. That stack asks `pam_unix` first so the entered token is available to the PIN verifier; successful account passwords remain a fallback, while empty passwords cannot unlock the screen. The isolated PAM test exercises PIN and password success, wrong-PIN rejection, lockout, and password recovery through this exact stack. A real lock/unlock test in the rebuilt disposable VM is still required before claiming GUI PIN unlock works. PIN persistence across reboot and autologin behavior also need separate validation.

## Tests

On a Debian test host with the PAM development headers, PAM runtime and a C compiler installed:

```sh
bash scripts/check-scaffold.sh
sudo python3 scripts/test-pin-auth.py
sudo python3 scripts/test-pin-pam.py
```

The unit test covers 4/5-digit validation, salted scrypt verification, file ownership/modes, lockout and PIN removal. The PAM test creates temporary service and credential files, plus a disposable system account for testing the real `pam_unix` fallback; it removes these on exit. It does not change the invoking account password or host PAM configuration. These tests do not substitute for a built-image or VM login test.
