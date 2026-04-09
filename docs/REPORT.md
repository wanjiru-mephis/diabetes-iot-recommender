# Final Project Report
## AI-Based Medical IoT Recommender System for Type 2 Diabetes Treatment Support

---

## 1. Abstract

This project presents the end-to-end design and implementation of a **non-diagnostic,
treatment-support Medical IoT system** for people living with Type 2 Diabetes. The system
ingests continuous glucose monitoring (CGM) data from the FreeStyle Libre 3 Plus companion
app, computes a set of interpretable per-day features, and produces personalised
recommendations through a transparent rule-based engine. A React dashboard delivers the
insights back to the user in a clinician-friendly format. The system is deliberately
architected so that the only component that needs to change when direct sensor access
becomes available in the future is the ingestion source; every downstream module is
already integrated and functional.

---

## 2. Problem Statement

Type 2 Diabetes affects hundreds of millions of people worldwide and its management is
inherently data-driven: lifestyle choices, medication adherence, meal composition, sleep,
and stress all interact to determine glycemic outcomes. Continuous glucose monitors such
as the FreeStyle Libre 3 Plus produce rich, minute-level data, but the insight that data
delivers to patients is often limited to a basic in-app trend line. There is an
opportunity to layer an **interpretable, explanation-first recommendation layer** on top
of the raw CGM stream that nudges users toward healthier behaviour without ever crossing
the line into diagnosis or prescription.

---

## 3. The App-Export Constraint (Reality Check)

A core engineering constraint shaped the entire architecture:

> The FreeStyle Libre 3 Plus does **not** expose a public real-time API for third parties,
> and direct sensor access is not reliably available in practice. However, the companion
> app allows the user to export their own glucose history as CSV or JSON.

Rather than stub this out with a fake sensor simulator, this project **treats the
app-export as a first-class ingestion source**. Ingesting a file is functionally equivalent
to ingesting a batch from a streaming source: the file format maps one-to-one onto the
`ParsedEvent` objects that the rest of the pipeline consumes. When real-time access
becomes available, a new ingestion worker can be added that produces the exact same
`ParsedEvent` objects and inserts them into `raw_sensor_events` — **no other module changes**.

---

## 4. System Architecture

```
Sensing (App Export)
        │
        ▼
  Ingestion API  ────────► import_jobs table (audit log of uploads)
        │
        ▼
  Parser (Libre CSV/JSON, generic CSV/JSON)
        │
        ▼
  raw_sensor_events   (dedup on user + timestamp + source)
        │
        ▼
  Feature Engineering  (pandas/numpy)
        │
        ▼
  daily_features   (per-day aggregates + rolling stats + trend)
        │
        ▼
  Rule-based Recommendation Engine
        │
        ▼
  recommendations_log
        │
        ▼
  FastAPI REST endpoints
        │
        ▼
  React + Vite + Recharts dashboard
```

### 4.1 Tech Stack

| Layer              | Choice                          | Rationale                                 |
|--------------------|---------------------------------|-------------------------------------------|
| Backend framework  | FastAPI                         | Modern, typed, automatic OpenAPI docs     |
| ORM                | SQLAlchemy 2.0                  | Battle-tested, portable across DBs        |
| Database           | SQLite (default), PostgreSQL    | Zero-setup demo + production option       |
| Data processing    | pandas + numpy                  | Standard for tabular feature engineering  |
| Validation         | Pydantic v2                     | Shared models across request/response     |
| Frontend           | React + Vite                    | Fast iteration, small footprint           |
| Charts             | Recharts                        | Simple, declarative, good defaults        |

---

## 5. Methodology

### 5.1 Data Ingestion

The parser (`backend/app/services/parser.py`) accepts three input shapes:

1. **FreeStyle Libre CSV** (the real-world target format). Libre exports include one or
   two metadata rows above the header; the parser auto-detects the header row by scanning
   the first few lines for `"glucose"` + `"timestamp"` tokens.
2. **Generic CSV** with a minimum schema of `timestamp,glucose_mgdl`.
3. **JSON**, either a list of readings or `{"readings": [...]}`.

