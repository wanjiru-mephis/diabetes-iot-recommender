# Diabetes IoT Recommender System

An **AI-assisted, non-diagnostic, treatment-support system** for Type 2 Diabetes built around
CGM (Continuous Glucose Monitor) data. Specifically designed around the **FreeStyle Libre 3 Plus**
constraint that real-time sensor access is not reliably available to third-party apps — so the
system ingests **app-exported glucose data (CSV/JSON)** as its primary data source.

The architecture is production-shaped: ingestion → storage → feature engineering →
rule-based recommendation engine → React dashboard. When real sensor streaming becomes
available, **the only thing that needs to change is the ingestion source** — everything
downstream is already wired up.

> ⚠️ **Non-diagnostic.** This system does not diagnose, prescribe, or dose. It produces
> reminders, lifestyle nudges, data-quality prompts, and escalation guidance only.

---

## 1. Architecture

```
┌──────────────┐    ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐
│ Libre App    │───▶│  Ingestion  │───▶│  Storage     │───▶│ Feature          │
│ CSV / JSON   │    │  (FastAPI)  │    │ (Postgres /  │    │ Engineering      │
│ export       │    │  /upload    │    │  SQLite)     │    │ (pandas/numpy)   │
└──────────────┘    └─────────────┘    └──────────────┘    └──────────────────┘
                                                                     │
                                                                     ▼
                          ┌──────────────┐    ┌───────────────────────────────┐
                          │ React UI     │◀───│ Rule-based Recommendation     │
                          │ (Vite +      │    │ Engine                        │
                          │  Recharts)   │    │ (non-diagnostic, explainable) │
                          └──────────────┘    └───────────────────────────────┘
```

- **Sensing (App Export)** — FreeStyle Libre 3 Plus companion app exports glucose history as CSV/JSON.
- **Ingestion** — `POST /api/ingest/upload` parses, validates, deduplicates, and stores.
- **Storage** — SQLAlchemy ORM with SQLite (default, zero setup) or PostgreSQL (via env var).
- **Feature Engineering** — Per-day aggregates, rolling 3/7-day means, variability (CV%),
  time-in-range, trend slope, estimated A1c.
- **Recommendation Engine** — Transparent, rule-based engine with `category`, `severity`,
  `explanation`, `confidence`, and `rule_id` on every output.
- **Dashboard** — React + Vite + Recharts: summary cards, trends, upload, recommendations.

See `docs/REPORT.md` for the full methodology and `docs/DEMO_SCRIPT.md` for the presentation walkthrough.

---

## 2. Project Structure

```
diabetes-iot-recommender/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app + CORS + routers
│   │   ├── config.py               # Settings (DATABASE_URL, ranges)
│   │   ├── database.py             # SQLAlchemy engine & session
│   │   ├── logging_config.py       # Central logging
│   │   ├── models.py               # ORM: users, raw_sensor_events,
│   │   │                           #      daily_features, recommendations_log,
│   │   │                           #      import_jobs
│   │   ├── schemas.py              # Pydantic schemas
│   │   ├── routers/
│   │   │   ├── ingestion.py        # POST /api/ingest/upload, /jobs
│   │   │   ├── features.py         # GET  /api/features/daily, /raw, /recompute
│   │   │   ├── recommendations.py  # GET  /api/recommendations, POST /regenerate
│   │   │   └── dashboard.py        # GET  /api/dashboard/summary
│   │   └── services/
│   │       ├── parser.py           # Libre CSV/JSON parser
│   │       ├── feature_engineering.py
│   │       └── recommender.py      # Rule-based engine
│   ├── requirements.txt
│   ├── run.py
│   └── .env.example
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api.js
│       ├── styles.css
│       ├── components/
│       │   ├── SummaryCard.jsx
│       │   ├── GlucoseChart.jsx
│       │   ├── RecommendationList.jsx
│       │   └── UploadForm.jsx
│       └── pages/
│           ├── Dashboard.jsx
│           ├── Upload.jsx
│           ├── Trends.jsx
│           └── Recommendations.jsx
├── sample_data/
│   ├── libre_export_sample.csv     # 21 days, Libre-format
│   └── libre_export_sample.json    # Same data, JSON
├── scripts/
│   ├── generate_sample_data.py
│   └── init_db.py
├── docs/
│   ├── REPORT.md
│   └── DEMO_SCRIPT.md
└── README.md
```

