-- INPUT: raw blood pressure records (Stage 1 & Stage 2)
CREATE TABLE IF NOT EXISTS bp_records (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id       UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    systolic         INT NOT NULL,
    diastolic        INT NOT NULL,
    source           VARCHAR(20),
    day_period       VARCHAR(20),
    position         VARCHAR(20),
    rested_minutes   FLOAT,
    device_type      VARCHAR(50),
    device_validated BOOLEAN,
    status           VARCHAR(20),
    severity         VARCHAR(20),
    created_at       TIMESTAMP NOT NULL DEFAULT NOW()
);

-- INPUT: structured clinical facts (Stage 2)
CREATE TABLE IF NOT EXISTS clinical_facts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id  UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    fact_group  VARCHAR(50),
    fact_key    VARCHAR(100),
    value       BOOLEAN,
    status      VARCHAR(20),
    severity    VARCHAR(20),
    source      VARCHAR(50),
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
