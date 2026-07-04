# Smoke Test

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
uvicorn app.main:app --reload --port 8000
```

Expected checks:

- `GET /api/health` returns `{"status":"ok"}`.
- `GET /api/datasets/samples` returns quarterly and monthly sample datasets.
- `GET /api/imf/indicators` returns curated IMF indicators.
- Regression, forecast, VAR, memo, and lesson endpoints return user-friendly JSON responses.

## Frontend

```bash
npm install
npm run dev
```

Open `http://localhost:5173`.

