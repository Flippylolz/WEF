"""Channel-scoped aggregate queries; no source content leaves the persistence boundary."""

ARCHIVE = """
WITH work AS (
 SELECT e.processed_at,e.data_failure_count,e.next_attempt_at,e.received_at,e.attempts,
 e.deferral_count,e.retry_policy_version,r.event_id IS NOT NULL AS has_receipt
 FROM telegram_raw_events e LEFT JOIN telegram_archive_resolutions r ON r.event_id=e.id
 WHERE e.channel_external_id=:channel
)
SELECT count(*) FILTER (WHERE processed_at IS NOT NULL) AS terminal,
 count(*) FILTER (WHERE processed_at IS NULL AND data_failure_count>=5
   AND NOT has_receipt AND retry_policy_version=:archive_policy) AS quarantined,
 count(*) FILTER (WHERE processed_at IS NULL AND (has_receipt
   OR retry_policy_version<>:archive_policy OR data_failure_count<5 AND
   (next_attempt_at IS NULL OR next_attempt_at<=:now))) AS eligible,
 count(*) FILTER (WHERE processed_at IS NULL AND data_failure_count<5
   AND NOT has_receipt AND retry_policy_version=:archive_policy
   AND next_attempt_at>:now) AS delayed,
 coalesce(sum(attempts),0) AS attempted, coalesce(sum(deferral_count),0) AS deferred,
 min(CASE WHEN has_receipt OR retry_policy_version<>:archive_policy THEN received_at
   ELSE coalesce(next_attempt_at,received_at) END) FILTER
   (WHERE processed_at IS NULL AND (has_receipt OR retry_policy_version<>:archive_policy
    OR data_failure_count<5 AND (next_attempt_at IS NULL OR next_attempt_at<=:now))) AS oldest_due
FROM work
"""

MEDIA = """
SELECT count(*) FILTER (WHERE w.state IN ('completed','unsupported','superseded')) AS terminal,
 count(*) FILTER (WHERE w.state='quarantined'
   AND w.policy_version=:media_policy) AS quarantined,
 count(*) FILTER (WHERE w.state='completed') AS completed,
 count(*) FILTER (WHERE w.state IN ('pending','retry_wait') AND w.next_attempt_at<=:now
   OR w.state='leased' AND w.lease_until<=:now
   OR w.state='quarantined' AND w.policy_version<>:media_policy) AS eligible,
 count(*) FILTER (WHERE w.state IN ('pending','retry_wait') AND w.next_attempt_at>:now) AS
delayed,
 count(*) FILTER (WHERE w.state='leased' AND w.lease_until>:now) AS leased,
 coalesce(sum(w.deferrals),0) AS deferred,
 min(CASE WHEN w.state='leased' THEN w.lease_until ELSE w.next_attempt_at END) FILTER
   (WHERE w.state IN ('pending','retry_wait') AND w.next_attempt_at<=:now
    OR w.state='leased' AND w.lease_until<=:now) AS oldest_due
FROM media_recovery_work w JOIN source_message_revisions r ON r.id=w.source_revision_id
JOIN source_messages m ON m.id=r.source_message_id
JOIN source_channels c ON c.id=m.source_channel_id WHERE c.external_id=:channel
"""

DISCOVERY = """
SELECT count(*) FILTER (WHERE i.discovered) AS terminal,
 count(*) FILTER (WHERE NOT i.discovered) AS eligible,
 min(i.created_at) FILTER (WHERE NOT i.discovered) AS oldest_due
FROM media_recovery_intentions i JOIN source_message_revisions r ON r.id=i.source_revision_id
JOIN source_messages m ON m.id=r.source_message_id
JOIN source_channels c ON c.id=m.source_channel_id WHERE c.external_id=:channel
"""

CONTROL = """
SELECT a.phase AS archive_phase, a.pause_reason AS archive_reason,
 m.phase AS media_phase, m.reason AS media_reason, m.source_retry_at AS media_wait,
 m.scan_after_id, m.scan_upper_id, p.polled_through_id, p.sweep_after_id,
 p.last_polled_at, p.last_sweep_at, p.source_retry_at AS traversal_wait,
 (SELECT count(*) FROM source_messages s WHERE s.source_channel_id=c.id
    AND s.external_message_id>coalesce(m.scan_after_id,0) AND NOT EXISTS (SELECT 1 FROM
media_recovery_intentions i WHERE i.source_revision_id=s.current_revision_id)) AS
undiscovered_sources,
 (SELECT min(s.ingested_at) FROM source_messages s WHERE s.source_channel_id=c.id
    AND s.external_message_id>coalesce(m.scan_after_id,0) AND NOT EXISTS (SELECT 1 FROM
media_recovery_intentions i WHERE i.source_revision_id=s.current_revision_id)) AS oldest_source,
 (SELECT max(s.external_message_id) FROM source_messages s WHERE s.source_channel_id=c.id) AS
known_head
FROM source_channels c
LEFT JOIN telegram_archive_recovery a ON a.channel_external_id=c.external_id
LEFT JOIN media_recovery_channels m ON m.source_channel_id=c.id
LEFT JOIN telegram_channel_progress p ON p.source_channel_id=c.id
WHERE c.external_id=:channel
"""

