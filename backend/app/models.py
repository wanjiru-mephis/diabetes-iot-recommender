"""
ORM models for the Diabetes IoT Recommender.

Tables:
    users                 - optional multi-user support (default user auto-seeded)
    import_jobs           - metadata for each CSV/JSON upload
    raw_sensor_events     - every glucose reading parsed from exports
    daily_features        - engineered per-day features
    recommendations_log   - recommendations produced by the engine
"""
from datetime import datetime, date

from sqlalchemy import (
    String, Integer, Float, DateTime, Date, ForeignKey, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    events: Mapped[list["RawSensorEvent"]] = relationship(back_populates="user")
    features: Mapped[list["DailyFeature"]] = relationship(back_populates="user")
    recommendations: Mapped[list["RecommendationLog"]] = relationship(back_populates="user")


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_format: Mapped[str] = mapped_column(String(32), nullable=False)  # csv | json
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    rows_parsed: Mapped[int] = mapped_column(Integer, default=0)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RawSensorEvent(Base):
    __tablename__ = "raw_sensor_events"
    __table_args__ = (
        UniqueConstraint("user_id", "timestamp", "source", name="uq_user_ts_source"),
        Index("ix_events_user_time", "user_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    glucose_mgdl: Mapped[float] = mapped_column(Float, nullable=False)
    record_type: Mapped[str] = mapped_column(String(32), default="historic")  # historic | scan | manual
    source: Mapped[str] = mapped_column(String(64), default="libre_export")
    device_serial: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="events")


class DailyFeature(Base):
    __tablename__ = "daily_features"
    __table_args__ = (
        UniqueConstraint("user_id", "day", name="uq_user_day"),
        Index("ix_features_user_day", "user_id", "day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)

    readings_count: Mapped[int] = mapped_column(Integer, default=0)
    mean_glucose: Mapped[float | None] = mapped_column(Float)
    min_glucose: Mapped[float | None] = mapped_column(Float)
    max_glucose: Mapped[float | None] = mapped_column(Float)
    std_glucose: Mapped[float | None] = mapped_column(Float)
    cv_glucose: Mapped[float | None] = mapped_column(Float)  # coefficient of variation %
    time_in_range_pct: Mapped[float | None] = mapped_column(Float)
    time_below_range_pct: Mapped[float | None] = mapped_column(Float)
    time_above_range_pct: Mapped[float | None] = mapped_column(Float)
    rolling_3d_mean: Mapped[float | None] = mapped_column(Float)
    rolling_7d_mean: Mapped[float | None] = mapped_column(Float)
    trend_slope: Mapped[float | None] = mapped_column(Float)  # mg/dL per day
    estimated_a1c: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="features")


class RecommendationLog(Base):
    __tablename__ = "recommendations_log"
    __table_args__ = (
        Index("ix_recs_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # info | low | medium | high
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="recommendations")
