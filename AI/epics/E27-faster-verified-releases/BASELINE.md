# E27-T1 baseline — 2026-09-05

Read-only GitHub API collection of the latest 50 main-branch release runs as of
2026-09-05. Eight were manual dispatches and 42 were pushes; 30 push SHAs had an
exact matching merged PR targeting main. Of those 30, 24 had successful deploy
jobs and six were cancelled before any job started. The twelve unmatched pushes
are excluded from the ordinary cohort, not interpreted as deployed successes.
The cohort covers 2026-09-02 through 2026-09-05 and is a bounded historical sample.

| Metric | Samples | p50 | p95 |
| --- | --- | --- | --- |
| Merge to successful deploy-job completion | 24 | 580 seconds | 831 seconds |
| Event to first job start | 24 | 10 seconds | 316 seconds |
| Publish completion to deploy start | 24 | 4 seconds | 6 seconds |
| Merge to observed healthy version | 0 | unavailable | unavailable |

Percentiles use nearest rank (`ceil(p*n)`, one-based) without interpolation.
Job completion is not first healthy time. Historical cache, host activation,
rollback, and first-health timestamps are unavailable; no warm/cold split or
performance-budget pass is claimed. Cancelled jobs have no invented latency.
Runner/provider incidents have not been independently attributed. The new T1
instrumentation supplies more precise evidence for future normal releases.

The API run URLs below and exact-SHA merged-PR timestamps make the sample
reviewable without storing raw API exports or logs. No manual releases were
created to populate it.

