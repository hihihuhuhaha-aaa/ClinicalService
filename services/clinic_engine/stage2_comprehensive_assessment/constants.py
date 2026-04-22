"""Constants for Stage 2 comprehensive assessment."""

BP_STAGE_KEYS = ["bp_stage", "bpStage", "bp_stage_label"]

BP_STAGE_VALUES_MEDIUM = ["stage2", "stage_2", "hypertension"]

COMORBIDITIES_FIELDS = ["cvd", "stroke", "ckd"]
FAMILY_HISTORY_FIELDS = ["directHypertension", "earlyASCVD"]

TARGET_ORGAN_DAMAGE_FIELDS = [
    "leftVentricularHypertrophy",
    "brainDamage",
    "heartDamage",
    "kidneyDamage",
    "vascularDamage",
    "ckdStage3",
    "pulsePressureOver60",
    "ckdStage4",
    "ckdStage5",
    "ckdStageIV",
    "ckdStageV",
]

MAIN_RISK_FACTOR_FIELDS = [
    "ageOver65",
    "male",
    "heartRateOver80",
    "overweight",
    "highLDLOrTriglyceride",
    "earlyMenopause",
    "menopause",
    "smoking",
    "sedentaryLifestyle",
]

SPECIAL_RISK_FACTOR_FIELDS = ["diabetes", "familialHypercholesterolemia"]

HMOD_FIELDS = [
    "leftVentricularHypertrophy",
    "brainDamage",
    "heartDamage",
    "kidneyDamage",
    "vascularDamage",
    "pulsePressureOver60",
    "ckdStage3",
]

HIGH_RISK_FIELDS = [
    "coronaryArteryDisease",
    "heartFailure",
    "stroke",
    "peripheralVascularDisease",
    "atrialFibrillation",
    "ckdStage4",
    "ckdStage5",
]

HIGH_RISK_CONDITIONS = HIGH_RISK_FIELDS
