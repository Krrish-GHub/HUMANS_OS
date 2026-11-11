# H.U.M.A.N.S agent architecture: selectable models and local control

Status: design proposal only. The existing project documents an XFCE/Debian live-image prototype and a future policy broker; it does not yet implement an agent service, provider selection, personal-context store, or system-action bridge. This proposal expands the planned agent around Krrish's stated goal: choose Gemini or another model through an API key, give it useful personal context, and let it perform practical desktop tasks such as toggling Wi-Fi or helping with YouTube.

## Design goal

Make the agent broadly useful without giving a language model direct authority over the machine. The model may understand requests and propose actions; only a local, typed, policy-checked broker may execute them. “Full control” should mean a growing set of real OS capabilities under the user's chosen grants—not an unrestricted root shell, hidden automation, or permission to treat webpages and files as instructions.

## Components and trust boundaries

1. **Desktop agent UI** — conversation, current task plan, previews, approval prompts, running/cancel state, permission controls, provider/context settings, and a visible emergency stop. The UI remains usable if the model or network is unavailable.
2. **Agent orchestrator (unprivileged user process)** — receives a request, retrieves only allowed context, asks a selected model for a structured plan, validates its schema, and coordinates the task lifecycle. It never executes model-produced shell text.
3. **Provider adapters** — one stable interface for Gemini and later providers; a local Ollama/llama.cpp adapter can be another choice. Adapters handle model requests only, not desktop permissions. Keep provider-specific authentication out of the UI and logs.
4. **Personal-context service** — user-owned, inspectable profile and memory with per-item provenance, scope, retention and delete controls. Retrieve only relevant records. Treat imported files, browser content, notifications and model output as untrusted data, never as consent or policy.
5. **Local tool broker** — a narrow IPC service exposing versioned, typed operations such as `wifi.status`, `wifi.set_enabled`, `app.launch`, `files.list_scoped`, `files.read_scoped`, or `youtube.search`. Validate arguments, caller, permission, target and current state at execution time. Return structured results, not a shell.
6. **Small privileged helpers, only where necessary** — user-level DBus/desktop APIs should handle ordinary tasks. If a task truly needs elevated privileges, use a narrowly defined Polkit action with a human-visible system prompt; never provide the model with root, sudo, a general terminal, or a reusable privileged token.
7. **Audit and recovery** — record task/action IDs, requested operation, approval decision and result, with secrets and sensitive content redacted. Provide stop/revoke controls and a password-based recovery route. Logs must not become a second store of private context.

## Request lifecycle

`request → relevant-context selection → structured plan → local policy check → preview/approval when needed → typed tool execution → verify actual state → concise result`

Every action has a stable ID and an explicit schema. Revalidate policy and live state at execution, prevent stale/replayed approvals, make actions idempotent where possible, and stop dependent steps after failure. Model-generated plans, tool output and remote content are all untrusted. A task that reads a page must not obey instructions found on that page. Show the user what data will leave the device before sending personal context to a cloud provider.

## Permissions: broad capability, specific authority

Offer configurable grants by capability, not a single “AI can do anything” switch. A grant should identify the allowed tool/category, scope, duration and whether each action needs a prompt. Start with all external sharing and privileged actions disabled; users can enable capabilities deliberately.

- **Read-only and low impact:** answer from selected local context, inspect Wi-Fi state, open an application, or search public YouTube content, within granted scope. These can run without a per-action prompt after the user enables that capability.
- **Reversible device changes:** toggling Wi-Fi or changing a visible desktop preference may be allowed after an explicit category grant; on first use, show the exact device change. Always report the actual result and offer undo where meaningful.
- **Sensitive or consequential:** deleting/overwriting files, installing software, changing accounts/security settings, privileged commands, purchases, messages, public posts, or uploading private data require a fresh, exact action preview and approval. Scope approvals to one operation and its stated target.
- **Never delegate:** arbitrary shell/root access, silent credential use, blanket access to all files or browser sessions, or an approval that can be reused for a different action.

The user can pause the agent, revoke any grant, choose local-only operation, and inspect or delete saved context. A network outage or model refusal must not leave a half-executed hidden plan.

## Model credentials and Google account access

