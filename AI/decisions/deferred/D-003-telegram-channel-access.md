---
schema: ai-docs/deferred-decision@1
id: D-003
title: Telegram channel identity and access
status: deferred
task_gates:
  - E8-T1
---

# D-003: Telegram channel identity and access

- Status: **deferred** for live API credentials/session; **public identity recorded** under E8-T1.
- Verified channel: `https://t.me/elestate_warszawa`.
- Expected numeric channel ID: `2180077318` (matches historical import settings).
- Expected title: `El Estate | Покупка Варшава`.
- Verified message-link pattern: `https://t.me/elestate_warszawa/{message_id}`; message 3 is the public probe target.
- Operating owner: one dedicated least-privilege Telegram **user** account (not a bot).
- Worker-only secrets (mode `0600`, never in Git): API ID, API hash, Telethon string session file paths configured via `WEF_TELEGRAM_*_FILE`.
- Remaining for full resolution: owner supplies secrets to the approved NUC/GitHub secret paths; E8-T2 performs authenticated entity resolve; real new/edit/delete observations close B-003.
