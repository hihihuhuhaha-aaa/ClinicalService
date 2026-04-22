from __future__ import annotations

"""Patient summary builder for the symbolic pipeline.

This module aggregates raw measurement records into patient-level metrics,
computes per-source quality, and then applies symbolic classification.
"""

from datetime import timedelta

import pandas as pd

from .scoring.classification import (
    _build_source_summary,
    _source_available,
    classify_bp_category,
    classify_bp_stage,
    classify_phenotype,
)
from .scoring.quality import compute_abpm_quality, compute_clinic_quality, compute_home_quality


def _parse_datetime(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    return pd.to_datetime(series, errors="coerce")


def _uniform_or_unknown(series: pd.Series, unknown_value: str = "unknown") -> str | None:
    values = series.dropna().astype(str).str.strip()
    values = values[values != ""]
    if values.empty:
        return None
    unique_values = values.str.lower().unique()
    if len(unique_values) == 1:
        return str(unique_values[0])
    return unknown_value


def _iqr_outlier_count(series: pd.Series) -> int:
    numeric = series.dropna().astype(float)
    if len(numeric) < 4:
        return 0
    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return 0
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return int(((numeric < lower) | (numeric > upper)).sum())


def _select_clinic_average(group: pd.DataFrame) -> tuple[float | None, float | None, dict[str, object]]:
    """Select and aggregate the most recent clinic readings for a patient."""
    clinic = group[group["source"].astype(str).str.upper() == "OBPM"].copy()
    clinic["datetime"] = _parse_datetime(clinic["datetime"])
    readings_count = len(clinic)
    clinic = clinic.dropna(subset=["systolic", "diastolic"])
    if clinic.empty:
        return None, None, {
            "clinic_readings_count": readings_count,
            "clinic_missing": True,
            "clinic_rest_minutes": None,
        }

    clinic = clinic.sort_values("datetime", ascending=False).head(2)
    return (
        float(clinic["systolic"].mean()),
        float(clinic["diastolic"].mean()),
        {
            "clinic_readings_count": readings_count,
            "clinic_missing": False,
            "clinic_rest_minutes": clinic["rested_minutes"].dropna().astype(float).iloc[0]
            if "rested_minutes" in clinic.columns and clinic["rested_minutes"].notna().any()
            else None,
        },
    )


def _select_home_average(group: pd.DataFrame) -> tuple[float | None, float | None, dict[str, object]]:
    """Aggregate home blood pressure readings over the last 7 days."""
    home = group[group["source"].astype(str).str.upper() == "HBPM"].copy()
    home["datetime"] = _parse_datetime(home["datetime"])
    home = home.dropna(subset=["systolic", "diastolic", "datetime"])
    if home.empty:
        return None, None, {
            "home_available": False,
            "home_quality_flags": [],
        }

    last_date = home["datetime"].max().date()
    start_date = (pd.Timestamp(last_date) - pd.Timedelta(days=6)).date()
    home = home[
        (home["datetime"].dt.date >= start_date)
        & (home["datetime"].dt.date <= last_date)
    ]

    # Drop the first day in the 7-day window to reduce day-1 bias.
    if not home.empty:
        first_day_in_window = home["datetime"].dt.date.min()
        home = home[home["datetime"].dt.date > first_day_in_window]

    home = home.dropna(subset=["systolic", "diastolic"])
    if home.empty:
        return None, None, {
            "home_available": False,
            "home_quality_flags": [],
        }

    home_dates = home["datetime"].dt.date
    days_with_morning = len(home[home["day_period"] == "morning"]["datetime"].dt.date.unique())
    days_with_evening = len(home[home["day_period"] == "evening"]["datetime"].dt.date.unique())
    days_with_both_sessions = len(
        home.groupby(home["datetime"].dt.date)["day_period"].apply(lambda periods: {"morning", "evening"}.issubset(set(periods)))
        .loc[lambda x: x]
    )
    session_counts = home.groupby([home["datetime"].dt.date, home["day_period"].fillna("unknown")]).size()
    avg_readings_per_session = float(session_counts.mean()) if not session_counts.empty else 0.0
    pct_sessions_with_pairs = float((session_counts >= 2).mean()) if not session_counts.empty else 0.0
    pairs_per_session = avg_readings_per_session
    pattern = "random_only" if not days_with_morning and not days_with_evening else "no_time_pattern" if home["day_period"].isnull().all() else "normal"

    sys_values = home["systolic"].astype(float)
    dia_values = home["diastolic"].astype(float)
    std_sys = float(sys_values.std(ddof=0)) if len(sys_values) > 1 else 0.0
    std_dia = float(dia_values.std(ddof=0)) if len(dia_values) > 1 else 0.0
    sys_min = float(sys_values.min())
    sys_max = float(sys_values.max())
    dia_min = float(dia_values.min())
    dia_max = float(dia_values.max())
    sys_outlier_count = _iqr_outlier_count(sys_values)
    dia_outlier_count = _iqr_outlier_count(dia_values)
    outlier_count = max(sys_outlier_count, dia_outlier_count)

    quality_context = {
        "home_available": True,

        # coverage
        "num_days": len(home_dates.unique()),
        "days_with_morning": days_with_morning,
        "days_with_evening": days_with_evening,
        "days_with_both_sessions": days_with_both_sessions,
        "has_morning": days_with_morning > 0,
        "has_evening": days_with_evening > 0,

        # pattern / session quality
        "pairs_per_session": pairs_per_session,
        "avg_readings_per_session": avg_readings_per_session,
        "pct_sessions_with_pairs": pct_sessions_with_pairs,
        "pattern": pattern,

        # variability / dispersion metrics
        "std_sys": std_sys,
        "std_dia": std_dia,
        "range": {
            "sys_min": sys_min,
            "sys_max": sys_max,
            "sys_range": sys_max - sys_min,
            "dia_min": dia_min,
            "dia_max": dia_max,
            "dia_range": dia_max - dia_min,
        },
        "outlier": {
            "method": "iqr_1.5",
            "sys_outlier_count": sys_outlier_count,
            "dia_outlier_count": dia_outlier_count,
            "outlier_count": outlier_count,
            "has_outlier": outlier_count > 0,
        },

        # device quality
        "device_validated": bool(home["device_validated"].dropna().astype(bool).all()) if "device_validated" in home.columns and home["device_validated"].notna().any() else None,
        "device_type": _uniform_or_unknown(home["device_type"]) if "device_type" in home.columns else None,

        # measurement condition
        "position": _uniform_or_unknown(home["position"]) if "position" in home.columns else None,
        "rested_minutes": float(home["rested_minutes"].dropna().astype(float).min()) if "rested_minutes" in home.columns and home["rested_minutes"].notna().any() else None,

        # completeness
        "all_readings_have_sys_dia_timestamp": bool(home["systolic"].notna().all() and home["diastolic"].notna().all() and home["datetime"].notna().all()),
        "missing_timestamp_only": bool(home["datetime"].isna().any() and home["systolic"].notna().all() and home["diastolic"].notna().all()),
        "missing_some_sys_or_dia": bool(home["systolic"].isna().any() or home["diastolic"].isna().any()),
        "many_unusable_readings": float(home["systolic"].isna().mean() + home["diastolic"].isna().mean()) > 0.3,
    }

    session_averages = home.groupby([home["datetime"].dt.date, home["day_period"].fillna("unknown")])[["systolic", "diastolic"]].mean()
    return (
        float(session_averages["systolic"].mean()),
        float(session_averages["diastolic"].mean()),
        quality_context,
    )


def _select_abpm_average(group: pd.DataFrame) -> tuple[float | None, float | None, dict[str, object]]:
    """Aggregate ABPM data over the latest 24-hour window for a patient."""
    abpm = group[group["source"].astype(str).str.upper() == "ABPM"].copy()
    abpm["datetime"] = _parse_datetime(abpm["datetime"])
    abpm = abpm.dropna(subset=["systolic", "diastolic", "datetime"])
    if abpm.empty:
        return None, None, {
            "abpm_24h_available": False,
            "duration_hours": 0.0,
            "valid_readings": 0.0,
            "expected_readings": 1,
            "has_day_data": False,
            "has_night_data": False,
            "day_interval_minutes": None,
            "night_interval_minutes": None,
            "minor_deviation_from_target": False,
            "major_deviation_from_target": False,
            "interval_unknown": True,
            "all_readings_have_sys_dia_timestamp_period": False,
            "missing_period_tag_only": False,
            "missing_some_sys_or_dia_or_timestamp": False,
            "many_unusable_readings": False,
            "activity_log": None,
        }

    max_ts = abpm["datetime"].max()
    window_start = max_ts - timedelta(hours=24)
    window = abpm[(abpm["datetime"] > window_start) & (abpm["datetime"] <= max_ts)]
    if window.empty:
        window = abpm[abpm["datetime"].dt.date == max_ts.date()]

    valid_count = len(window)
    duration_hours = (window["datetime"].max() - window["datetime"].min()).total_seconds() / 3600 if valid_count > 1 else 0.0
    expected_readings = max(int(round(duration_hours * 2)), 1)
    valid_readings = int(window[["systolic", "diastolic"]].notna().all(axis=1).sum())
    has_day_data = bool(window[window["day_period"].isin(["morning", "day", "evening"])] .shape[0])
    has_night_data = bool(window[window["day_period"] == "night"].shape[0])

    def _avg_interval(period_name: str) -> float | None:
        subset = window[window["day_period"] == period_name].sort_values("datetime")
        if len(subset) < 2:
            return None
        diffs = subset["datetime"].diff().dt.total_seconds().dropna() / 60
        return float(diffs.mean())

    day_interval_minutes = _avg_interval("day")
    night_interval_minutes = _avg_interval("night")
    if day_interval_minutes is None and night_interval_minutes is None:
        interval_unknown = True
    else:
        interval_unknown = False

    quality_context = {
        "abpm_24h_available": True,
        "duration_hours": duration_hours,
        "valid_readings": valid_count,
        "expected_readings": expected_readings,
        "has_day_data": has_day_data,
        "has_night_data": has_night_data,
        "day_interval_minutes": day_interval_minutes,
        "night_interval_minutes": night_interval_minutes,
        "minor_deviation_from_target": False,
        "major_deviation_from_target": False,
        "interval_unknown": interval_unknown,
        "all_readings_have_sys_dia_timestamp_period": bool(window["systolic"].notna().all() and window["diastolic"].notna().all() and window["datetime"].notna().all() and window["day_period"].notna().all()),
        "missing_period_tag_only": bool(window["day_period"].isna().any() and window["systolic"].notna().all() and window["diastolic"].notna().all() and window["datetime"].notna().all()),
        "missing_some_sys_or_dia_or_timestamp": bool(window["systolic"].isna().any() or window["diastolic"].isna().any() or window["datetime"].isna().any()),
        "many_unusable_readings": float(window["systolic"].isna().mean() + window["diastolic"].isna().mean()) > 0.3,
        "activity_log": bool(abpm["activity_log"].dropna().iloc[0]) if "activity_log" in abpm.columns and abpm["activity_log"].notna().any() else None,
    }

    if day_interval_minutes is not None and night_interval_minutes is not None:
        quality_context["minor_deviation_from_target"] = (15 <= day_interval_minutes <= 30 and 30 <= night_interval_minutes <= 60)
        quality_context["major_deviation_from_target"] = not quality_context["minor_deviation_from_target"]

    return (
        float(window["systolic"].mean()),
        float(window["diastolic"].mean()),
        quality_context,
    )


def summarize_patient_rules(df: pd.DataFrame) -> pd.DataFrame:
    """Build a patient-level summary and symbolic classification report.

    This function groups raw measurements by patient_id, computes source
    averages and quality, then applies category, stage, and phenotype rules.
    """
    records: list[dict[str, object]] = []
    df = df.copy()
    df["datetime"] = _parse_datetime(df["datetime"])

    for patient_id, group in df.groupby("patient_id"):
        # get sys and dia averages and quality contexts for each source
        clinic_sys, clinic_dia, clinic_meta = _select_clinic_average(group)
        home_sys, home_dia, home_meta = _select_home_average(group)
        abpm_sys, abpm_dia, abpm_meta = _select_abpm_average(group)

        # compute quality scores and levels for each source
        clinic_quality_score, clinic_quality_level, clinic_quality_flags = compute_clinic_quality(
            {
                "clinic_readings_count": clinic_meta.get("clinic_readings_count", 0),
                "clinic_rest_minutes": clinic_meta.get("clinic_rest_minutes"),
                "clinic_missing": clinic_meta.get("clinic_missing", True),
            }
        )
        home_quality_score, home_quality_level, home_quality_flags = compute_home_quality(home_meta)
        abpm_quality_score, abpm_quality_level, abpm_quality_flags = compute_abpm_quality(abpm_meta)

        # aggregate all metrics and metadata into a single record for classification
        metrics = {
            "patient_id": patient_id,
            "clinic_sys": clinic_sys,
            "clinic_dia": clinic_dia,
            "home_sys": home_sys,
            "home_dia": home_dia,
            "abpm_24h_sys": abpm_sys,
            "abpm_24h_dia": abpm_dia,
            "clinic_available": _source_available(clinic_sys) and _source_available(clinic_dia),
            "home_available": _source_available(home_sys) and _source_available(home_dia),
            "abpm_24h_available": _source_available(abpm_sys) and _source_available(abpm_dia),
            "clinic_quality_score": clinic_quality_score,
            "clinic_quality_level": clinic_quality_level,
            "clinic_quality_flags": clinic_quality_flags,
            "home_quality_score": home_quality_score,
            "home_quality_level": home_quality_level,
            "home_quality_flags": home_quality_flags,
            "home_quality_usable": home_quality_level != "low",
            "abpm_quality_score": abpm_quality_score,
            "abpm_quality_level": abpm_quality_level,
            "abpm_quality_flags": abpm_quality_flags,
            "abpm_quality_usable": abpm_quality_level != "low",
        }

        # apply classification rules to determine category, stage, phenotype, and overall type
        metrics.update(_build_source_summary(metrics))
        category = classify_bp_category(metrics)
        stage = classify_bp_stage(metrics, category["bp_category"])
        phenotype = classify_phenotype(metrics)

        if stage["bp_stage"] == "stage2":
            tha_type = "stage_2"
        elif stage["bp_stage"] == "stage1":
            tha_type = "stage_1"
        elif category["bp_category"] == "elevated":
            tha_type = "elevated"
        elif category["bp_category"] == "hypertension":
            # Nếu không xác định được stage (do thiếu clinic) nhưng đã xác định hypertension → gán "hypertension"
            tha_type = "hypertension"
        elif category["bp_category"] == "normal":
            tha_type = "normal"
        else:
            tha_type = "unknown"

        record = {
            **metrics,
            **clinic_meta,
            **home_meta,
            **abpm_meta,
            **category,
            **stage,
            **phenotype,
            "tha_type": tha_type,
        }
        records.append(record)

    return pd.DataFrame(records)