An API key authorizes model API calls; it is not a Google account sign-in and does not grant access to Gmail, YouTube history, or other Google data. Store keys in the desktop's OS Secret Service/keyring, never in source control, plain configuration, prompts, screenshots or logs. Support add/replace/revoke and show the provider/model in use without exposing the key. Before a cloud request, disclose the categories of context being sent; allow a per-request context toggle and a local-only mode.

If Krrish wants personalized YouTube history or account-specific recommendations, implement a separate Google OAuth flow with the narrowest available YouTube scopes and explicit consent; explain exactly what is read and how to revoke it. Without that OAuth grant, offer public search/recommendations only. Do not ask for or store a Google password. Model sign-in and YouTube data access are independent settings.

## Personal context

Keep a user-controlled profile and memory separate from chat transcripts and provider credentials. Each item should record its source, date, confidence and purpose; support view, edit, forget and export. Retrieve a minimal relevant subset for each task. Sensitive categories should be excluded by default and require explicit user selection. Cloud providers receive only context needed for that request, after clear disclosure; never train on the user's data by default or imply that a model has learned persistent facts when they are only in local memory.

## Suggested delivery sequence

1. **Foundation:** document threat model and action schemas; implement a user-level orchestrator plus broker skeleton, task lifecycle, stop control, policy tests and audit redaction. No cloud keys or machine-changing actions yet.
2. **Provider choice:** implement the adapter interface and settings for Gemini plus one alternative or local provider. Securely store/revoke API credentials. Verify provider failures and local-only behavior.
3. **Context:** add opt-in, editable profile/memory with provenance and per-request context selection. Test that irrelevant or sensitive items are not sent.
4. **First real action:** implement a narrow, non-root Wi-Fi status/toggle path using NetworkManager DBus or a similarly constrained interface. Add permission prompt, state verification, failure handling and tests for model prompt injection. Do not expose `nmcli` as free-form shell.
5. **Useful desktop tasks:** the source now lists visible desktop entries and can launch one listed application after a fresh confirmation. Scoped file read/search and preview-and-approve for writes or installs remain next, with sandbox and path/symlink tests.
6. **YouTube:** begin with public search. Add Google OAuth only if personalized account data is needed; test scopes, revocation, no-token handling and privacy disclosure.
7. **Persistence and release readiness:** test saved settings/context across reboot, keyring behavior, offline recovery, accessibility and resource use; only then test on spare hardware. Keep real-hardware compatibility separate from VM evidence.

## Acceptance criteria for the first agent MVP

- User can select a provider/model and revoke its credential without exposing it in files, logs or chat.
- User can inspect/edit/delete context and see the subset selected for a task and what is sent to a cloud model.
- Model output cannot execute a command directly; every tool call passes typed validation and a local permission check.
- At least one real task (Wi-Fi status and an explicitly authorized toggle) works end-to-end, verifies final state, reports failure honestly and can be stopped.
- A malicious instruction embedded in a webpage/file cannot widen permissions or trigger an unapproved action.
- The system remains usable and can recover if the provider is offline or returns malformed output.

## Current implementation boundary

A small executable MVP exists at `config/includes.chroot/usr/lib/humans-agent/agent.py` and is included in the rebuilt ISO with a desktop launcher. It configures the Gemini model, stores the API key through `secret-tool` in the desktop Secret Service, supports optional owner-only context with a per-request Google data-transfer confirmation, and exposes Wi-Fi status, typed Wi-Fi enable/disable, listing visible applications, and launching a listed application. State-changing requests require a fresh interactive confirmation; Wi-Fi state is verified using NetworkManager. `scripts/test-agent.py` covers the provider request contract, API-key redaction, typed-tool allowlisting, app selection and confirmation, and Wi-Fi state verification. The ISO boots in QEMU to the H.U.M.A.N.S setup screen; all 13 offline tests pass.

This remains an early MVP, not production-ready: no live Gemini request, actual Secret Service operation, real Wi-Fi change, malicious-content end-to-end test, or persistence across reboot has been tested. Google-account OAuth, YouTube/history access, generic system automation, broader personal-data integrations, and unrestricted shell/root remain out of scope.
