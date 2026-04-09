"""Features router: daily engineered features and raw event listings."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DailyFeature, RawSensorEvent, User
from ..schemas import DailyFeatureOut, RawEventOut
from ..services.feature_engineering import recompute_daily_features

router = APIRouter(prefix="/api/features", tags=["features"])


def _default_user(db: Session) -> User:
    user = db.execute(select(User).where(User.username == "default")).scalar_one_or_none()
    if user is None:
        user = User(username="default", display_name="Default User")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.get("/daily", response_model=list[DailyFeatureOut])
def get_daily_features(
    limit: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    user = _default_user(db)
    rows = db.execute(
        select(DailyFeature)
        .where(DailyFeature.user_id == user.id)
        .order_by(DailyFeature.day.desc())
        .limit(limit)
    ).scalars().all()
    # Return oldest -> newest for chart-friendly order
    return [DailyFeatureOut.model_validate(r) for r in reversed(rows)]


@router.get("/raw", response_model=list[RawEventOut])
def get_raw_events(
    hours: int = Query(48, ge=1, le=24 * 90),
    db: Session = Depends(get_db),
):
    user = _default_user(db)
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    rows = db.execute(
        select(RawSensorEvent)
        .where(RawSensorEvent.user_id == user.id)
        .where(RawSensorEvent.timestamp >= cutoff)
        .order_by(RawSensorEvent.timestamp.asc())
    ).scalars().all()
    # If nothing in the last N hours (e.g. sample data is older), fall back to most recent N events
    if not rows:
        rows = db.execute(
            select(RawSensorEvent)
            .where(RawSensorEvent.user_id == user.id)
            .order_by(RawSensorEvent.timestamp.desc())
            .limit(500)
        ).scalars().all()
        rows = list(reversed(rows))
    return [RawEventOut.model_validate(r) for r in rows]


@router.post("/recompute")
def recompute(db: Session = Depends(get_db)):
    user = _default_user(db)
    n = recompute_daily_features(db, user.id)
    return {"days_written": n}
