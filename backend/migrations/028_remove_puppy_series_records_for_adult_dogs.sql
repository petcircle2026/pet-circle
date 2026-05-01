-- Migration 028: Remove puppy-series preventive records seeded for adult dogs
--
-- The seeder previously created not_started records for DHPPi 1st/2nd/3rd Dose
-- and Puppy Booster for ALL dogs regardless of age. For dogs older than 6 months
-- these phantom records pollute the care plan and GPT query context, making it
-- appear as if puppy vaccines are outstanding when they are age-inappropriate.
--
-- Safe to delete: these records have status='not_started' and no last_done_date,
-- meaning they carry no actual health history. Adult dogs get their vaccination
-- history through document upload (which creates records with last_done_date set).

DELETE FROM preventive_records pr
USING preventive_master pm, pets p
WHERE pr.preventive_master_id = pm.id
  AND pr.pet_id = p.id
  AND pr.status = 'not_started'
  AND pr.last_done_date IS NULL
  AND pm.recurrence_days >= 36500
  AND p.dob IS NOT NULL
  AND (CURRENT_DATE - p.dob) > 180  -- older than 6 months
  AND p.species = 'dog';
