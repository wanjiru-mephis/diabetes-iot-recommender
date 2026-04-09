"""
Feature engineering: raw sensor events -> daily features.

Computes, per day:
    - readings_count
    - mean / min / max / std
    - coefficient of variation (CV) - glycemic variability proxy
    - time in range (70-180), time below, time above
    - rolling 3-day and 7-day means
    - linear trend slope across the last 14 days
    - estimated A1c (eA1c), from ADAG equation:  eA1c = (mean + 46.7) / 28.7
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from ..config import settings
from ..logging_config import get_logger
from ..models import RawSensorEvent, DailyFeature

log = get_logger(__name__)


def _estimated_a1c(mean_mgdl: float) -> float:
    return round((mean_mgdl + 46.7) / 28.7, 2)


def recompute_daily_features(db: Session, user_id: int) -> int:
    """Recompute all daily features for a user. Returns number of days written."""
    rows = db.execute(
        select(RawSensorEvent.timestamp, RawSensorEvent.glucose_mgdl)
        .where(RawSensorEvent.user_id == user_id)
        .order_by(RawSensorEvent.timestamp.asc())
    ).all()

    if not rows:
        log.info("No events for user=%s, clearing features.", user_id)
        db.execute(delete(DailyFeature).where(DailyFeature.user_id == user_id))
        db.commit()
        return 0

    df = pd.DataFrame(rows, columns=["timestamp", "glucose"])
    df["day"] = pd.to_datetime(df["timestamp"]).dt.date

    # Per-day aggregates
    grouped = df.groupby("day")["glucose"]
    daily = pd.DataFrame({
        "readings_count": grouped.count(),
        "mean_glucose":   grouped.mean().round(2),
        "min_glucose":    grouped.min().round(2),
        "max_glucose":    grouped.max().round(2),
        "std_glucose":    grouped.std(ddof=0).round(2),
    })
    daily["cv_glucose"] = (
        (daily["std_glucose"] / daily["mean_glucose"].replace(0, np.nan)) * 100
    ).round(2)

    low, high = settings.tir_low, settings.tir_high
    tir = df.assign(
        in_range=(df["glucose"] >= low) & (df["glucose"] <= high),
        below=df["glucose"] < low,
        above=df["glucose"] > high,
    ).groupby("day")[["in_range", "below", "above"]].mean() * 100
    tir = tir.round(2)
    tir.columns = ["time_in_range_pct", "time_below_range_pct", "time_above_range_pct"]
    daily = daily.join(tir)

    daily = daily.sort_index()

    # Rolling means
    daily["rolling_3d_mean"] = daily["mean_glucose"].rolling(window=3, min_periods=1).mean().round(2)
    daily["rolling_7d_mean"] = daily["mean_glucose"].rolling(window=7, min_periods=1).mean().round(2)

    # Trend slope (last 14 days, mg/dL per day, via least squares)
    daily["trend_slope"] = np.nan
    means = daily["mean_glucose"].values
    days_list = list(daily.index)
    for i in range(len(days_list)):
        start = max(0, i - 13)
        window = means[start:i + 1]
        if len(window) >= 3:
            x = np.arange(len(window), dtype=float)
            slope = float(np.polyfit(x, window, 1)[0])
            daily.iat[i, daily.columns.get_loc("trend_slope")] = round(slope, 3)

    daily["estimated_a1c"] = daily["mean_glucose"].apply(_estimated_a1c)

    # Upsert: simple "delete then insert" for this user
    db.execute(delete(DailyFeature).where(DailyFeature.user_id == user_id))
    records = []
    for day_val, row in daily.iterrows():
        records.append(DailyFeature(
            user_id=user_id,
            day=day_val,
            readings_count=int(row["readings_count"]),
            mean_glucose=float(row["mean_glucose"]) if pd.notna(row["mean_glucose"]) else None,
            min_glucose=float(row["min_glucose"]) if pd.notna(row["min_glucose"]) else None,
            max_glucose=float(row["max_glucose"]) if pd.notna(row["max_glucose"]) else None,
            std_glucose=float(row["std_glucose"]) if pd.notna(row["std_glucose"]) else None,
            cv_glucose=float(row["cv_glucose"]) if pd.notna(row["cv_glucose"]) else None,
            time_in_range_pct=float(row["time_in_range_pct"]) if pd.notna(row["time_in_range_pct"]) else None,
            time_below_range_pct=float(row["time_below_range_pct"]) if pd.notna(row["time_below_range_pct"]) else None,
            time_above_range_pct=float(row["time_above_range_pct"]) if pd.notna(row["time_above_range_pct"]) else None,
            rolling_3d_mean=float(row["rolling_3d_mean"]) if pd.notna(row["rolling_3d_mean"]) else None,
            rolling_7d_mean=float(row["rolling_7d_mean"]) if pd.notna(row["rolling_7d_mean"]) else None,
            trend_slope=float(row["trend_slope"]) if pd.notna(row["trend_slope"]) else None,
            estimated_a1c=float(row["estimated_a1c"]) if pd.notna(row["estimated_a1c"]) else None,
        ))
    db.add_all(records)
    db.commit()
    log.info("Recomputed %d day-features for user=%s", len(records), user_id)
    return len(records)
