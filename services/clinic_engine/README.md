# Symbolic Pipeline - Hypertension Assessment

Neural-Symbolic LLM baseline cho hypertension assessment với 2 stages: measurement classification và comprehensive risk assessment.

## Overview

Pipeline sử dụng kết hợp neural (LLM) và symbolic (rule-based) approaches để:
- **Stage 1**: Phân loại measurements và xác định BP categories/stages
- **Stage 2**: Comprehensive risk assessment dựa trên patient profile

## Stage 1: Measurement Classification

### Rules & Flow
- **Input**: Raw BP measurements từ CSV (home, clinic, ABPM)
- **Rules**: YAML-based thresholds cho từng measurement source
- **Flow**:
  1. Aggregate measurements theo patient/source
  2. Quality assessment cho từng source
  3. Apply BP category rules (Normal/Elevated/Hypertension)
  4. Apply BP stage rules (Stage 1/2)
  5. Classify phenotype (Sustained/White Coat/Masked)

### Input Format
```csv
datetime,patient_id,source,systolic,diastolic
2024-01-01 08:00,patient_001,home,135,85
2024-01-01 09:00,patient_001,home,140,88
```

### Output Example
```json
{
  "patient_summary": [
    {
      "patient_id": "patient_001",
      "phenotype": "sustained_hypertension",
      "tha_type": "clinic",
      "bp_stage": "stage_1",
      "quality_score": 0.85
    }
  ],
  "patient_count": 1,
  "phenotypes": ["sustained_hypertension"],
  "tha_types": ["clinic"],
  "tha_stages": ["stage_1"]
}
```

## Stage 2: Comprehensive Risk Assessment

### Rules & Flow
- **Input**: Patient profile JSON với cardiovascular risk factors
- **Rules**: Modular logic cho risk classification
- **Flow**:
  1. Data processing & normalization
  2. Risk level classification (Low/Medium/High)
  3. Generate explanation
  4. Build treatment recommendations
  5. Calculate confidence level

### Input Format
```json
{
  "patientInfo": {
    "age": 62,
    "gender": "female",
    "bmi": 28.4
  },
  "cardiovascularRiskFactors": {
    "diabetes": true,
    "smoking": false,
    "overweight": true
  },
  "targetOrganDamage": {
    "leftVentricularHypertrophy": true,
    "ckdStage3": true
  },
  "comorbidities": {
    "cvd": false,
    "stroke": false,
    "ckd": true
  }
}
```

### Output Example
```json
{
  "risk_level": "medium",
  "recommendation": "Recommend lifestyle modification and careful monitoring...",
  "explanation": "There are 5 additional cardiovascular risk factor(s)...",
  "confidence": "medium"
}
```

## Usage
### Unified Test
```bash
# Stage 1
bash scripts/symbolic_test.sh --stage stage1 --json <path/to/stage1_input.json>

# Stage 2
bash scripts/symbolic_test.sh --stage stage2 --json temp/stage2_test_cases/case01_rule1_low_pre120.json
```

> **Note**: Unified test script `scripts/symbolic_test.sh` handles both stages.

## Architecture

```
services/symbolic/
├── stage1_measurement_classification/
│   ├── pipeline.py          # Main pipeline
│   ├── summary.py           # Patient aggregation
│   ├── rules/               # YAML rulebook
│   └── scoring/             # Classification logic
└── stage2_comprehensive_assessment/
    ├── assessment.py        # Main orchestrator
    ├── constants.py         # All constants
    ├── data_processing.py   # Data normalization
    ├── risk_classification.py # Risk logic
    ├── explanation_builder.py # Explanations
    ├── recommendation_builder.py # Recommendations
    └── confidence_calculator.py # Confidence scoring

scripts/
├── generate_hypertension_data.py  # Data generation utility
└── symbolic_test.sh               # Unified stage1/stage2 runner
```