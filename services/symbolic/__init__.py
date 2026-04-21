"""Symbolic pipeline package."""

try:
    from .stage1_measurement_classification.scoring.classification import (
        classify_abpm_pattern,
        classify_hypertension_phenotype,
        classify_tha_stage,
        classify_tha_type,
    )
    from .stage1_measurement_classification.data.dataset import (
        generate_synthetic_hypertension_data,
        load_hypertension_data,
    )
    from .stage1_measurement_classification.pipeline import run_symbolic_pipeline
    from .stage1_measurement_classification.summary import summarize_patient_rules
except ImportError:
    classify_abpm_pattern = None
    classify_hypertension_phenotype = None
    classify_tha_stage = None
    classify_tha_type = None
    generate_synthetic_hypertension_data = None
    load_hypertension_data = None
    run_symbolic_pipeline = None
    summarize_patient_rules = None

from .stage2_comprehensive_assessment import load_patient_input, run_stage2_assessment