The parser is deliberately tolerant: it accepts timestamps in ISO-8601, `MM-DD-YYYY HH:MM`
(Libre's default US locale), or any format `python-dateutil` can recognise. It also
accepts mmol/L values and normalises to mg/dL (multiplying by 18.0182). Values outside
the physiological range of 20–600 mg/dL are rejected as parse errors.

Duplicates are prevented by a unique constraint on `(user_id, timestamp, source)` at the
database level, and the ingestion router also deduplicates in memory before the insert
to avoid round-trip constraint errors.

### 5.2 Feature Engineering

For every day that contains at least one reading, the engine computes:

| Feature                 | Definition                                                |
|-------------------------|-----------------------------------------------------------|
| `readings_count`        | Number of glucose readings that day                       |
| `mean_glucose`          | Daily arithmetic mean                                     |
| `min_glucose`, `max_glucose` | Daily extremes                                       |
| `std_glucose`           | Population standard deviation                             |
| `cv_glucose`            | Coefficient of variation = std/mean × 100 (variability)   |
| `time_in_range_pct`     | Share of readings in [70, 180] mg/dL                      |
| `time_below_range_pct`  | Share of readings < 70 mg/dL                              |
| `time_above_range_pct`  | Share of readings > 180 mg/dL                             |
| `rolling_3d_mean`       | 3-day rolling mean of `mean_glucose`                      |
| `rolling_7d_mean`       | 7-day rolling mean of `mean_glucose`                      |
| `trend_slope`           | Slope (mg/dL per day) of a linear fit over last 14 days   |
| `estimated_a1c`         | ADAG equation: (mean + 46.7) / 28.7                       |

The 70–180 mg/dL target is the internationally accepted time-in-range target published
by the Advanced Technologies & Treatments for Diabetes (ATTD) consensus. The A1c estimate
uses the ADAG (A1c-Derived Average Glucose) equation. Both are used here purely to shape
*recommendation rules*, not to produce diagnostic claims.

### 5.3 Recommendation Engine

The recommendation engine is intentionally **rule-based and transparent** rather than an
opaque ML model. For a treatment-support system operating close to a medical domain, the
ability to explain *why* a recommendation was produced is more valuable than marginal
accuracy gains, and it keeps the system firmly in the non-diagnostic category. Every
recommendation ships with a structured record:

```python
@dataclass
class Recommendation:
    category: str       # data_quality, glucose_level, variability, trend,
                        # positive, lifestyle, reminder, safety
    severity: str       # info | low | medium | high
    title: str
    message: str        # user-facing, safe, non-diagnostic
    explanation: str    # "Why": the concrete feature values that triggered this
    confidence: float   # 0.0 – 1.0, reflects rule reliability
    rule_id: str        # e.g. "GLU_001" for audit / iteration
```

The current ruleset:

| Rule ID      | Category       | Trigger                                                     |
|--------------|----------------|-------------------------------------------------------------|
| DATA_001/002 | data_quality   | No data / fewer than 3 days of features                     |
| DATA_003     | data_quality   | Recent readings/day < 100 (sensor coverage low)             |
| GLU_001      | glucose_level  | 7-day mean ≥ 200 mg/dL → escalation to care team            |
| GLU_002      | glucose_level  | 7-day mean ≥ 170 mg/dL → lifestyle review                   |
| GLU_003      | glucose_level  | Most recent day time-below-range ≥ 4%                       |
| GLU_004      | glucose_level  | 7-day average time-in-range < 50%                           |
| SAFETY_001   | safety         | Any reading below 54 mg/dL in history                       |
| VAR_001      | variability    | 7-day average CV% ≥ 36% (ATTD variability threshold)        |
| TREND_001    | trend          | 14-day slope ≥ +3 mg/dL per day                             |
| TREND_002    | trend          | 14-day slope ≤ −3 mg/dL per day                             |
| POS_001      | positive       | 7-day average TIR ≥ 70% → positive reinforcement            |
| LIFE_001     | lifestyle      | ≥ 4 of last 7 days had a max reading > 220 mg/dL            |
| REM_001      | reminder       | Recent day mean ≥ 200 → hydration reminder                  |

Rules are evaluated independently and deduplicated by `rule_id`, keeping the highest
severity version. One failing rule never breaks the others — the engine logs the
exception and continues.

---

## 6. Implementation

The backend is a standard FastAPI application with four routers (`ingestion`, `features`,
`recommendations`, `dashboard`) and three service modules (`parser`, `feature_engineering`,
`recommender`). SQLAlchemy 2.0-style ORM models define five tables:

- `users` — seeded with a `default` user on first request (multi-user scaffolding)
- `import_jobs` — audit log of every upload with status, counts, and errors
- `raw_sensor_events` — every parsed glucose reading with uniqueness on (user, timestamp, source)
- `daily_features` — engineered per-day features with uniqueness on (user, day)
- `recommendations_log` — every recommendation ever emitted, with full explanation metadata

The frontend is a Vite + React app with four pages (Dashboard, Upload, Trends, Recommendations),
four reusable components, and a single `api.js` client that talks to the backend via a Vite
dev-server proxy. Recharts is used for the time-series visualisations, with a coloured reference
band marking the 70–180 mg/dL target range on every chart.

Key engineering choices:

- **SQLite by default, PostgreSQL via env var** — the system runs with zero external
  dependencies out of the box, but swapping to Postgres is a single `DATABASE_URL` change.
- **Dedup-on-insert** — the parser may be called on overlapping exports; the system
  guarantees idempotency through the unique constraint and an in-memory dedup pass.
- **Automatic recomputation** — every successful upload triggers feature recomputation and
  recommendation regeneration, so the dashboard is always in sync with the latest data.
- **Defensive rules** — recommendation rules are isolated; one failing rule logs and
  yields, the others still produce output.
- **CORS** — configured for local dev ports (5173, 3000) so the frontend works immediately.

---

## 7. Evaluation

The system was validated end-to-end using 21 days of synthetic CGM data designed to
exercise every recommendation rule:

| Intentionally embedded pattern          | Rule it exercises          |
|-----------------------------------------|----------------------------|
| Rising baseline in the last 7 days      | `TREND_001`, `GLU_001/002` |
| One day with injected random swings     | `VAR_001`                  |
| One day with 70% of readings dropped    | `DATA_003`                 |
| One day with a severe-low excursion     | `SAFETY_001`               |
| Many days with post-meal peaks > 220    | `LIFE_001`                 |
| Consistent TIR ≥ 70% in the first week  | `POS_001` (early window)   |

Running the pipeline on this dataset produced daily feature outputs that match
hand-computed reference values (verified during development) and recommendations that
fire on the expected day-windows. The parser was additionally validated against the
bundled JSON export (same data, different format) and produced byte-identical downstream
results, confirming that the ingestion layer is format-agnostic from the storage layer
onward.

Performance: ingesting ~2,000 readings plus full feature recomputation and rule
evaluation completes in well under a second on the development machine.

---

## 8. Limitations

1. **Rule-based, not learned.** The recommendation engine is intentionally hand-crafted.
   It does not adapt to individual baselines beyond the configurable reference thresholds.
   This is a trade-off we deliberately chose for explainability and safety; a future
   version could layer a learned component for *personalisation* while keeping the
   rule engine as a safety floor.
2. **Single-user by design.** The schema supports multi-user, but only a `default` user
   is auto-created. Authentication is out of scope for this project.
3. **No live streaming.** Because of the Libre 3 Plus access constraint, data arrives in
   batches. The worst-case staleness is the interval between manual exports.
4. **Estimated A1c ≠ clinical A1c.** The ADAG-based estimate is useful as a monitoring
   proxy but must not be presented as a lab value.
5. **English-only UI copy.** Recommendation text is currently only in English.
6. **No medication or carb integration.** The Libre export may contain insulin or carb
   events; the current parser ignores them by design (non-diagnostic scope).

---

## 9. Future Work

- **Live ingestion worker** when/if real-time sensor access becomes available —
  the only component that needs to change.
- **Personalised baselines** — replace fixed thresholds with per-user rolling baselines.
- **Clinician-share view** — read-only export of the dashboard to send to a care team.
- **Pattern mining** — unsupervised detection of time-of-day glycemic patterns
  (e.g., consistent post-dinner spikes).
- **Multi-language** recommendation text.
- **Auth + multi-user** with per-user data isolation and sharing controls.
- **Alerting channel** (email/push) for high-severity recommendations.

---

## 10. Conclusion

This project delivers a fully integrated, end-to-end Medical IoT recommender system for
Type 2 Diabetes treatment support. Rather than mocking components, every layer is
implemented and working: ingestion parses real-world Libre exports, features are
computed with standard data-science tooling, recommendations are generated by a
transparent rule engine with full explainability, and a React dashboard surfaces
everything to the user. Most importantly, the architecture is **honest about the
data-access constraint** imposed by the FreeStyle Libre 3 Plus and is intentionally
designed so that replacing batched app exports with live sensor streaming later on
requires only a new ingestion worker — the rest of the system is already ready.
