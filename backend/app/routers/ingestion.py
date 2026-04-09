"""Ingestion router: upload CSV/JSON glucose exports."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..logging_config import get_logger
from ..models import ImportJob, RawSensorEvent, User
from ..schemas import IngestionResult, ImportJobOut
from ..services import parser as parser_svc
from ..services.feature_engineering import recompute_daily_features
from ..services.recommender import generate_recommendations, store_recommendations

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])
log = get_logger(__name__)


def _get_default_user(db: Session) -> User:
    user = db.execute(select(User).where(User.username == "default")).scalar_one_or_none()
    if user is None:
        user = User(username="default", display_name="Default User")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.post("/upload", response_model=IngestionResult, status_code=status.HTTP_201_CREATED)
async def upload_glucose_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a Libre (or generic) glucose export. Accepts .csv or .json.

    Flow:
        1. Parse file into ParsedEvent objects.
        2. Insert into raw_sensor_events (dedup by (user, timestamp, source)).
        3. Recompute daily_features.
        4. Regenerate recommendations.
    """
    if not file.filename:
        raise HTTPException(400, "No filename provided.")

    name_lower = file.filename.lower()
    if name_lower.endswith(".csv"):
        fmt = "csv"
    elif name_lower.endswith(".json"):
        fmt = "json"
    else:
        raise HTTPException(400, "Only .csv and .json files are supported.")

    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Uploaded file is empty.")

    user = _get_default_user(db)

    job = ImportJob(
        user_id=user.id,
        filename=file.filename,
        source_format=fmt,
        status="parsing",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        events = parser_svc.parse_csv(raw) if fmt == "csv" else parser_svc.parse_json(raw)
    except ValueError as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
        raise HTTPException(400, f"Parse error: {e}")

    job.rows_parsed = len(events)

    # Dedup + insert
    existing = db.execute(
        select(RawSensorEvent.timestamp, RawSensorEvent.source)
        .where(RawSensorEvent.user_id == user.id)
    ).all()
    existing_keys = {(t, s) for t, s in existing}

    inserted = 0
    skipped = 0
    batch: list[RawSensorEvent] = []
    for ev in events:
        key = (ev.timestamp, ev.source)
        if key in existing_keys:
            skipped += 1
            continue
        existing_keys.add(key)
        batch.append(RawSensorEvent(
            user_id=user.id,
            timestamp=ev.timestamp,
            glucose_mgdl=ev.glucose_mgdl,
            record_type=ev.record_type,
            source=ev.source,
            device_serial=ev.device_serial,
        ))
        inserted += 1

    if batch:
        db.add_all(batch)
        db.commit()

    job.rows_inserted = inserted
    job.rows_skipped = skipped
    job.status = "completed"
    db.commit()
    log.info("Import job %d: parsed=%d inserted=%d skipped=%d",
             job.id, job.rows_parsed, inserted, skipped)

    # Recompute features + regenerate recommendations
    recomputed = False
    if inserted > 0:
        recompute_daily_features(db, user.id)
        recs = generate_recommendations(db, user.id)
        store_recommendations(db, user.id, recs)
        recomputed = True

    db.refresh(job)
    return IngestionResult(
        job=ImportJobOut.model_validate(job),
        message=f"Ingested {inserted} new reading(s); skipped {skipped} duplicate(s).",
        features_recomputed=recomputed,
    )


@router.get("/jobs", response_model=list[ImportJobOut])
def list_jobs(db: Session = Depends(get_db)):
    user = _get_default_user(db)
    jobs = db.execute(
        select(ImportJob).where(ImportJob.user_id == user.id).order_by(ImportJob.created_at.desc())
    ).scalars().all()
    return [ImportJobOut.model_validate(j) for j in jobs]
