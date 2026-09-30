# DataGuard AI — Data Quality & Anomaly Detection Platform

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-Isolation%20Forest-F7931E.svg)](https://scikit-learn.org/)
[![Tests](https://img.shields.io/badge/tests-52%20passed-brightgreen.svg)]()

**DataGuard AI** is a production-style, modular data quality assessment and anomaly detection platform. It accepts structured tabular datasets (such as CSV files), performs automated statistical profiling, enforces configurable quality validation rules, detects statistical outliers using unsupervised Machine Learning (Isolation Forest), calculates an overall Data Health Score (0–100), persists analysis history in PostgreSQL, and serves insights through RESTful APIs and containerized Docker services.

> **Portfolio highlight:** DataGuard AI demonstrates an end-to-end backend data product: API design, validation and profiling engines, applied ML, database persistence, containerization, and automated tests—all in one focused service.

## Why it matters

Poor data quietly damages dashboards, models, and business decisions. DataGuard AI makes quality checks repeatable: upload a CSV, receive a structured report, investigate anomalies, and retain analysis history for later comparison.

---

## Architecture Flow

```text
       Uploaded CSV Dataset
                │
                ▼
   ┌─────────────────────────┐
   │   1. Data Profiler      │ ──► Dimensions, dtypes, nulls, duplicates & column stats
   └─────────────────────────┘
                │
                ▼
   ┌─────────────────────────┐
   │   2. Quality Validator  │ ──► Schema, non-null, uniqueness & range assertions
   └─────────────────────────┘
                │
                ▼
   ┌─────────────────────────┐
   │   3. Isolation Forest   │ ──► Unsupervised ML outlier detection on numeric features
   └─────────────────────────┘
                │
                ▼
   ┌─────────────────────────┐
   │  4. Health Calculator   │ ──► 0–100 Weighted Health Score & Rule-Based Recommendations
   └─────────────────────────┘
                │
        ┌───────┴───────┐
        ▼               ▼
┌──────────────┐ ┌──────────────┐
│  PostgreSQL  │ │ FastAPI JSON │
│  (Database)  │ │  (Response)  │
└──────────────┘ └──────────────┘
```

---

## Features

* **Automated Data Profiling:** Automatically infers column data types (`numeric`, `categorical`, `boolean`, `datetime`, `unknown`), computes completeness rates, uniqueness metrics, descriptive statistics (min, max, mean, median, std, quartiles), and mode frequencies.
* **Data-Quality Validation:** Configurable rule engine checking mandatory non-null fields, column uniqueness, numeric thresholds (`amount >= 0`), allowed categorical values, and schema integrity.
* **Missing-Value & Duplicate Analysis:** Quantifies row duplicates and missing value percentages across dataset and column levels.
* **Unsupervised Anomaly Detection:** Applies Scikit-Learn's `IsolationForest` to identify statistically abnormal records across numeric features without requiring pre-labeled training data.
* **Dataset Health Score (0–100):** Weighted multi-factor score synthesizing completeness (30%), validation quality (30%), uniqueness (20%), and anomaly rate (20%), categorized into `EXCELLENT`, `GOOD`, `NEEDS_ATTENTION`, and `POOR`.
* **Actionable Rule-Based Recommendations:** Generates clear, non-LLM recommendations identifying specific columns requiring data cleaning, deduplication, or investigation.
* **PostgreSQL Storage:** Persists dataset metadata (`datasets` table) and full analysis report payloads (`reports` table) with relationships.
* **FastAPI REST APIs:** Modular API endpoints with Swagger UI documentation (`/docs`) and ReDoc (`/redoc`).
* **Docker Containerization:** Multi-container orchestration via Docker Compose running the API and PostgreSQL with persistent data volumes.

---

## Technology Stack

* **Programming Language:** Python 3.12+ (tested on Python 3.13)
* **Web Framework:** FastAPI, Uvicorn, Python-Multipart
* **Data Processing & ML:** Pandas, NumPy, Scikit-learn (Isolation Forest)
* **Database & ORM:** PostgreSQL 16, SQLAlchemy 2.0, psycopg2-binary
* **Validation & Schemas:** Pydantic v2 & Pydantic Settings
* **Containerization:** Docker & Docker Compose
* **Testing:** pytest & HTTPX
* **Version Control:** Git

---

## Project Structure

```text
dataguard-ai/
│
├── app/
│   ├── __init__.py               # Application package metadata
│   ├── main.py                   # FastAPI application & lifespan management
│   │
│   ├── api/                      # REST API routers
│   │   ├── __init__.py
│   │   ├── profile.py            # POST /profile
│   │   ├── validate.py           # POST /validate
│   │   ├── anomalies.py          # POST /anomalies
│   │   └── report.py             # POST /report, GET /reports, GET /reports/{id}
│   │
│   ├── core/                     # Core computational engines
│   │   ├── __init__.py
│   │   ├── config.py             # Environment configuration (Pydantic Settings)
│   │   ├── logging.py            # Structured console logging
│   │   ├── profiler.py           # Data Profiling Engine
│   │   ├── validator.py          # Data Validation Engine
│   │   ├── anomaly_detector.py   # Isolation Forest ML Engine
│   │   └── health_score.py       # Health Score & Recommendation Engine
│   │
│   ├── models/                   # SQLAlchemy ORM database models
│   │   ├── __init__.py
│   │   ├── dataset.py            # datasets table model
│   │   └── report.py             # reports table model
│   │
│   ├── schemas/                  # Pydantic data schemas
│   │   ├── __init__.py
│   │   ├── profiling.py          # Profiling schemas
│   │   ├── validation.py         # Validation schemas
│   │   ├── anomaly.py            # Anomaly schemas
│   │   ├── health.py             # Health score schemas
│   │   └── db.py                 # Persisted report schemas
│   │
│   ├── db/                       # Database session & engine setup
│   │   ├── __init__.py
│   │   └── database.py           # SQLAlchemy setup and table initialization
│   │
│   └── services/                 # Business logic services
│       └── __init__.py
│
├── data/
│   ├── .gitkeep
│   └── sample_transactions.csv   # 150 synthetic financial records for testing
│
├── tests/                        # Automated pytest suite (52 tests)
│   ├── __init__.py
│   ├── conftest.py               # Shared test database fixtures
│   ├── test_main.py              # Root and health endpoint tests
│   ├── test_profiler.py          # Profiling engine tests
│   ├── test_validator.py         # Validation engine tests
│   ├── test_anomaly_detector.py  # Anomaly detector tests
│   ├── test_health_score.py      # Health score calculator tests
│   └── test_database.py          # Persistence & retrieval tests
│
├── .dockerignore                 # Docker build ignore rules
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore rules
├── Dockerfile                    # Application container specification
├── docker-compose.yml            # Multi-container orchestration (API + Postgres)
├── pyproject.toml                # Project packaging & pytest settings
├── requirements.txt              # Pinned Python dependencies
└── README.md                     # Project documentation
```

---

## Running with Docker (Recommended)

DataGuard AI provides a complete multi-container setup with **PostgreSQL** and the **FastAPI application**.

### 1. Start Services

```bash
docker compose up --build -d
```

### 2. Access the Application

* **Interactive API Documentation (Swagger UI):** [http://localhost:8001/docs](http://localhost:8001/docs)
* **Alternative API Documentation (ReDoc):** [http://localhost:8001/redoc](http://localhost:8001/redoc)
* **Health Check Endpoint:** [http://localhost:8001/health](http://localhost:8001/health)

*(The API is exposed on host port `8001` and PostgreSQL on host port `5433` to prevent conflicts with local services).*

### 3. Stop Services

```bash
docker compose down
```

To stop and remove data volumes:

```bash
docker compose down -v
```

---

## Running Locally (Without Docker)

### 1. Create and Activate a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

*(If `DATABASE_URL` is not set, DataGuard AI defaults to local SQLite at `sqlite:///./data/dataguard.db`).*

### 4. Start the Application

```bash
uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) to explore and run every endpoint interactively.

---

## API Endpoints Guide

### 1. End-to-End Analysis & Persistence: `POST /report`

Uploads a CSV dataset, executes profiling, validation, and anomaly detection, computes the health score, and saves the report in PostgreSQL.

```bash
curl -X POST "http://localhost:8001/report" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@data/sample_transactions.csv"
```

#### Example Response:

```json
{
  "id": 1,
  "dataset_id": 1,
  "filename": "sample_transactions.csv",
  "created_at": "2026-09-11T06:52:44.364592",
  "health_score": 91.62,
  "status": "EXCELLENT",
  "summary": {
    "rows": 150,
    "columns": 8,
    "missing_values": 5,
    "duplicates": 2,
    "validation_violations": 6,
    "anomalies": 8
  },
  "score_breakdown": {
    "completeness_score": 99.58,
    "validation_score": 76.92,
    "uniqueness_score": 98.67,
    "anomaly_score": 94.67
  },
  "recommendations": [
    "Review and clean/impute 5 missing value(s) found in: amount, payment_method, city.",
    "Investigate and deduplicate 2 duplicate record(s) (1.33% of dataset).",
    "Resolve 3 failing validation quality rule(s) for: transaction_id (unique), amount (required), payment_method (required).",
    "Inspect 8 statistically anomalous transaction record(s) flagged by Isolation Forest."
  ]
}
```

### 2. List Saved Reports: `GET /reports`

Retrieves a summary list of all previously analyzed datasets in reverse chronological order:

```bash
curl -X GET "http://localhost:8001/reports"
```

### 3. Retrieve Report by ID: `GET /reports/{report_id}`

Fetches complete profiling, validation, and anomaly details for a specific stored report:

```bash
curl -X GET "http://localhost:8001/reports/1"
```

### 4. Direct Phase Endpoints

* **`POST /profile`:** Deep statistical profiling of column distributions and dtypes.
* **`POST /validate`:** Data quality rule verification.
* **`POST /anomalies`:** Unsupervised ML anomaly detection using Isolation Forest.

---

## Running Automated Tests

Run the full pytest suite:

```bash
pytest -v
```

*All 52 tests run against an isolated in-memory test database, ensuring zero dependencies on an external running PostgreSQL instance during test execution.*

---

## Limitations & Disclaimer

* **Portfolio / Demonstration Platform:** Built as a clean, intermediate-level portfolio project demonstrating backend software engineering, data quality pipelines, and applied machine learning principles.
* **Statistical Anomaly vs. Fraud:** The Isolation Forest model detects statistical deviations and unusual patterns (e.g. extreme values in numeric distributions). An anomaly flag **does not** imply confirmed financial fraud or malicious activity.

---

## Engineering practices

* **Automated verification:** A GitHub Actions workflow runs the test suite on Python 3.12 and 3.13 for every pull request and push to `main`.
* **Safe defaults:** Environment-specific settings live in `.env`; only the documented `.env.example` template is tracked.
* **Reproducible local stack:** Docker Compose provisions both the API and PostgreSQL with health checks and persistent storage.
* **Sample data only:** The included transaction data is synthetic. The repository ignores ad-hoc datasets and generated local database files.

## Roadmap

- [ ] Add authentication and role-based access controls.
- [ ] Support scheduled data-quality checks and alerting.
- [ ] Add drift detection between historical reports.
- [ ] Export reports as downloadable CSV and PDF artifacts.

## License

Released under the [MIT License](LICENSE).

## Author

Built by **Akshit Thakur** as a portfolio project focused on dependable data systems and applied machine learning.
