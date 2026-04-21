# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Neural-symbolic clinical decision support system for hypertension assessment. The "neural" component (LLM integration) is a planned extension — the current implementation is purely rule-based (symbolic). The pipeline has two independent stages.

## Running Tests

```bash
# Stage 1 — blood pressure measurement classification
python test/symbolic_test.py --stage stage1 --json data/temp/stage1_hbpm_sample.json

# Stage 2 — comprehensive cardiovascular risk assessment
python test/symbolic_test.py --stage stage2 --json data/temp/stage2_sample_input.json

# Regenerate synthetic dataset
python scripts/generate_hypertension_data.py
```

No package manager or build step is required. Dependencies are implicit (`pandas`, standard library).

## Architecture

Two-stage pipeline, each stage is independently invocable via the public API in `services/symbolic/__init__.py`:

- `run_symbolic_pipeline(df)` — Stage 1 entry point (takes a pandas DataFrame)
- `run_stage2_assessment(payload_dict_or_path)` — Stage 2 entry point (accepts dict or JSON file path)

**Stage 1** (`services/symbolic/stage1_measurement_classification/`): Reads raw BP measurements (home/clinic/ABPM sources), applies YAML-defined thresholds from `data/rules/`, aggregates per-patient, and outputs phenotype + BP stage classification.

**Stage 2** (`services/symbolic/stage2_comprehensive_assessment/`): Accepts a structured patient profile JSON, runs modular risk logic across `risk_classification.py`, `explanation_builder.py`, `recommendation_builder.py`, and `confidence_calculator.py`, then returns a unified risk assessment object.

**Key architectural constraint**: BP classification thresholds live in `data/rules/bp_interpretation_d1.yaml`, not in Python code. Changes to clinical thresholds should go there, not in `scoring/`.

## Input/Output Formats

Stage 1 CSV input columns: `datetime, patient_id, source, systolic, diastolic`

Stage 2 JSON input top-level keys: `patientInfo`, `cardiovascularRiskFactors`, `targetOrganDamage`, `comorbidities`

Sample inputs for both stages are in `data/temp/`.
