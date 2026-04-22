# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Neural-symbolic clinical decision support system for hypertension assessment. The pipeline has two independent rule-based stages exposed via a FastAPI HTTP API. An LLM (vLLM, Cloudflare-tunnelled) is wired as a dependency for future neural augmentation.

## Running the API

```bash
# Development (auto-reload)
duy_venv/bin/uvicorn main:app --reload

# Production
duy_venv/bin/python main.py
```

Copy `.env.example` to `.env` and adjust values before starting.

## Running Tests

The primary test runner is `scripts/symbolic_test.sh`. It accepts `--json` and `--stage` flags.

```bash
# Stage 1 — blood pressure measurement classification
bash scripts/symbolic_test.sh --stage stage1 --json data/temp/stage1_test_cases/<case>.json

# Stage 2 — comprehensive cardiovascular risk assessment
bash scripts/symbolic_test.sh --stage stage2 --json data/temp/stage2_test_cases/<case>.json

# Regenerate synthetic dataset
duy_venv/bin/python scripts/generate_hypertension_data.py
```

Sample inputs live under `data/temp/`:
- `data/temp/stage1_test_cases/` — 10 Stage 1 cases (case01–case10) + `sample_home_bp_week.json`
- `data/temp/stage2_test_cases/` — 10 Stage 2 cases (case01–case10, rule-based risk scenarios)

## Architecture

```
main.py                         FastAPI entry point — lifespan, DI, routers
configs/config.py               Pydantic-settings — secrets only (.env); exports `settings`, `config`, `ai_config`
configs/config.yaml             System config: app, server, cors, database, logging (non-secret)
configs/ai_config.yaml          AI config: LLM base_url, timeout, model profiles, task params (non-secret)
configs/rules_config.yaml       Rule versioning: maps stage → active version → rulebook YAML path
api/routes/health.py            GET /health
api/routes/assessment.py        POST /api/v1/stage1, POST /api/v1/stage2
integrations/llms/vllm.py       Async vLLM client (OpenAI-compatible); create_llm(profile=)
middleware/error_handler.py     Global exception → 500 JSON
middleware/logging.py           Per-request timing log
services/clinic_engine/         Rule-based engine (renamed from services/symbolic)
  stage1_measurement_classification/
  stage2_comprehensive_assessment/
  pipeline/                     Orchestrator (merged from services/pipeline)
services/observability/         Langfuse stub (replace with real client)
utils/logger.py                 setup_logging()
```

Two-stage pipeline, each stage is independently invocable via the public API in `services/clinic_engine/__init__.py`:

- `run_symbolic_pipeline(df)` — Stage 1 entry point (takes a pandas DataFrame)
- `run_stage2_assessment(payload_dict_or_path)` — Stage 2 entry point (accepts dict or JSON file path)

**Stage 1** (`services/clinic_engine/stage1_measurement_classification/`): Reads raw BP measurements (home/clinic/ABPM sources), applies YAML-defined thresholds from `data/rules/`, aggregates per-patient, and outputs phenotype + BP stage classification.

**Stage 2** (`services/clinic_engine/stage2_comprehensive_assessment/`): Accepts a structured patient profile JSON, runs modular risk logic across `risk_classification.py`, `explanation_builder.py`, `recommendation_builder.py`, and `confidence_calculator.py`, then returns a unified risk assessment object.

**Key architectural constraint**: BP classification thresholds live in `data/rules/bp_interpretation_d1.yaml`, not in Python code. Changes to clinical thresholds should go there, not in `scoring/`.

## Input/Output Formats

Stage 1 CSV input columns: `datetime, patient_id, source, systolic, diastolic`

Stage 2 JSON input top-level keys: `patientInfo`, `cardiovascularRiskFactors`, `targetOrganDamage`, `comorbidities`

HTTP API:
- `POST /api/v1/stage1` — body: `{"readings": [{...BP reading...}]}`
- `POST /api/v1/stage2` — body: stage2 JSON object
- `GET /health` — liveness + DB + LLM URL

Sample inputs for both stages are in `data/temp/`.

## LLM Integration

`integrations/llms/vllm.py` wraps the vLLM server at `https://sim-examples-collect-jets.trycloudflare.com` (OpenAI-compatible `/v1/chat/completions`). Use `create_llm(profile="primary"|"classifier"|"summarizer")` — profiles map to model names in `_PROFILES`. The client is injected via `request.app.state.llm` in route handlers.
