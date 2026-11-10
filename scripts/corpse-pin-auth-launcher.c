#define _GNU_SOURCE
#include <pwd.h>
#include <sys/prctl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#ifndef CORPSE_PIN_PYTHON
#define CORPSE_PIN_PYTHON "/usr/bin/python3"
#endif
#ifndef CORPSE_PIN_AUTH_SCRIPT
#define CORPSE_PIN_AUTH_SCRIPT "/usr/lib/corpse-os/corpse-pin-auth.py"
#endif
#ifndef CORPSE_PIN_CREDENTIAL_DIR
#define CORPSE_PIN_CREDENTIAL_DIR "/var/lib/corpse-os/pins"
#endif
#ifndef CORPSE_PIN_STATE_DIR
#define CORPSE_PIN_STATE_DIR "/var/lib/corpse-os/pin-state"
#endif

static int valid_username(const char *name) {
    if (!name || !*name || strlen(name) > 64 || name[0] == '-') return 0;
    for (const unsigned char *p = (const unsigned char *)name; *p; ++p) {
        if (!( (*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z') ||
               (*p >= '0' && *p <= '9') || *p == '_' || *p == '-' || *p == '.'))
            return 0;
    }
    return 1;
}

int main(int argc, char **argv) {
    (void)argv;
    if (argc != 1 || geteuid() != 0) return 1;

    const char *username = getenv("PAM_USER");
    const char *type = getenv("PAM_TYPE");
    if (!valid_username(username) || !type || strcmp(type, "auth") != 0) return 1;

    struct passwd *account = getpwnam(username);
    if (!account || account->pw_uid < 1000 || account->pw_uid == 65534) return 1;
    uid_t caller = getuid();
    if (caller != 0 && caller != account->pw_uid) return 1;

    char pam_user_env[80];
    if (snprintf(pam_user_env, sizeof(pam_user_env), "PAM_USER=%s", username) < 0) return 1;
    char *const args[] = {
        (char *)CORPSE_PIN_PYTHON, "-I", (char *)CORPSE_PIN_AUTH_SCRIPT,
        "--credential-dir", (char *)CORPSE_PIN_CREDENTIAL_DIR,
        "--state-dir", (char *)CORPSE_PIN_STATE_DIR, NULL
    };
    char *const env[] = {pam_user_env, "PAM_TYPE=auth", "PATH=/usr/bin:/bin", "LANG=C", NULL};

    umask(077);
    if (prctl(PR_SET_DUMPABLE, 0, 0, 0, 0) != 0) return 1;
    execve(CORPSE_PIN_PYTHON, args, env);
    return 1;
}
