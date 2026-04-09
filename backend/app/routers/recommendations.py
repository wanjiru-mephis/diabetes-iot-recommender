"""Recommendations router: list and regenerate treatment-support recs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import RecommendationLog, User
from ..schemas import RecommendationOut
from ..services.recommender import generate_recommendations, store_recommendations

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _default_user(db: Session) -> User:
    user = db.execute(select(User).where(User.username == "default")).scalar_one_or_none()
    if user is None:
        user = User(username="default", display_name="Default User")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.get("", response_model=list[RecommendationOut])
def list_recommendations(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    user = _default_user(db)
    rows = db.execute(
        select(RecommendationLog)
        .where(RecommendationLog.user_id == user.id)
        .order_by(RecommendationLog.created_at.desc())
        .limit(limit)
    ).scalars().all()
    return [RecommendationOut.model_validate(r) for r in rows]


@router.post("/regenerate", response_model=list[RecommendationOut])
def regenerate(db: Session = Depends(get_db)):
    user = _default_user(db)
    # Clear older recs so the dashboard only shows the latest set
    db.execute(delete(RecommendationLog).where(RecommendationLog.user_id == user.id))
    db.commit()
    recs = generate_recommendations(db, user.id)
    store_recommendations(db, user.id, recs)
    rows = db.execute(
        select(RecommendationLog)
        .where(RecommendationLog.user_id == user.id)
        .order_by(RecommendationLog.created_at.desc())
    ).scalars().all()
    return [RecommendationOut.model_validate(r) for r in rows]
