# Client Report Portal

FastAPI, SQLite, and React prototype for managing client households, entering quarterly financial data, calculating report totals, and generating local SACS/TCC PDF reports.

## Backend

Use the checked-in virtual environment instead of global Python:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The backend creates `dev.db`, seeds fake households on first startup, and stores generated PDFs under `generated_reports/`.

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```

## Railway deployment

This repository is set up as one Railway web service:

- `Dockerfile` builds the React frontend and runs the FastAPI backend.
- `railway.json` tells Railway to use the Dockerfile and health check `/api/health`.
- The container starts Uvicorn on `0.0.0.0:$PORT`, which Railway provides.

Deploy from Railway by creating a new project from this GitHub repository. After the first deploy, generate a Railway domain from the service Networking settings.

For persistent SQLite data and generated PDFs, attach a Railway volume and set this service variable:

```text
APP_DATA_DIR=/data
```

Without a volume, Railway can still run the app, but `dev.db` and `generated_reports/` are stored on the container filesystem and should be treated as ephemeral.
