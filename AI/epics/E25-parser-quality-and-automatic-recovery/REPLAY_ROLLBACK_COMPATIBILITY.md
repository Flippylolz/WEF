# E25-T4 additive replay migration compatibility

The owner requested repair and merge of PR #337 on 2026-10-19. This unplanned
prerequisite prepares the current 0027 runtime as its application rollback image.
It does not implement another task or activate replay.

PR #337 allocates `20261019_0028` after deployed `20260908_0027`. Its additive
replay ledgers and expanded parser-origin constraint leave the 0027 writer valid.
This reader explicitly accepts 0027 and 0028; arbitrary later revisions remain
unready. Deploy this compatibility release successfully before merging #337.
The replay writer will require 0028, because its optional maintenance accesses
those ledgers. Rollback retains the additive schema and uses this prior image;
never downgrade or drop production metadata to roll back the application.

Validation is recorded in the prerequisite PR. The readiness integration test
checks both accepted revisions and rejects an unrelated successor. Full lint,
format, type, test and contract gates remain required before push and merge.
