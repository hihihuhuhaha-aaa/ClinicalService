from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

BPSource = Literal["OBPM", "HBPM", "ABPM"]


def _time_based_period(timestamp: datetime) -> str:
    hour = timestamp.hour
    if 5 <= hour < 10:
        return "morning"
    if 10 <= hour < 16:
        return "day"
    if 16 <= hour < 22:
        return "evening"
    return "night"


def _sample_bp(mean_sys: float, mean_dia: float, jitter: float = 6.0) -> tuple[float, float]:
    systolic = np.clip(np.random.normal(mean_sys, jitter), 80, 240)
    diastolic = np.clip(np.random.normal(mean_dia, jitter * 0.7), 50, 140)
    return float(round(systolic, 1)), float(round(diastolic, 1))


def _build_abpm_day_profile(start_time: datetime, base_sys: float, base_dia: float, pattern: str, clean: bool) -> list[dict]:
    records = []
    for step in range(24 * 2):
        timestamp = start_time + timedelta(minutes=30 * step)
        period = _time_based_period(timestamp)

        if period == "morning":
            sys_offset = 10.0 if pattern in {"non_dipper", "reverse_dipper"} else 20.0
            dia_offset = 6.0 if pattern in {"non_dipper", "reverse_dipper"} else 10.0
        elif period == "night":
            if pattern == "extreme_dipper":
                sys_offset = -20.0
                dia_offset = -12.0
            elif pattern == "dipper":
                sys_offset = -12.0
                dia_offset = -8.0
            elif pattern == "non_dipper":
                sys_offset = -4.0
                dia_offset = -3.0
            else:
                sys_offset = 4.0
                dia_offset = 2.0
        else:
            sys_offset = 0.0
            dia_offset = 0.0

        base_sys_time = base_sys + sys_offset
        base_dia_time = base_dia + dia_offset
        systolic, diastolic = _sample_bp(base_sys_time, base_dia_time, jitter=5.0)

        if not clean and random.random() < 0.06:
            systolic += random.choice([-30, -20, 20, 25])
            diastolic += random.choice([-18, -12, 12, 15])

        if not clean and random.random() < 0.08:
            systolic = np.nan
            diastolic = np.nan

        records.append(
            {
                "datetime": timestamp,
                "day_period": period,
                "systolic": systolic,
                "diastolic": diastolic,
                "source": "ABPM",
                "is_missing": np.isnan(systolic) or np.isnan(diastolic),
                "is_artifact": bool(not clean and random.random() < 0.06),
                "noise_level": "high" if not clean and random.random() < 0.12 else "low",
            }
        )
    return records


def _build_clinic_home_profile(start_time: datetime, count: int, source: BPSource, base_sys: float, base_dia: float, clean: bool) -> list[dict]:
    records = []
    interval = 1 if source == "OBPM" else 0.5
    for step in range(count):
        timestamp = start_time + timedelta(days=step * interval, hours=8 if source == "OBPM" else 7 + (step % 3) * 2)
        period = _time_based_period(timestamp)
        systolic, diastolic = _sample_bp(base_sys, base_dia, jitter=8.0 if source == "OBPM" else 6.0)
        if not clean and source == "HBPM" and random.random() < 0.1:
            systolic += random.choice([-18, 18, 20, 22])
            diastolic += random.choice([-12, 12, 14, 15])
        if not clean and source == "HBPM" and random.random() < 0.06:
            systolic = np.nan
            diastolic = np.nan
        records.append(
            {
                "datetime": timestamp,
                "day_period": period,
                "systolic": systolic,
                "diastolic": diastolic,
                "source": source,
                "is_missing": np.isnan(systolic) or np.isnan(diastolic),
                "is_artifact": bool(not clean and random.random() < 0.08),
                "noise_level": "high" if not clean and random.random() < 0.12 else "low",
            }
        )
    return records


