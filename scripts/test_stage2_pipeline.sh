#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CASE_DIR="$ROOT_DIR/temp/stage2_test_cases"

if [[ ! -d "$CASE_DIR" ]]; then
  echo "Missing test case directory: $CASE_DIR"
  exit 1
fi

echo "Running Stage 2 pipeline for JSON files in: $CASE_DIR"
python - <<'PY'
import json
from pathlib import Path

from services.clinic_engine.stage2_comprehensive_assessment.assessment import run_stage2_assessment

root = Path.cwd()
case_dir = root / "temp" / "stage2_test_cases"
files = sorted(case_dir.glob("*.json"))

if not files:
    raise SystemExit(f"No JSON files found in {case_dir}")

for path in files:
    result = run_stage2_assessment(path)
    print(f"\n=== {path.name} ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
PY
