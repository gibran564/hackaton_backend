# Restaurant BI Platform — Backend

> FastAPI · Firestore · Redis · Celery · Bubble Intelligence

---

## Stack

| Layer | Tech |
|-------|------|
| API | FastAPI + Uvicorn |
| Persistence | Google Cloud Firestore |
| DB | Firebase / Firestore |
| Cache | Redis 7 |
| Tasks | Celery + Celery Beat |
| ML/BI | scikit-learn · XGBoost · SHAP |
| Storage | MinIO (S3-compatible) |
| Deploy | Docker + Nginx |

---

## Quick Start

```bash
# 1. Clone and enter
cd backend

# 2. Environment
cp .env.example .env
# Edit .env with your secrets

# 3. Run with Docker
cd docker
docker compose up --build

# API docs available at:
# http://localhost/docs
# http://localhost/redoc
```

---

## Local Development

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure Firebase/Firestore credentials and start Redis first, then:
uvicorn app.main:app --reload --port 8000
```

Firestore uses `VITE_FIREBASE_PROJECT_ID` for the project and
`GOOGLE_APPLICATION_CREDENTIALS` for the service account JSON path. If no
Google credentials are available, the app falls back to an in-memory repository
for local tests.

---

## Tests

```bash
pytest tests/ -v --cov=app
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register user |
| POST | `/api/v1/auth/login` | Login → tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/users/me` | Current user |
| GET/POST | `/api/v1/restaurants/` | Restaurant CRUD |
| POST | `/api/v1/restaurants/{id}/floors` | Create floor |
| GET | `/api/v1/floors/{id}/tables` | List tables |
| PATCH | `/api/v1/tables/{id}` | Update table status |
| POST | `/api/v1/reservations/` | Create reservation |
| GET | `/api/v1/reservations/` | My reservations |
| DELETE | `/api/v1/reservations/{id}` | Cancel reservation |
| GET/POST | `/api/v1/restaurants/{id}/menus` | Menu management |
| POST | `/api/v1/orders/` | Create order |
| PATCH | `/api/v1/orders/{id}/status` | Kitchen status update |
| POST | `/api/v1/analytics/bubble-insight` | Bubble Intelligence inference |
| GET | `/api/v1/analytics/dashboard/{id}` | Dashboard stats |
| WS | `/ws/tables` | Realtime table updates |
| WS | `/ws/orders` | Realtime kitchen updates |
| WS | `/ws/reservations` | Realtime reservation events |

---

## Bubble Intelligence Architecture

```
Context Input (25 features)
        ↓
┌───────────────────────────────┐
│  B1  Customer Flow    (GBR)   │  time_of_day, weather, holidays
│  B2  Consumption      (XGB)   │  order_value, categories
│  B3  Operations       (RF)    │  prep_time, staff_load
│  B4  Experience       (Ridge) │  ratings, cancellations
│  B5  Spatial          (XGB)   │  occupancy, table_positions
└───────────────────────────────┘
        ↓
   Meta-Collapser
   (weighted average + variance)
        ↓
  { occupancy_prediction, dominant_factor,
    uncertainty, shap_summary, recommendations }
```

---

## RBAC Roles

| Role | Access |
|------|--------|
| customer | Reservations only |
| waiter | Tables + Orders |
| kitchen | Order queue |
| cashier | Payments |
| manager | Analytics + All ops |
| admin | Full system access |

---

## Author

Christian Gibrán Espituñal Villanueva — v1.0
