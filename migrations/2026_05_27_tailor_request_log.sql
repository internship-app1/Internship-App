-- Documentation only. This table is auto-created by Base.metadata.create_all()
-- at startup (job_database.py via job_cache.py). This file is a manual
-- recovery artifact — do NOT wire it into the deploy pipeline.

CREATE TABLE IF NOT EXISTS tailor_request_log (
    id          SERIAL PRIMARY KEY,
    user_id     VARCHAR(255) NOT NULL,
    requested_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
    job_title   VARCHAR(500),
    company     VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS idx_tailor_user_time
    ON tailor_request_log (user_id, requested_at);
