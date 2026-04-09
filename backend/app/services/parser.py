"""
Parser for glucose data exported from the FreeStyle Libre (and Libre 3 Plus)
companion app, plus a generic simple CSV/JSON fallback.

The Libre CSV export typically looks like (header on row 2 or 3):

    Device,Serial Number,Device Timestamp,Record Type,Historic Glucose mg/dL,
    Scan Glucose mg/dL,Non-numeric Rapid-Acting Insulin,...
    FreeStyle LibreLink,1A2B3C,01-15-2025 08:05,0,112,,,,,
    FreeStyle LibreLink,1A2B3C,01-15-2025 08:20,1,,128,,,,

Record Type meaning:
    0 = historic glucose (periodic CGM reading)
    1 = scan glucose
    2+ = manual/insulin/carb events (we ignore for glucose)

This parser is tolerant:
    - It auto-detects the header row (scans first 5 rows for known columns).
    - Accepts either mg/dL or mmol/L (we normalize to mg/dL).
    - Accepts ISO timestamps or "MM-DD-YYYY HH:MM" / "DD-MM-YYYY HH:MM".
    - Also accepts a minimal schema: columns = timestamp,glucose_mgdl
    - JSON: either a list of {timestamp, glucose_mgdl} or the same keys as CSV.

Replacing sample data with real Libre exports: drop the file in and call
the /api/ingest/upload endpoint. No code change required.
"""
from __future__ import annotations

import io
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import pandas as pd
from dateutil import parser as dateparser

from ..logging_config import get_logger

log = get_logger(__name__)

# Columns we may see in Libre exports
LIBRE_TS_COLS = ["Device Timestamp", "device timestamp", "timestamp", "Timestamp"]
LIBRE_HIST_COLS = ["Historic Glucose mg/dL", "historic glucose mg/dl", "Historic Glucose (mg/dL)"]
LIBRE_SCAN_COLS = ["Scan Glucose mg/dL", "scan glucose mg/dl", "Scan Glucose (mg/dL)"]
LIBRE_HIST_MMOL = ["Historic Glucose mmol/L", "Historic Glucose (mmol/L)"]
LIBRE_SCAN_MMOL = ["Scan Glucose mmol/L", "Scan Glucose (mmol/L)"]
LIBRE_RECTYPE_COLS = ["Record Type", "record type"]
LIBRE_SERIAL_COLS = ["Serial Number", "serial number"]
GENERIC_GLUCOSE_COLS = ["glucose_mgdl", "glucose", "value", "mg_dl", "mgdl"]


@dataclass
class ParsedEvent:
    timestamp: datetime
    glucose_mgdl: float
    record_type: str  # "historic" | "scan" | "manual"
    device_serial: str | None = None
    source: str = "libre_export"


def _pick(columns: list[str], candidates: list[str]) -> str | None:
    lowered = {c.lower().strip(): c for c in columns}
    for cand in candidates:
        if cand.lower().strip() in lowered:
            return lowered[cand.lower().strip()]
    return None


