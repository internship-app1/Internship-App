-- Promote job category from job_metadata JSON blob to a first-class indexed column.
-- Safe to re-run (IF NOT EXISTS / DO NOTHING guards).

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS category VARCHAR(50);

CREATE INDEX IF NOT EXISTS ix_jobs_category ON jobs (category);

-- Backfill from the existing JSON blob for rows already stamped by
-- backfill_categories.py or the ATS crawler normalizer.
UPDATE jobs
SET category = job_metadata::json ->> 'category'
WHERE category IS NULL
  AND job_metadata IS NOT NULL
  AND job_metadata::json ->> 'category' IS NOT NULL;
