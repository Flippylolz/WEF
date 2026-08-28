---
schema: ai-docs/deferred-decision@1
id: D-003
title: Telegram channel identity and access
status: deferred
task_gates:
  - E8-T1
---

# D-003: Telegram channel identity and access

- Status: **deferred only for real passive new/edit/delete acceptance**; API credentials,
  authorized session, expected entity resolution, subscription, source reconciliation,
  and outage recovery are verified in deploy-managed production.
- Verified channel: `https://t.me/elestate_warszawa`.
- Expected numeric channel ID: `2180077318` (matches historical import settings).
- Expected title: `El Estate | Покупка Варшава`.
- Verified message-link pattern: `https://t.me/elestate_warszawa/{message_id}`; message 3 is the public probe target.
- Operating owner: one dedicated least-privilege Telegram **user** account (not a bot).
- Credentials: `WEF_TELEGRAM_API_ID` and `WEF_TELEGRAM_API_HASH` in gitignored `.env` locally and in GitHub production secrets / NUC `production.env`. The worker generates the Telethon string session in-process and persists `WEF_TELEGRAM_SESSION` (never Git).
- Release `3ee56a5` created and started the production worker service on 2026-08-26.
  Release `7184cc2d67a` subsequently verified live entity resolution and subscription,
  reconciled every source ID through observed head `29335`, and proved restart plus
  worker-health recovery without exposing session data.
- On 2026-08-27, read-only production evidence showed the authorized, subscribed,
  Docker-healthy worker remained at checkpoint `29202` while the verified channel
  advanced through at least `29257`. E15 is selected at blocker/P0 priority to add
  independent checkpoint reconciliation, truthful worker health, and bounded recovery.
  Those E15 controls are now deployed and accepted; exact redacted results are in
  [E15 production recovery evidence](../../epics/E15-telegram-ingestion-reliability/PRODUCTION_EVIDENCE.md).
  D-003 remains deferred only because no real passive new/edit/delete callback occurred
  during the observation window. Do not create a source-channel event without separate
  authority merely to close this record.
