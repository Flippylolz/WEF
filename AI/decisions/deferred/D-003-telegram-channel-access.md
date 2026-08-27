---
schema: ai-docs/deferred-decision@1
id: D-003
title: Telegram channel identity and access
status: deferred
task_gates:
  - E8-T1
---

# D-003: Telegram channel identity and access

- Status: **deferred** for real live acceptance; **API credentials and an authorized session live in deploy-managed configuration**.
- Verified channel: `https://t.me/elestate_warszawa`.
- Expected numeric channel ID: `2180077318` (matches historical import settings).
- Expected title: `El Estate | Покупка Варшава`.
- Verified message-link pattern: `https://t.me/elestate_warszawa/{message_id}`; message 3 is the public probe target.
- Operating owner: one dedicated least-privilege Telegram **user** account (not a bot).
- Credentials: `WEF_TELEGRAM_API_ID` and `WEF_TELEGRAM_API_HASH` in gitignored `.env` locally and in GitHub production secrets / NUC `production.env`. The worker generates the Telethon string session in-process and persists `WEF_TELEGRAM_SESSION` (never Git).
- Release `3ee56a5` created and started the production worker service on 2026-08-26. Remaining for full resolution: record verified live entity resolution, real new/edit/delete observations, gap reconciliation, and outage recovery without exposing session data.
