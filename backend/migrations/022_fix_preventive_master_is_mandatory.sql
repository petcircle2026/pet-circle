-- Migration 022: Fix is_mandatory flags on preventive_master
--
-- Puppy series doses (DHPPi 1st/2nd/3rd Dose, Puppy Booster) were seeded
-- without is_mandatory=TRUE. Without it the care plan guard skips them when
-- there is no completion date, so they never appear as recommended items for
-- puppies.
--
-- Kennel Cough and CCoV were seeded without is_mandatory=FALSE (defaulted to
-- false, so no change needed), but the seeder comment said "always shown" —
-- that was wrong. No DB change needed for those two; only the seeder comment
-- and explicit false flag were corrected.

UPDATE preventive_master
SET is_mandatory = TRUE
WHERE item_name IN (
    'DHPPi 1st Dose',
    'DHPPi 2nd Dose',
    'DHPPi 3rd Dose',
    'Puppy Booster'
)
AND species = 'dog';
