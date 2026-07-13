-- Migration: add an optional `depth` column (microns driven) to the RF tables.
--
-- Receptive fields may be mapped at depths/locations other than the final
-- recording location. `depth` records the microdrive depth in microns for each
-- saved RF. It defaults to 0, which denotes the final/reference recording
-- location, so existing rows keep their original meaning after migration.
--
-- tstamp remains the primary key (unique), so depth is not part of any key.
--
-- Run this against the template database AND every existing experiment database
-- that already contains RFInfo / RFObjectData. Standard MySQL does not support
-- "ADD COLUMN IF NOT EXISTS", so run once per database; re-running on an
-- already-migrated database will error on the duplicate column (safe to ignore).

ALTER TABLE RFInfo      ADD COLUMN depth INT NOT NULL DEFAULT 0;
ALTER TABLE RFObjectData ADD COLUMN depth INT NOT NULL DEFAULT 0;
