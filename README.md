# WealthPortal Client Report Portal

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