def _parse_timestamp(value) -> datetime | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    # Try common Libre format first
    for fmt in ("%m-%d-%Y %I:%M %p", "%m-%d-%Y %H:%M", "%d-%m-%Y %H:%M",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return dateparser.parse(s)
    except (ValueError, TypeError):
        return None


def _mmol_to_mgdl(v: float) -> float:
    return round(v * 18.0182, 1)


def _detect_header_row(content: str) -> int:
    """Libre exports often have 1-2 metadata rows before the real header."""
    lines = content.splitlines()[:6]
    for i, line in enumerate(lines):
        lower = line.lower()
        if "glucose" in lower and ("timestamp" in lower or "time" in lower):
            return i
        if "glucose_mgdl" in lower:
            return i
    return 0


def parse_csv(raw_bytes: bytes) -> list[ParsedEvent]:
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    header_row = _detect_header_row(text)
    try:
        df = pd.read_csv(io.StringIO(text), skiprows=header_row)
    except Exception as e:
        raise ValueError(f"Could not parse CSV: {e}") from e

    if df.empty:
        return []

    return _dataframe_to_events(df)


def parse_json(raw_bytes: bytes) -> list[ParsedEvent]:
    try:
        data = json.loads(raw_bytes.decode("utf-8-sig", errors="replace"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e

    if isinstance(data, dict) and "readings" in data:
        data = data["readings"]
    if not isinstance(data, list):
        raise ValueError("JSON must be a list of readings or an object with 'readings'.")

    df = pd.DataFrame(data)
    if df.empty:
        return []
    return _dataframe_to_events(df)


def _dataframe_to_events(df: pd.DataFrame) -> list[ParsedEvent]:
    cols = list(df.columns)
    ts_col = _pick(cols, LIBRE_TS_COLS)
    hist_col = _pick(cols, LIBRE_HIST_COLS)
    scan_col = _pick(cols, LIBRE_SCAN_COLS)
    hist_mmol_col = _pick(cols, LIBRE_HIST_MMOL)
    scan_mmol_col = _pick(cols, LIBRE_SCAN_MMOL)
    rectype_col = _pick(cols, LIBRE_RECTYPE_COLS)
    serial_col = _pick(cols, LIBRE_SERIAL_COLS)
    generic_col = _pick(cols, GENERIC_GLUCOSE_COLS)

    if not ts_col:
        raise ValueError(
            f"No timestamp column found. Columns seen: {cols}"
        )
    if not any([hist_col, scan_col, hist_mmol_col, scan_mmol_col, generic_col]):
        raise ValueError(
            f"No glucose column found. Columns seen: {cols}"
        )

    events: list[ParsedEvent] = []
    bad = 0

    for _, row in df.iterrows():
        ts = _parse_timestamp(row[ts_col])
        if ts is None:
            bad += 1
            continue

        glucose: float | None = None
        rtype = "historic"

        # Preference order: generic > historic mg/dL > scan mg/dL > historic mmol/L > scan mmol/L
        if generic_col and pd.notna(row[generic_col]):
            try:
                glucose = float(row[generic_col])
            except (ValueError, TypeError):
                glucose = None
        if glucose is None and hist_col and pd.notna(row[hist_col]):
            try:
                glucose = float(row[hist_col])
                rtype = "historic"
            except (ValueError, TypeError):
                pass
        if glucose is None and scan_col and pd.notna(row[scan_col]):
            try:
                glucose = float(row[scan_col])
                rtype = "scan"
            except (ValueError, TypeError):
                pass
        if glucose is None and hist_mmol_col and pd.notna(row[hist_mmol_col]):
            try:
                glucose = _mmol_to_mgdl(float(row[hist_mmol_col]))
                rtype = "historic"
            except (ValueError, TypeError):
                pass
        if glucose is None and scan_mmol_col and pd.notna(row[scan_mmol_col]):
            try:
                glucose = _mmol_to_mgdl(float(row[scan_mmol_col]))
                rtype = "scan"
            except (ValueError, TypeError):
                pass

        if glucose is None:
            bad += 1
            continue

        # Sanity check - physiological range
        if not (20.0 <= glucose <= 600.0):
            bad += 1
            continue

        # Override rtype from Libre's numeric Record Type if present
        if rectype_col and pd.notna(row[rectype_col]):
            try:
                rt = int(row[rectype_col])
                if rt == 0:
                    rtype = "historic"
                elif rt == 1:
                    rtype = "scan"
                else:
                    # manual insulin/carb events - skip
                    continue
            except (ValueError, TypeError):
                pass

        serial = None
        if serial_col and pd.notna(row[serial_col]):
            serial = str(row[serial_col])[:64]

        events.append(ParsedEvent(
            timestamp=ts,
            glucose_mgdl=round(float(glucose), 1),
            record_type=rtype,
            device_serial=serial,
        ))

    log.info("Parsed %d valid events (%d bad rows skipped)", len(events), bad)
    return events
