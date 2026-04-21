from __future__ import annotations

from pathlib import Path

import pandas as pd

from .summary import summarize_patient_rules


def run_symbolic_pipeline(df: pd.DataFrame) -> dict[str, object]:
    df = df.copy()
    if "source" not in df.columns:
        raise ValueError("Input DataFrame must contain a 'source' column")

    patient_summary = summarize_patient_rules(df)
    return {
        "patient_summary": patient_summary,
        "patient_count": len(patient_summary),
        "phenotypes": patient_summary["phenotype"].unique().tolist(),
        "tha_types": patient_summary["tha_type"].unique().tolist(),
        "tha_stages": patient_summary["bp_stage"].unique().tolist(),
    }


def load_symbolic_dataset(csv_path: Path | str) -> pd.DataFrame:
    return pd.read_csv(csv_path, parse_dates=["datetime"])
