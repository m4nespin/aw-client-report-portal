from datetime import date
from contextlib import asynccontextmanager
import json
from math import ceil
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from .calculations import AccountValue, LiabilityValue, TrustValue, calculate_household_summary, calculate_sacs
from .database import SessionLocal, create_db, get_db
from .models import Account, Client, GeneratedReport, Liability, ReportRun, TrustAsset
from .pdf import file_size, generate_sacs_pdf, generate_tcc_pdf, report_paths
from .schemas import (
    ClientDetail,
    ClientListItem,
    ClientListResponse,
    GeneratedReportOut,
    ReportRunCreate,
    ReportRunCreated,
    ReportRunOut,
)
from .seed import seed_if_empty


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db()
    with SessionLocal() as db:
        seed_if_empty(db)
    yield


app = FastAPI(title="WealthPortal Client Report Portal", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_client(db: Session, client_id: str) -> Client:
    client = db.scalar(
        select(Client)
        .where(Client.id == client_id)
        .options(
            selectinload(Client.members),
            selectinload(Client.accounts),
            selectinload(Client.liabilities),
            selectinload(Client.trust_assets),
            selectinload(Client.report_runs).selectinload(ReportRun.generated_reports),
        )
    )
    if not client:
        raise HTTPException(status_code=404, detail={"code": "client_not_found", "message": "Client not found."})
    return client


def summary_for(client: Client) -> dict:
    return calculate_household_summary(
        [AccountValue(owner=a.owner, category=a.category, balance=a.balance) for a in client.accounts],
        [LiabilityValue(balance=item.balance) for item in client.liabilities],
        [TrustValue(value=item.value) for item in client.trust_assets],
    )


def readiness_for(client: Client) -> str:
    if not client.accounts:
        return "Missing accounts"
    if not client.members:
        return "Missing household"
    if client.status == "Waiting on Data":
        return "Waiting on data"
    return "Ready"


def run_out(run: ReportRun) -> ReportRunOut:
    snapshot = json.loads(run.calculation_snapshot or "{}")
    return ReportRunOut(
        id=run.id,
        quarter=run.quarter,
        meeting_date=run.meeting_date,
        status=run.status,
        monthly_inflow=run.monthly_inflow,
        monthly_outflow=run.monthly_outflow,
        deductibles=run.deductibles,
        private_reserve_balance=run.private_reserve_balance,
        investment_account_balance=run.investment_account_balance,
        calculation_snapshot=snapshot,
        notes=run.notes,
        created_at=run.created_at,
        generated_reports=[GeneratedReportOut.model_validate(report) for report in run.generated_reports],
    )


def detail_out(client: Client) -> ClientDetail:
    return ClientDetail(
        id=client.id,
        household_name=client.household_name,
        primary_contact=client.primary_contact,
        status=client.status,
        tier=client.tier,
        assigned_team_member=client.assigned_team_member,
        next_meeting_date=client.next_meeting_date,
        last_report_date=client.last_report_date,
        notes=client.notes,
        members=client.members,
        accounts=client.accounts,
        liabilities=client.liabilities,
        trust_assets=client.trust_assets,
        report_runs=[run_out(run) for run in sorted(client.report_runs, key=lambda item: item.created_at, reverse=True)],
        summary=summary_for(client),
        readiness_status=readiness_for(client),
    )


def list_item_out(client: Client) -> ClientListItem:
    summary = summary_for(client)
    return ClientListItem(
        id=client.id,
        household_name=client.household_name,
        primary_contact=client.primary_contact,
        status=client.status,
        tier=client.tier,
        assigned_team_member=client.assigned_team_member,
        next_meeting_date=client.next_meeting_date,
        last_report_date=client.last_report_date,
        member_count=len(client.members),
        account_count=len(client.accounts),
        report_count=len(client.report_runs),
        total_assets=float(summary["grand_total"]),
        liabilities_total=float(summary["liabilities_total"]),
        net_worth_after_liabilities=float(summary["net_worth_after_liabilities"]),
        readiness_status=readiness_for(client),
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/clients", response_model=ClientListResponse)
def list_clients(
    db: Session = Depends(get_db),
    search: str = "",
    status: str = "",
    tier: str = "",
    assigned_team_member: str = "",
    missing_data: bool = False,
    sort_by: str = Query("next_meeting_date", pattern="^(household_name|status|tier|next_meeting_date|last_report_date)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=5, le=100),
) -> ClientListResponse:
    stmt: Select[tuple[Client]] = select(Client)
    if search:
        needle = f"%{search.lower()}%"
        stmt = stmt.where(or_(func.lower(Client.household_name).like(needle), func.lower(Client.primary_contact).like(needle)))
    if status:
        stmt = stmt.where(Client.status == status)
    if tier:
        stmt = stmt.where(Client.tier == tier)
    if assigned_team_member:
        stmt = stmt.where(Client.assigned_team_member == assigned_team_member)
    if missing_data:
        stmt = stmt.where(or_(Client.last_report_date.is_(None), Client.status == "Waiting on Data"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = getattr(Client, sort_by)
    stmt = stmt.order_by(column.desc() if sort_dir == "desc" else column.asc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    clients = db.scalars(
        stmt.options(
            selectinload(Client.members),
            selectinload(Client.accounts),
            selectinload(Client.liabilities),
            selectinload(Client.trust_assets),
            selectinload(Client.report_runs),
        )
    ).all()
    return ClientListResponse(
        items=[list_item_out(client) for client in clients],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, ceil(total / page_size)),
    )


@app.get("/api/meta")
def meta(db: Session = Depends(get_db)) -> dict[str, list[str]]:
    statuses = db.scalars(select(Client.status).distinct().order_by(Client.status)).all()
    tiers = db.scalars(select(Client.tier).distinct().order_by(Client.tier)).all()
    team = db.scalars(select(Client.assigned_team_member).distinct().order_by(Client.assigned_team_member)).all()
    return {"statuses": statuses, "tiers": tiers, "team": team}


@app.get("/api/clients/{client_id}", response_model=ClientDetail)
def get_client(client_id: str, db: Session = Depends(get_db)) -> ClientDetail:
    return detail_out(load_client(db, client_id))


@app.get("/api/clients/{client_id}/report-prefill")
def report_prefill(client_id: str, db: Session = Depends(get_db)) -> dict:
    client = load_client(db, client_id)
    latest = client.report_runs[0] if client.report_runs else None
    return {
        "quarter": f"{date.today().year} Q{((date.today().month - 1) // 3) + 1}",
        "meeting_date": client.next_meeting_date,
        "monthly_inflow": latest.monthly_inflow if latest else 25000,
        "monthly_outflow": latest.monthly_outflow if latest else 16000,
        "deductibles": latest.deductibles if latest else 4500,
        "private_reserve_balance": latest.private_reserve_balance if latest else 95000,
        "investment_account_balance": latest.investment_account_balance if latest else 350000,
        "account_updates": [{"id": account.id, "balance": account.balance} for account in client.accounts],
        "liability_updates": [{"id": item.id, "balance": item.balance} for item in client.liabilities],
        "trust_asset_updates": [{"id": item.id, "value": item.value} for item in client.trust_assets],
    }


@app.post("/api/clients/{client_id}/report-runs", response_model=ReportRunCreated, status_code=201)
def create_report_run(client_id: str, payload: ReportRunCreate, db: Session = Depends(get_db)) -> ReportRunCreated:
    client = load_client(db, client_id)
    account_by_id = {account.id: account for account in client.accounts}
    liability_by_id = {item.id: item for item in client.liabilities}
    trust_by_id = {item.id: item for item in client.trust_assets}

    for update in payload.account_updates:
        if update.id not in account_by_id:
            raise HTTPException(status_code=422, detail={"code": "unknown_account", "message": "Account update target was not found."})
        account_by_id[update.id].balance = update.balance
        account_by_id[update.id].as_of_date = date.today()
    for update in payload.liability_updates:
        if update.id not in liability_by_id:
            raise HTTPException(status_code=422, detail={"code": "unknown_liability", "message": "Liability update target was not found."})
        liability_by_id[update.id].balance = update.balance
        liability_by_id[update.id].as_of_date = date.today()
    for update in payload.trust_asset_updates:
        if update.id not in trust_by_id:
            raise HTTPException(status_code=422, detail={"code": "unknown_trust_asset", "message": "Trust update target was not found."})
        trust_by_id[update.id].value = update.value
        trust_by_id[update.id].as_of_date = date.today()

    snapshot = {
        "sacs": calculate_sacs(
            payload.monthly_inflow,
            payload.monthly_outflow,
            payload.deductibles,
            payload.private_reserve_balance,
        ),
        "household": summary_for(client),
    }
    run = ReportRun(
        client_id=client.id,
        quarter=payload.quarter,
        meeting_date=payload.meeting_date,
        monthly_inflow=payload.monthly_inflow,
        monthly_outflow=payload.monthly_outflow,
        deductibles=payload.deductibles,
        private_reserve_balance=payload.private_reserve_balance,
        investment_account_balance=payload.investment_account_balance,
        notes=payload.notes,
        calculation_snapshot=json.dumps(snapshot),
    )
    db.add(run)
    db.flush()

    sacs_path, tcc_path = report_paths(client, run)
    generate_sacs_pdf(client, run, snapshot, sacs_path)
    generate_tcc_pdf(client, run, snapshot, list(client.accounts), list(client.liabilities), list(client.trust_assets), tcc_path)
    db.add_all(
        [
            GeneratedReport(
                report_run_id=run.id,
                client_id=client.id,
                report_type="SACS",
                filename=sacs_path.name,
                file_path=str(sacs_path),
                size_bytes=file_size(sacs_path),
            ),
            GeneratedReport(
                report_run_id=run.id,
                client_id=client.id,
                report_type="TCC",
                filename=tcc_path.name,
                file_path=str(tcc_path),
                size_bytes=file_size(tcc_path),
            ),
        ]
    )
    client.last_report_date = date.today()
    if client.status in {"Review Due", "Waiting on Data"}:
        client.status = "Draft Ready"
    db.commit()
    db.refresh(run)
    refreshed = load_client(db, client.id)
    return ReportRunCreated(report_run=run_out(run), client=detail_out(refreshed))


@app.get("/api/generated-reports/{report_id}/download")
def download_report(report_id: str, db: Session = Depends(get_db)) -> FileResponse:
    report = db.get(GeneratedReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail={"code": "report_not_found", "message": "Report not found."})
    path = Path(report.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail={"code": "report_file_missing", "message": "The report metadata exists, but the local file is missing."})
    return FileResponse(path, media_type="application/pdf", filename=report.filename)
