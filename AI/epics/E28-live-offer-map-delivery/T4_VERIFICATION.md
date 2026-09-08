# E28-T4 verification

The initial media scan can finish before a parser/AI recovery creates the offer.
A defaulted per-primary-source discovery receipt detects that prerequisite change
and rewinds to the earliest newly linked current owner. Subsequent work remains
bounded by the existing page limit. Source context is rebuilt chronologically;
only repairable unassociated work is reopened. Existing work identity and current
revision/lease fencing remain unchanged.

All 17 media transaction regressions passed. The new real database/filesystem
case begins with a missed caption and three unsupported images, recovers its
offer, publishes two gallery images and four derivatives, leaves the image after
a text boundary unassociated, and verifies unchanged replay has no work or asset
duplication. Static checks passed; full final validation is recorded in the PR.
Production gallery acceptance remains pending release and bounded backfill.

Migration 0027 adds a Boolean receipt and partial lookup index only. T3 prepares
the rollback reader; T4 deployment and completion depend on T3 production success.
