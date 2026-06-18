-- Find experiment_ids in ClusterInfo that have a `_ga` version
-- but NO matching `_isogabor` version.
--
-- Experiment IDs look like: <base>_<type>, e.g.
--   260617_0_ga
--   260617_0_isogabor
-- The "base" is everything before the trailing suffix
-- (260617_0 in the example above).

SELECT DISTINCT ga.experiment_id AS ga_experiment_id,
                LEFT(ga.experiment_id, LENGTH(ga.experiment_id) - LENGTH('_ga')) AS base
FROM ClusterInfo ga
WHERE ga.experiment_id LIKE '%\_ga'
  AND NOT EXISTS (
      SELECT 1
      FROM ClusterInfo iso
      WHERE iso.experiment_id =
            CONCAT(LEFT(ga.experiment_id, LENGTH(ga.experiment_id) - LENGTH('_ga')), '_isogabor')
  )
ORDER BY ga.experiment_id;