def _patient_summary(patient_id: str, records: list[dict], phenotype: str, stage: str, night_pattern: str) -> list[dict]:
    df = pd.DataFrame(records)
    avg_morning = df[df["day_period"] == "morning"][['systolic', 'diastolic']].mean()
    avg_night = df[df["day_period"] == "night"][['systolic', 'diastolic']].mean()
    morning_hypertension = bool(avg_morning['systolic'] >= 135 or avg_morning['diastolic'] >= 85)
    morning_surge = bool((avg_morning['systolic'] - avg_night['systolic']) >= 20 or (avg_morning['diastolic'] - avg_night['diastolic']) >= 10)

    for record in records:
        record.update(
            {
                "patient_id": patient_id,
                "phenotype": phenotype,
                "tha_stage": stage,
                "night_pattern": night_pattern,
                "morning_hypertension": morning_hypertension,
                "morning_surge": morning_surge,
            }
        )
    return records


def generate_synthetic_hypertension_data(output_path: Path | str, seed: int = 42) -> pd.DataFrame:
    random.seed(seed)
    np.random.seed(seed)
    now = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)

    patients = [
        {
            "patient_id": "symbolic_p001",
            "sources": ["OBPM", "HBPM"],
            "clean": True,
            "base_sys": 150,
            "base_dia": 95,
            "phenotype": "sustained",
            "stage": "stage_2",
            "night_pattern": "dipper",
            "rows": 120,
        },
        {
            "patient_id": "symbolic_p002",
            "sources": ["HBPM", "ABPM"],
            "clean": True,
            "base_sys": 135,
            "base_dia": 82,
            "phenotype": "masked",
            "stage": "stage_1",
            "night_pattern": "non_dipper",
            "rows": 120,
        },
        {
            "patient_id": "symbolic_p005",
            "sources": ["OBPM", "ABPM"],
            "clean": True,
            "base_sys": 142,
            "base_dia": 88,
            "phenotype": "white_coat",
            "stage": "stage_2",
            "night_pattern": "extreme_dipper",
            "rows": 120,
        },
        {
            "patient_id": "neural_p003",
            "sources": ["ABPM"],
            "clean": False,
            "base_sys": 148,
            "base_dia": 92,
            "phenotype": "white_coat",
            "stage": "stage_2",
            "night_pattern": "reverse_dipper",
            "rows": 150,
        },
        {
            "patient_id": "neural_p004",
            "sources": ["HBPM"],
            "clean": False,
            "base_sys": 138,
            "base_dia": 86,
            "phenotype": "prehypertension",
            "stage": "elevated",
            "night_pattern": "non_dipper",
            "rows": 150,
        },
        {
            "patient_id": "neural_p006",
            "sources": ["ABPM", "HBPM"],
            "clean": False,
            "base_sys": 155,
            "base_dia": 98,
            "phenotype": "sustained",
            "stage": "stage_2",
            "night_pattern": "dipper",
            "rows": 160,
        },
    ]

    all_records: list[dict] = []
    for patient in patients:
        start_time = now - timedelta(days=patient["rows"] // 4)
        patient_records: list[dict] = []
        for source in patient["sources"]:
            if source == "ABPM":
                patient_records.extend(
                    _build_abpm_day_profile(start_time, patient["base_sys"], patient["base_dia"], patient["night_pattern"], patient["clean"])
                )
            else:
                patient_records.extend(
                    _build_clinic_home_profile(start_time, patient["rows"], source, patient["base_sys"], patient["base_dia"], patient["clean"])
                )
        all_records.extend(
            _patient_summary(
                patient["patient_id"],
                patient_records,
                patient["phenotype"],
                patient["stage"],
                patient["night_pattern"],
            )
        )

    df = pd.DataFrame(all_records)
    df = df.sort_values(["patient_id", "datetime"]).reset_index(drop=True)
    df["source"] = df["source"].astype(str)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def load_hypertension_data(csv_path: Path | str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, parse_dates=["datetime"])
    return df
