"""Pydantic schemas for API contracts."""
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    display_name: str


class ImportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    source_format: str
    status: str
    rows_parsed: int
    rows_inserted: int
    rows_skipped: int
    error_message: str | None = None
    created_at: datetime


class IngestionResult(BaseModel):
    job: ImportJobOut
    message: str
    features_recomputed: bool


class RawEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timestamp: datetime
    glucose_mgdl: float
    record_type: str
    source: str


class DailyFeatureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    day: date
    readings_count: int
    mean_glucose: float | None
    min_glucose: float | None
    max_glucose: float | None
    std_glucose: float | None
    cv_glucose: float | None
    time_in_range_pct: float | None
    time_below_range_pct: float | None
    time_above_range_pct: float | None
    rolling_3d_mean: float | None
    rolling_7d_mean: float | None
    trend_slope: float | None
    estimated_a1c: float | None


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category: str
    severity: str
    title: str
    message: str
    explanation: str
    confidence: float
    rule_id: str
    created_at: datetime


class DashboardSummary(BaseModel):
    user: UserOut
    total_readings: int
    days_covered: int
    latest_day: date | None
    latest_mean_glucose: float | None
    latest_tir_pct: float | None
    rolling_7d_mean: float | None
    estimated_a1c: float | None
    open_recommendations: int
