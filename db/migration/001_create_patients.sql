CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS patients (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gender      VARCHAR(10),
    birth_year  INT,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
