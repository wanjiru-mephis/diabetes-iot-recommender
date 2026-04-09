"""Dashboard router: high-level summary for the home page."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DailyFeature, RawSensorEvent, RecommendationLog, User
from ..schemas import DashboardSummary, UserOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _default_user(db: Session) -> User:
    user = db.execute(select(User).where(User.username == "default")).scalar_one_or_none()
    if user is None:
        user = User(username="default", display_name="Default User")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db)):
    user = _default_user(db)

    total_readings = db.execute(
        select(func.count(RawSensorEvent.id)).where(RawSensorEvent.user_id == user.id)
    ).scalar_one()

    days_covered = db.execute(
        select(func.count(DailyFeature.id)).where(DailyFeature.user_id == user.id)
    ).scalar_one()

    latest = db.execute(
        select(DailyFeature)
        .where(DailyFeature.user_id == user.id)
        .order_by(DailyFeature.day.desc())
        .limit(1)
    ).scalar_one_or_none()

    open_recs = db.execute(
        select(func.count(RecommendationLog.id)).where(RecommendationLog.user_id == user.id)
    ).scalar_one()

    return DashboardSummary(
        user=UserOut.model_validate(user),
        total_readings=total_readings,
        days_covered=days_covered,
        latest_day=latest.day if latest else None,
        latest_mean_glucose=latest.mean_glucose if latest else None,
        latest_tir_pct=latest.time_in_range_pct if latest else None,
        rolling_7d_mean=latest.rolling_7d_mean if latest else None,
        estimated_a1c=latest.estimated_a1c if latest else None,
        open_recommendations=open_recs,
    )