| Run | SHA | Merged UTC | Deployment job | Merge to job end (seconds) |
| --- | --- | --- | --- | --- |
| [run 33959891006](https://github.com/Flippylolz/WEF/actions/runs/33959891006) | `a2cdb1665c9575dd855391cd85428ed232da171a` | 2026-09-05T10:09:27Z | success | 529 |
| [run 33774830809](https://github.com/Flippylolz/WEF/actions/runs/33774830809) | `a52ecbaad9842361d82ac513a3c30f9fc7fe801d` | 2026-09-03T15:48:31Z | success | 637 |
| [run 33771936322](https://github.com/Flippylolz/WEF/actions/runs/33771936322) | `677da1a181c44b63cc17063ee5fce5acc97bd46b` | 2026-09-03T15:19:24Z | success | 501 |
| [run 33676028013](https://github.com/Flippylolz/WEF/actions/runs/33676028013) | `823cac0c583178216ad681c573b9f5ba8023894f` | 2026-09-02T19:53:38Z | success | 574 |
| [run 33673571111](https://github.com/Flippylolz/WEF/actions/runs/33673571111) | `b478a06a8c50814b51e7abc14359235f50bd8453` | 2026-09-02T19:29:00Z | success | 481 |
| [run 33670234372](https://github.com/Flippylolz/WEF/actions/runs/33670234372) | `adcdb10592770d6638eb386cb40bb24b1962f4bc` | 2026-09-02T18:55:50Z | success | 891 |
| [run 33670225634](https://github.com/Flippylolz/WEF/actions/runs/33670225634) | `459c3b911b1b650e44f03e715320744c0b8a37a8` | 2026-09-02T18:55:45Z | cancelled | unavailable |
| [run 33669957000](https://github.com/Flippylolz/WEF/actions/runs/33669957000) | `660dddeb1c9908b35780e0b53bbb6ae275c6cd9d` | 2026-09-02T18:53:07Z | success | 498 |
| [run 33666318665](https://github.com/Flippylolz/WEF/actions/runs/33666318665) | `ac5d136c0ec1fd5ef74122734e8b8a038f0a987c` | 2026-09-02T18:17:39Z | success | 831 |
| [run 33666011666](https://github.com/Flippylolz/WEF/actions/runs/33666011666) | `10905b6c38d8e77139e966ec852b41e5ce0b61d3` | 2026-09-02T18:14:35Z | success | 499 |
| [run 33664488885](https://github.com/Flippylolz/WEF/actions/runs/33664488885) | `eef128cecee4108c39c8065f65ec5deff4a10159` | 2026-09-02T17:59:46Z | success | 717 |
| [run 33663512307](https://github.com/Flippylolz/WEF/actions/runs/33663512307) | `4fce3fb6d48a4f02b8d825b01ba477ca661123c5` | 2026-09-02T17:50:01Z | success | 757 |
| [run 33662961318](https://github.com/Flippylolz/WEF/actions/runs/33662961318) | `ab420e46875018d66ddfc83110123fc25d24ba99` | 2026-09-02T17:44:41Z | cancelled | unavailable |
| [run 33662567175](https://github.com/Flippylolz/WEF/actions/runs/33662567175) | `9cf21e287f88e90339ca87b00ac5de939623a99f` | 2026-09-02T17:40:46Z | success | 758 |
| [run 33662247631](https://github.com/Flippylolz/WEF/actions/runs/33662247631) | `4e19c931d1950fe230c758c949187992a744d610` | 2026-09-02T17:37:37Z | cancelled | unavailable |
| [run 33661670182](https://github.com/Flippylolz/WEF/actions/runs/33661670182) | `625e8c078dd45a6a7251fd5d17070c2c5eb32297` | 2026-09-02T17:32:03Z | success | 699 |
| [run 33661599546](https://github.com/Flippylolz/WEF/actions/runs/33661599546) | `07868595048aee90193a3e6a5b21db5b75fac6ea` | 2026-09-02T17:31:22Z | cancelled | unavailable |
| [run 33661080315](https://github.com/Flippylolz/WEF/actions/runs/33661080315) | `162623824b76e2d7dd2a4f91aa80f700b919e6c1` | 2026-09-02T17:26:25Z | success | 504 |
| [run 33659894308](https://github.com/Flippylolz/WEF/actions/runs/33659894308) | `b28c9bc15d1cc90331a978fdffd82d482ef75b39` | 2026-09-02T17:14:59Z | success | 685 |
| [run 33658985392](https://github.com/Flippylolz/WEF/actions/runs/33658985392) | `f78bfb98561c34e8d4965d801ac1967c2fb09c9a` | 2026-09-02T17:06:04Z | success | 639 |
| [run 33658293678](https://github.com/Flippylolz/WEF/actions/runs/33658293678) | `7a07cf00c9f3b02e847b7ba3d39d60f0b221a982` | 2026-09-02T16:59:27Z | success | 504 |
| [run 33654527273](https://github.com/Flippylolz/WEF/actions/runs/33654527273) | `4817c9ba9782e4a37007144118b352ba3bcbe95f` | 2026-09-02T16:22:35Z | success | 580 |
| [run 33653525707](https://github.com/Flippylolz/WEF/actions/runs/33653525707) | `f9a300660b0ccf8d02d730786f68bd5d25477623` | 2026-09-02T16:12:56Z | success | 564 |
| [run 33652397774](https://github.com/Flippylolz/WEF/actions/runs/33652397774) | `f3819c5599b2dda4b3755a5afc3cfde69f438e17` | 2026-09-02T16:02:14Z | success | 607 |
| [run 33651552146](https://github.com/Flippylolz/WEF/actions/runs/33651552146) | `fe71e58ee6d84934f9029f030321180d56a0e9dc` | 2026-09-02T15:54:14Z | success | 569 |
| [run 33649175982](https://github.com/Flippylolz/WEF/actions/runs/33649175982) | `34a4ab9432ed6a972261e0a890cab2a97f220941` | 2026-09-02T15:32:07Z | success | 628 |
| [run 33648277247](https://github.com/Flippylolz/WEF/actions/runs/33648277247) | `2c9fe7855bc99db55f85fb6fb47427878d38180b` | 2026-09-02T15:23:50Z | success | 571 |
| [run 33645866041](https://github.com/Flippylolz/WEF/actions/runs/33645866041) | `cd918c909ffcbb0262f812e28d78a332bbf97fac` | 2026-09-02T15:01:32Z | success | 589 |
| [run 33645795162](https://github.com/Flippylolz/WEF/actions/runs/33645795162) | `d31413eb9325919841bfd4cfcf7c6e83d8fbedb6` | 2026-09-02T15:00:53Z | cancelled | unavailable |
| [run 33645625438](https://github.com/Flippylolz/WEF/actions/runs/33645625438) | `30b1d8bfa4f8b310f50d6e3a812bdb156a4ab009` | 2026-09-02T14:59:21Z | cancelled | unavailable |
