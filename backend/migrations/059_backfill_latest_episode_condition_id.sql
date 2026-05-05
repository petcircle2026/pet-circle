-- Migration 059: Backfill latest_episode_condition_id on aggregated_conditions.
--
-- Root cause: migration 056 added the column with a NULL default but did not
-- populate existing rows. Any pet whose documents were extracted before 056 ran
-- has aggregated_conditions rows with latest_episode_condition_id = NULL, which
-- causes the precompute JOIN and display-filter queries to return no source/vet_resolved.
--
-- Fix: for each aggregated_conditions row where the FK is still NULL, set it to
-- the most-recently-diagnosed active conditions row in that family.

UPDATE aggregated_conditions ac
SET    latest_episode_condition_id = (
           SELECT c.id
           FROM   conditions c
           WHERE  c.condition_family_id = ac.id
             AND  c.is_active = TRUE
           ORDER BY c.diagnosed_at DESC NULLS LAST,
                    c.created_at   DESC
           LIMIT  1
       )
WHERE  ac.latest_episode_condition_id IS NULL;