EVIDENCE = """
SELECT
 (SELECT count(*) FROM source_message_revisions r JOIN source_messages m ON
m.id=r.source_message_id
   JOIN source_channels c ON c.id=m.source_channel_id WHERE c.external_id=:channel) AS
canonical_revisions,
 (SELECT count(*) FROM telegram_archive_resolutions r JOIN telegram_raw_events e ON
e.id=r.event_id WHERE e.channel_external_id=:channel) AS archive_receipts,
 (SELECT count(*) FROM media_derivative_attempts d JOIN media_assets a ON a.id=d.media_asset_id
   JOIN source_messages m ON m.id=a.source_message_id JOIN source_channels c ON
c.id=m.source_channel_id
   WHERE c.external_id=:channel AND d.status='succeeded') AS successful_variant_attempts,
 (SELECT count(*) FROM offer_media o JOIN media_assets a ON a.id=o.media_asset_id
   JOIN source_messages m ON m.id=a.source_message_id JOIN source_channels c ON
c.id=m.source_channel_id
   WHERE c.external_id=:channel) AS public_associations
"""

# Recent text-bearing photo posts remain visible to operations even when the
# parser never created an offer. Media-only album children are not extra offers.
DELIVERY = """
WITH recent AS (
 SELECT s.id,s.current_revision_id,s.ingested_at,s.raw_payload_json,
   link.offer_id,o.location_id,o.visibility,l.review_status,l.out_of_scope,l.point,l.precision
 FROM source_messages s JOIN source_channels c ON c.id=s.source_channel_id
 LEFT JOIN LATERAL (SELECT os.offer_id FROM offer_sources os
   WHERE os.source_message_id=s.id AND os.relationship='primary'
   ORDER BY os.created_at DESC LIMIT 1) link ON true
 LEFT JOIN offers o ON o.id=link.offer_id LEFT JOIN locations l ON l.id=o.location_id
 LEFT JOIN LATERAL (SELECT p.classification FROM parse_evaluations p
   WHERE p.source_message_revision_id=s.current_revision_id
   ORDER BY p.created_at DESC LIMIT 1) evaluation ON true
 WHERE c.external_id=:channel AND s.deleted_at IS NULL
   AND (o.visibility IS NULL OR o.visibility<>'hidden')
   AND s.published_at>=CAST(:now AS timestamptz)-interval '7 days'
   AND length(trim(s.text_original))>0
   AND (link.offer_id IS NOT NULL OR
       (s.raw_payload_json ? 'photo' AND
        coalesce(evaluation.classification,'unclassified')<>'expected_non_offer'))
), delivery AS (
 SELECT r.*,
   greatest(
     (SELECT min(w.next_attempt_at) FROM media_recovery_work w
      JOIN source_messages m ON m.current_revision_id=w.source_revision_id
      WHERE w.offer_id=r.offer_id AND m.deleted_at IS NULL
        AND w.state='retry_wait' AND w.next_attempt_at>CAST(:now AS timestamptz)),
     (SELECT min(w.next_attempt_at) FROM location_validation_work w
      WHERE w.location_id=r.location_id AND w.target=:validation_target
        AND w.state='deferred' AND w.next_attempt_at>CAST(:now AS timestamptz))
   ) AS retry_until,
   coalesce(visibility='visible' AND review_status='accepted' AND NOT out_of_scope
     AND point IS NOT NULL AND precision IN ('building','street','city'),false) AS mapped,
   EXISTS (SELECT 1 FROM offer_media om JOIN media_derivatives d
     ON d.media_asset_id=om.media_asset_id
     WHERE om.offer_id=r.offer_id GROUP BY om.media_asset_id
     HAVING count(DISTINCT d.variant) FILTER (WHERE d.variant IN
       ('thumbnail_webp_v1','thumbnail_jpeg_v1'))=2) AS gallery,
   EXISTS (SELECT 1 FROM media_recovery_work w JOIN source_messages m
     ON m.current_revision_id=w.source_revision_id
     WHERE w.offer_id=r.offer_id AND m.deleted_at IS NULL
       AND w.state NOT IN ('completed','superseded')) AS media_pending
 FROM recent r
)
SELECT count(*) AS expected,
 count(*) FILTER (WHERE mapped) AS mapped,
 count(*) FILTER (WHERE offer_id IS NULL) AS missing_offer,
 count(*) FILTER (WHERE offer_id IS NOT NULL AND NOT mapped) AS missing_map,
 count(*) FILTER (WHERE mapped AND (NOT gallery OR media_pending)) AS missing_gallery,
 count(*) FILTER (WHERE mapped AND gallery AND NOT media_pending) AS terminal,
 count(*) FILTER (WHERE NOT (mapped AND gallery AND NOT media_pending)
   AND retry_until IS NULL) AS eligible,
 count(*) FILTER (WHERE NOT (mapped AND gallery AND NOT media_pending)
   AND retry_until IS NOT NULL) AS delayed,
 min(ingested_at) FILTER (WHERE NOT (mapped AND gallery AND NOT media_pending)
   AND retry_until IS NULL) AS oldest_due
FROM delivery
"""
