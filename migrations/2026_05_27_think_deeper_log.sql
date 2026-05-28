-- Documentation only. This table is auto-created by Base.metadata.create_all()
-- at startup (job_database.py:104 via job_cache.py:36). This file is a manual
-- recovery artifact — do NOT wire it into the deploy pipeline.

CREATE TABLE IF NOT EXISTS think_deeper_request_log (
    id          SERIAL PRIMARY KEY,
    user_id     VARCHAR(255) NOT NULL,
    requested_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
    resume_hash VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_think_deeper_user_time
    ON think_deeper_request_log (user_id, requested_at);
