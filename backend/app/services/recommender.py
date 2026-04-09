"""
Rule-based recommendation engine.

IMPORTANT (non-diagnostic):
    This module does NOT diagnose, prescribe, or dose. It produces
    treatment-support suggestions: reminders, lifestyle nudges, data-quality
    prompts, and escalation guidance ("consider contacting your care team").

Each rule returns zero or more Recommendation dicts with:
    category, severity, title, message, explanation, confidence, rule_id.

Severity:
    info     - informational / positive reinforcement
    low      - gentle nudge
    medium   - notable concern, action suggested
    high     - prompt to contact care team (never an emergency instruction here;
               severe-low/high pathways use explicit escalation wording)
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..logging_config import get_logger
from ..models import DailyFeature, RecommendationLog, RawSensorEvent

log = get_logger(__name__)


@dataclass
class Recommendation:
    category: str
    severity: str
    title: str
    message: str
    explanation: str
    confidence: float
    rule_id: str


def _latest_features(db: Session, user_id: int, days: int = 14) -> list[DailyFeature]:
    rows = db.execute(
        select(DailyFeature)
        .where(DailyFeature.user_id == user_id)
        .order_by(DailyFeature.day.desc())
        .limit(days)
    ).scalars().all()
    return list(reversed(rows))  # oldest -> newest


# --------------------- Individual rules ----------------------

def rule_insufficient_data(feats: list[DailyFeature]) -> list[Recommendation]:
    if len(feats) == 0:
        return [Recommendation(
            category="data_quality",
            severity="info",
            title="No glucose data yet",
            message="Upload a glucose export to start seeing trends and recommendations.",
            explanation="The system has no daily features stored for this user.",
            confidence=1.0,
            rule_id="DATA_001",
        )]
    if len(feats) < 3:
        return [Recommendation(
            category="data_quality",
            severity="low",
            title="Limited data available",
            message="Keep uploading your CGM exports regularly. At least 3-7 days of data "
                    "helps the system produce more reliable trend insights.",
            explanation=f"Only {len(feats)} day(s) of features are available; rolling "
                        f"averages and trend slope need more history.",
            confidence=0.9,
            rule_id="DATA_002",
        )]
    return []


def rule_low_sensor_coverage(feats: list[DailyFeature]) -> list[Recommendation]:
    # Libre 3 Plus records ~every 1-5 min; healthy daily count is usually >= 200.
    # We warn if recent days average < 100 readings.
    recent = feats[-3:]
    if not recent:
        return []
    avg = sum(f.readings_count for f in recent) / len(recent)
    if avg < 100:
        return [Recommendation(
            category="data_quality",
            severity="medium",
            title="Low sensor coverage detected",
            message="Recent days have fewer readings than expected. Check that the sensor "
                    "is worn consistently and that the app is syncing regularly.",
            explanation=f"Average readings over the last {len(recent)} day(s) = {avg:.0f}; "
                        f"a healthy CGM day is typically several hundred readings.",
            confidence=0.8,
            rule_id="DATA_003",
        )]
    return []


def rule_high_average(feats: list[DailyFeature]) -> list[Recommendation]:
    recent = feats[-7:]
    means = [f.mean_glucose for f in recent if f.mean_glucose is not None]
    if len(means) < 3:
        return []
    avg7 = sum(means) / len(means)
    if avg7 >= 200:
        return [Recommendation(
            category="glucose_level",
            severity="high",
            title="Sustained high average glucose",
            message="Your 7-day average glucose is notably elevated. Consider contacting "
                    "your diabetes care team to review your current plan.",
            explanation=f"7-day mean glucose = {avg7:.0f} mg/dL (target generally < 154).",
            confidence=0.9,
            rule_id="GLU_001",
        )]
    if avg7 >= 170:
        return [Recommendation(
            category="glucose_level",
            severity="medium",
            title="7-day average above target",
            message="Your average glucose trend is above the usual target range. Reviewing "
                    "meal timing, carbohydrate portions, and activity can help.",
            explanation=f"7-day mean glucose = {avg7:.0f} mg/dL.",
            confidence=0.8,
            rule_id="GLU_002",
        )]
    return []


def rule_low_readings(feats: list[DailyFeature], db: Session, user_id: int) -> list[Recommendation]:
    if not feats:
        return []
    last = feats[-1]
    recs: list[Recommendation] = []
    if last.time_below_range_pct is not None and last.time_below_range_pct >= 4:
        recs.append(Recommendation(
            category="glucose_level",
            severity="high",
            title="Time below range is elevated",
            message="A higher-than-usual share of readings were below 70 mg/dL yesterday. "
                    "Please review your logs with your care team; never self-adjust medication "
                    "without guidance.",
            explanation=f"Time below range on {last.day} = {last.time_below_range_pct:.1f}% "
                        f"(target < 4%).",
            confidence=0.9,
            rule_id="GLU_003",
        ))
    # Severe-low check on raw events (last 24h)
    cutoff = feats[-1].day
    severe_count = db.execute(
        select(RawSensorEvent)
        .where(RawSensorEvent.user_id == user_id)
        .where(RawSensorEvent.glucose_mgdl < settings.severe_low)
    ).scalars().all()
    if len(severe_count) > 0:
        recs.append(Recommendation(
            category="safety",
            severity="high",
            title="Severe low readings detected in history",
            message=f"{len(severe_count)} reading(s) below {settings.severe_low:.0f} mg/dL "
                    "were found. If you experience symptoms of hypoglycemia, follow the "
                    "hypoglycemia plan provided by your care team and seek urgent help if severe.",
            explanation="Severe-low events are flagged regardless of frequency so you can "
                        "discuss them with your clinician.",
            confidence=0.95,
            rule_id="SAFETY_001",
        ))
    return recs


def rule_high_variability(feats: list[DailyFeature]) -> list[Recommendation]:
    recent = feats[-7:]
    cvs = [f.cv_glucose for f in recent if f.cv_glucose is not None]
    if len(cvs) < 3:
        return []
    avg_cv = sum(cvs) / len(cvs)
    # International consensus: CV >= 36% indicates unstable glycemia.
    if avg_cv >= 36:
        return [Recommendation(
            category="variability",
            severity="medium",
            title="High glycemic variability",
            message="Your glucose is swinging more widely than usual. Consistent meal timing, "
                    "balanced carbs/protein/fiber, and steady activity can help smooth swings.",
            explanation=f"Average coefficient of variation over last {len(cvs)} day(s) "
                        f"= {avg_cv:.1f}% (target < 36%).",
            confidence=0.8,
            rule_id="VAR_001",
        )]
    return []


def rule_trend_rising(feats: list[DailyFeature]) -> list[Recommendation]:
    if not feats:
        return []
    last = feats[-1]
    if last.trend_slope is None:
        return []
    if last.trend_slope >= 3.0:
        return [Recommendation(
            category="trend",
            severity="medium",
            title="Rising glucose trend",
            message="Your daily averages have been rising over the last two weeks. "
                    "Consider reviewing recent changes in meals, stress, sleep, or activity.",
            explanation=f"14-day trend slope = +{last.trend_slope:.1f} mg/dL per day.",
            confidence=0.8,
            rule_id="TREND_001",
        )]
    if last.trend_slope <= -3.0:
        return [Recommendation(
            category="trend",
            severity="low",
            title="Falling glucose trend",
            message="Your daily averages are trending down. If this is intentional, great — "
                    "just keep an eye on lows. Otherwise, flag it with your care team.",
            explanation=f"14-day trend slope = {last.trend_slope:.1f} mg/dL per day.",
            confidence=0.75,
            rule_id="TREND_002",
        )]
    return []


def rule_time_in_range(feats: list[DailyFeature]) -> list[Recommendation]:
    recent = feats[-7:]
    tirs = [f.time_in_range_pct for f in recent if f.time_in_range_pct is not None]
    if len(tirs) < 3:
        return []
    avg_tir = sum(tirs) / len(tirs)
    if avg_tir >= 70:
        return [Recommendation(
            category="positive",
            severity="info",
            title="Great time-in-range",
            message="You're meeting the general time-in-range target. Keep up the consistent "
                    "habits that are working.",
            explanation=f"7-day average time-in-range = {avg_tir:.0f}% (goal ≥ 70%).",
            confidence=0.9,
            rule_id="POS_001",
        )]
    if avg_tir < 50:
        return [Recommendation(
            category="glucose_level",
            severity="medium",
            title="Time-in-range below goal",
            message="Less than half of recent readings are within the 70-180 range. "
                    "Small, steady changes in meal composition and activity can help. "
                    "Discuss adjustments with your care team if this pattern continues.",
            explanation=f"7-day average time-in-range = {avg_tir:.0f}% (goal ≥ 70%).",
            confidence=0.85,
            rule_id="GLU_004",
        )]
    return []


def rule_lifestyle_nudge(feats: list[DailyFeature]) -> list[Recommendation]:
    if len(feats) < 7:
        return []
    # If max glucose stays high most days, nudge toward post-meal movement.
    highs = sum(1 for f in feats[-7:] if f.max_glucose and f.max_glucose > 220)
    if highs >= 4:
        return [Recommendation(
            category="lifestyle",
            severity="low",
            title="Consider a post-meal walk",
            message="Several recent days show post-meal peaks above 220 mg/dL. A 10-15 "
                    "minute walk after your largest meal is a gentle habit that many people "
                    "find helps blunt post-meal spikes.",
            explanation=f"{highs} of the last 7 days had a max reading above 220 mg/dL.",
            confidence=0.7,
            rule_id="LIFE_001",
        )]
    return []


def rule_reminder_hydration(feats: list[DailyFeature]) -> list[Recommendation]:
    if not feats:
        return []
    last = feats[-1]
    if last.mean_glucose is not None and last.mean_glucose >= 200:
        return [Recommendation(
            category="reminder",
            severity="low",
            title="Stay hydrated",
            message="On days with higher glucose, drinking water regularly supports your body "
                    "and can help your kidneys clear excess glucose. This is a general wellness "
                    "reminder, not a treatment.",
            explanation=f"Mean glucose on {last.day} = {last.mean_glucose:.0f} mg/dL.",
            confidence=0.6,
            rule_id="REM_001",
        )]
    return []


RULES = [
    rule_insufficient_data,
    rule_low_sensor_coverage,
    rule_high_average,
    rule_high_variability,
    rule_trend_rising,
    rule_time_in_range,
    rule_lifestyle_nudge,
    rule_reminder_hydration,
]


def generate_recommendations(db: Session, user_id: int) -> list[Recommendation]:
    feats = _latest_features(db, user_id, days=14)
    all_recs: list[Recommendation] = []
    for rule in RULES:
        try:
            all_recs.extend(rule(feats))
        except Exception as e:  # defensive - one rule shouldn't break the rest
            log.exception("Rule %s failed: %s", rule.__name__, e)

    # Rules that need DB access
    try:
        all_recs.extend(rule_low_readings(feats, db, user_id))
    except Exception as e:
        log.exception("rule_low_readings failed: %s", e)

    # Deduplicate by rule_id (keep highest severity)
    severity_rank = {"info": 0, "low": 1, "medium": 2, "high": 3}
    seen: dict[str, Recommendation] = {}
    for r in all_recs:
        prev = seen.get(r.rule_id)
        if not prev or severity_rank[r.severity] > severity_rank[prev.severity]:
            seen[r.rule_id] = r
    return list(seen.values())


def store_recommendations(db: Session, user_id: int, recs: Iterable[Recommendation]) -> int:
    objs = [RecommendationLog(user_id=user_id, **asdict(r)) for r in recs]
    db.add_all(objs)
    db.commit()
    return len(objs)