---

## 3. Setup — Backend

### Prerequisites
- Python 3.10+
- pip

### Steps

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

The system uses **SQLite by default** — no database setup required. To use PostgreSQL instead:

```bash
cp .env.example .env
# Edit .env: DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/diabetes_iot
```

### Run the backend

```bash
python run.py
# OR
uvicorn app.main:app --reload --port 8000
```

Backend runs at **http://localhost:8000**.
Interactive API docs: **http://localhost:8000/docs**.
Tables are created automatically on first run.

---

## 4. Setup — Frontend

### Prerequisites
- Node.js 18+
- npm (or pnpm/yarn)

### Steps

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**. Vite proxies `/api/*` to the backend, so as long
as the backend is running on port 8000 everything connects automatically.

---

## 5. Importing Data

### Option A: Use the bundled sample data

1. Start both backend and frontend.
2. Go to **Upload Data** in the sidebar.
3. Drag-and-drop `sample_data/libre_export_sample.csv` (or the `.json` file).
4. Navigate to **Dashboard**, **Trends**, and **Recommendations** — you should see 21 days of data
   with multiple active recommendations.

### Option B: Regenerate sample data

```bash
python scripts/generate_sample_data.py
```
This writes 21 days of realistic ~15-minute-interval readings with diurnal patterns,
post-meal spikes, a dawn-phenomenon rise, one high-variability day, one low-coverage day,
a severe-low excursion, and a rising trend across the last week — which exercises every
recommendation rule.

### Option C: Use a real FreeStyle Libre export

1. In the Libre companion app: **Menu → Connected Apps → LibreView → download glucose report**.
2. Export as CSV.
3. Upload through the **Upload Data** page.
4. The parser auto-detects Libre header rows; no code change required.

---

## 6. Testing the System

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Upload the CSV via curl
curl -X POST http://localhost:8000/api/ingest/upload \
     -F "file=@sample_data/libre_export_sample.csv"

# 3. Check summary
curl http://localhost:8000/api/dashboard/summary

# 4. Daily features
curl http://localhost:8000/api/features/daily?limit=10

# 5. Recommendations
curl http://localhost:8000/api/recommendations
```

---

## 7. API Reference (quick)

| Method | Endpoint                              | Purpose                               |
|--------|---------------------------------------|---------------------------------------|
| GET    | `/`                                   | Root info + disclaimer                |
| GET    | `/health`                             | Health check                          |
| POST   | `/api/ingest/upload`                  | Upload CSV/JSON glucose export        |
| GET    | `/api/ingest/jobs`                    | List past import jobs                 |
| GET    | `/api/features/daily?limit=30`        | Daily engineered features             |
| GET    | `/api/features/raw?hours=48`          | Raw readings window                   |
| POST   | `/api/features/recompute`             | Force feature recomputation           |
| GET    | `/api/recommendations`                | List recommendations                  |
| POST   | `/api/recommendations/regenerate`     | Regenerate from current features      |
| GET    | `/api/dashboard/summary`              | High-level dashboard summary          |

---

## 8. Replacing Sample Data with Real Sensor Data Later

The architecture deliberately isolates the sensing layer. To migrate from
app-export ingestion to live sensor streaming (e.g., via a BLE bridge or
partner API):

1. Write a new ingestion worker that produces `ParsedEvent` objects
   (see `backend/app/services/parser.py`).
2. Insert those events into `raw_sensor_events` using the same dedup rules.
3. Call `recompute_daily_features(db, user_id)` and
   `generate_recommendations(db, user_id)`.

**Zero changes are required** in the storage schema, feature engineering,
recommendation engine, or frontend.

---

## 9. License & Disclaimer

This project is provided for **educational and research purposes**. It is **not a medical device**,
is **not FDA/CE cleared**, and **must not be used** to make clinical decisions. Always consult a
qualified healthcare professional regarding diabetes management.
