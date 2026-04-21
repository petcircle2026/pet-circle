-- Add last_visit_date to contacts so vet visit date is self-contained.
-- Backfill from the linked document's event_date where available.

ALTER TABLE contacts
  ADD COLUMN IF NOT EXISTS last_visit_date DATE;

UPDATE contacts
SET last_visit_date = documents.event_date
FROM documents
WHERE contacts.document_id = documents.id
  AND contacts.last_visit_date IS NULL
  AND documents.event_date IS NOT NULL;
