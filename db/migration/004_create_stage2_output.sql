-- OUTPUT Stage 2: cardiovascular risk assessment result
CREATE TABLE IF NOT EXISTS risk_assessments (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    classification_id UUID NOT NULL REFERENCES clinical_classifications(id) ON DELETE CASCADE,
    patient_id        UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    risk_level        VARCHAR(20),
    rule_version      VARCHAR(50),
    created_at        TIMESTAMP NOT NULL DEFAULT NOW()
);

-- OUTPUT Stage 2: human-readable reasoning for risk assessment
CREATE TABLE IF NOT EXISTS risk_reasonings (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_assessment_id UUID NOT NULL REFERENCES risk_assessments(id) ON DELETE CASCADE,
    patient_id         UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    explanation        TEXT,
    recommendation     TEXT,
    confidence         VARCHAR(20),
    rule_version       VARCHAR(50),
    created_at         TIMESTAMP NOT NULL DEFAULT NOW()
);
