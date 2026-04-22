-- OUTPUT Stage 1: top-level classification result per BP run
CREATE TABLE IF NOT EXISTS clinical_classifications (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id    UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    bp_run_id     UUID,
    bp_category   VARCHAR(50),
    bp_stage      VARCHAR(50),
    phenotype     VARCHAR(50),
    source_used   VARCHAR(20),
    source_value  VARCHAR(50),
    confidence    VARCHAR(20),
    flags         JSONB,
    rule_version  VARCHAR(50),
    created_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

-- OUTPUT Stage 1: per-source usability flags
CREATE TABLE IF NOT EXISTS classification_usability (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    classification_id   UUID NOT NULL REFERENCES clinical_classifications(id) ON DELETE CASCADE,
    patient_id          UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    clinic_usable       BOOLEAN,
    home_usable         BOOLEAN,
    abpm_usable         BOOLEAN,
    bp_category_usable  BOOLEAN,
    bp_stage_usable     BOOLEAN,
    phenotype_usable    BOOLEAN,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- OUTPUT Stage 1: per-source measurement quality evaluation
CREATE TABLE IF NOT EXISTS measurement_evaluation (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id        UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    classification_id UUID NOT NULL REFERENCES clinical_classifications(id) ON DELETE CASCADE,
    source            VARCHAR(20),
    quality_score     FLOAT,
    quality_level     VARCHAR(20),
    usable            BOOLEAN,
    flags             JSONB,
    details           JSONB,
    created_at        TIMESTAMP NOT NULL DEFAULT NOW()
);

-- OUTPUT Stage 1: human-readable reasoning (explanation + recommendation)
CREATE TABLE IF NOT EXISTS clinical_reasonings (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    classification_id UUID NOT NULL REFERENCES clinical_classifications(id) ON DELETE CASCADE,
    patient_id        UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    explanation       TEXT,
    recommendation    TEXT,
    confidence        VARCHAR(20),
    created_at        TIMESTAMP NOT NULL DEFAULT NOW()
);
