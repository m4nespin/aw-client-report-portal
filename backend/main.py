from datetime import date
from contextlib import asynccontextmanager
import json
from math import ceil
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.orm import Session, selectinload

from .calculations import AccountValue, LiabilityValue, TrustValue, calculate_household_summary, calculate_sacs
from .config import FRONTEND_DIST_DIR
from .database import SessionLocal, create_db, get_db
from .models import Account, Client, GeneratedReport, HouseholdMember, Liability, ReportRun, TrustAsset, new_id, utc_now
from .pdf import file_size, generate_sacs_pdf, generate_tcc_pdf, report_paths
from .schemas import (
    ClientCreate,
    ClientDetail,
    ClientListItem,
    ClientListResponse,
    ClientUpdate,
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


app = FastAPI(title="Client Report Portal", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
    ],
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


def member_name(member: HouseholdMember | None) -> str:
    if not member:
        return ""
    return f"{member.first_name} {member.last_name}".strip()


def primary_member(client: Client) -> HouseholdMember | None:
    return next((member for member in client.members if member.relationship.lower() == "primary"), None)


def spouse_member(client: Client) -> HouseholdMember | None:
    return next((member for member in client.members if member.relationship.lower() == "spouse"), None)


def visible_household_members(client: Client) -> list[HouseholdMember]:
    return [member for member in (primary_member(client), spouse_member(client)) if member]


def readiness_for(client: Client) -> str:
    if not client.accounts:
        return "Missing accounts"
    if not primary_member(client) or not spouse_member(client):
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
    primary = primary_member(client)
    spouse = spouse_member(client)
    return ClientDetail(
        id=client.id,
        household_name=client.household_name,
        primary_contact=member_name(primary) or client.primary_contact,
        spouse_contact=member_name(spouse),
        status=client.status,
        last_report_date=client.last_report_date,
        notes=client.notes,
        members=visible_household_members(client),
        accounts=client.accounts,
        liabilities=client.liabilities,
        trust_assets=client.trust_assets,
        report_runs=[run_out(run) for run in sorted(client.report_runs, key=lambda item: item.created_at, reverse=True)],
        summary=summary_for(client),
        readiness_status=readiness_for(client),
    )


def list_item_out(client: Client) -> ClientListItem:
    summary = summary_for(client)
    primary = primary_member(client)
    spouse = spouse_member(client)
    return ClientListItem(
        id=client.id,
        household_name=client.household_name,
        primary_contact=member_name(primary) or client.primary_contact,
        spouse_contact=member_name(spouse),
        status=client.status,
        last_report_date=client.last_report_date,
        member_count=len(visible_household_members(client)),
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
    missing_data: bool = False,
    sort_by: str = Query("household_name", pattern="^(household_name|status|last_report_date)$"),
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
    return {"statuses": statuses}


@app.get("/api/clients/{client_id}", response_model=ClientDetail)
def get_client(client_id: str, db: Session = Depends(get_db)) -> ClientDetail:
    return detail_out(load_client(db, client_id))


def clean_required(value: str, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail={"code": "blank_field", "message": f"{field} cannot be blank."})
    return cleaned


def submitted_ids(items: list, label: str) -> set[str]:
    ids = [item.id for item in items if item.id]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail={"code": "duplicate_id", "message": f"{label} contains duplicate rows."})
    return set(ids)


def apply_client_payload(db: Session, client: Client, payload: ClientUpdate) -> None:
    client.household_name = clean_required(payload.household_name, "Household name")
    client.status = clean_required(payload.status, "Status")
    client.last_report_date = payload.last_report_date
    client.notes = payload.notes.strip()

    primary = primary_member(client)
    if not primary:
        primary = HouseholdMember(client_id=client.id, first_name="", last_name="", relationship="Primary")
        db.add(primary)
        client.members.append(primary)
    primary.first_name = clean_required(payload.primary_first_name, "Primary first name")
    primary.last_name = clean_required(payload.primary_last_name, "Primary last name")
    primary.relationship = "Primary"
    primary.date_of_birth = payload.primary_date_of_birth
    client.primary_contact = member_name(primary)

    spouse = spouse_member(client)
    if not spouse:
        spouse = HouseholdMember(client_id=client.id, first_name="", last_name="", relationship="Spouse")
        db.add(spouse)
        client.members.append(spouse)
    spouse.first_name = clean_required(payload.spouse_first_name, "Spouse first name")
    spouse.last_name = clean_required(payload.spouse_last_name, "Spouse last name")
    spouse.relationship = "Spouse"
    spouse.date_of_birth = payload.spouse_date_of_birth

    keep_ids = {primary.id, spouse.id}
    for member in list(client.members):
        if member.id not in keep_ids:
            db.delete(member)

    account_by_id = {account.id: account for account in client.accounts}
    account_ids = submitted_ids(payload.accounts, "Accounts")
    if unknown := account_ids - set(account_by_id):
        raise HTTPException(status_code=422, detail={"code": "unknown_account", "message": f"Unknown account row: {sorted(unknown)[0]}."})
    for account in list(client.accounts):
        if account.id not in account_ids:
            db.delete(account)
    for item in payload.accounts:
        account = account_by_id[item.id] if item.id else Account(client_id=client.id)
        if not item.id:
            db.add(account)
        account.owner = clean_required(item.owner, "Account owner")
        account.category = clean_required(item.category, "Account category")
        account.name = clean_required(item.name, "Account name")
        account.institution = clean_required(item.institution, "Account institution")
        account.account_type = clean_required(item.account_type, "Account type")
        account.balance = item.balance
        account.as_of_date = item.as_of_date

    liability_by_id = {liability.id: liability for liability in client.liabilities}
    liability_ids = submitted_ids(payload.liabilities, "Liabilities")
    if unknown := liability_ids - set(liability_by_id):
        raise HTTPException(status_code=422, detail={"code": "unknown_liability", "message": f"Unknown liability row: {sorted(unknown)[0]}."})
    for liability in list(client.liabilities):
        if liability.id not in liability_ids:
            db.delete(liability)
    for item in payload.liabilities:
        liability = liability_by_id[item.id] if item.id else Liability(client_id=client.id)
        if not item.id:
            db.add(liability)
        liability.name = clean_required(item.name, "Liability name")
        liability.liability_type = clean_required(item.liability_type, "Liability type")
        liability.balance = item.balance
        liability.as_of_date = item.as_of_date

    trust_by_id = {asset.id: asset for asset in client.trust_assets}
    trust_ids = submitted_ids(payload.trust_assets, "Trust assets")
    if unknown := trust_ids - set(trust_by_id):
        raise HTTPException(status_code=422, detail={"code": "unknown_trust_asset", "message": f"Unknown trust asset row: {sorted(unknown)[0]}."})
    for asset in list(client.trust_assets):
        if asset.id not in trust_ids:
            db.delete(asset)
    for item in payload.trust_assets:
        asset = trust_by_id[item.id] if item.id else TrustAsset(client_id=client.id)
        if not item.id:
            db.add(asset)
        asset.name = clean_required(item.name, "Trust asset name")
        asset.value = item.value
        asset.as_of_date = item.as_of_date


def create_client_row(db: Session, payload: ClientCreate) -> Client:
    values = {
        "id": new_id(),
        "household_name": clean_required(payload.household_name, "Household name"),
        "primary_contact": f"{clean_required(payload.primary_first_name, 'Primary first name')} {clean_required(payload.primary_last_name, 'Primary last name')}",
        "status": clean_required(payload.status, "Status"),
        "last_report_date": payload.last_report_date,
        "notes": payload.notes.strip(),
        "created_at": utc_now(),
    }
    table_info = db.execute(text("PRAGMA table_info(clients)")).all()
    columns = [row[1] for row in table_info]
    legacy_defaults = {
        "tier": "Standard",
        "assigned_team_member": "",
        "next_meeting_date": None,
    }
    for column, value in legacy_defaults.items():
        if column in columns:
            values[column] = value

    insert_columns = [column for column in values if column in columns]
    db.execute(
        text(
            f"INSERT INTO clients ({', '.join(insert_columns)}) "
            f"VALUES ({', '.join(f':{column}' for column in insert_columns)})"
        ),
        {column: values[column] for column in insert_columns},
    )
    return load_client(db, values["id"])


@app.post("/api/clients", response_model=ClientDetail, status_code=201)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)) -> ClientDetail:
    client = create_client_row(db, payload)
    apply_client_payload(db, client, payload)
    db.commit()
    return detail_out(load_client(db, client.id))


@app.put("/api/clients/{client_id}", response_model=ClientDetail)
def update_client(client_id: str, payload: ClientUpdate, db: Session = Depends(get_db)) -> ClientDetail:
    client = load_client(db, client_id)
    apply_client_payload(db, client, payload)
    db.commit()
    return detail_out(load_client(db, client.id))


@app.get("/api/clients/{client_id}/report-prefill")
def report_prefill(client_id: str, db: Session = Depends(get_db)) -> dict:
    client = load_client(db, client_id)
    latest = client.report_runs[0] if client.report_runs else None
    return {
        "quarter": f"{date.today().year} Q{((date.today().month - 1) // 3) + 1}",
        "meeting_date": latest.meeting_date if latest else date.today(),
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


def frontend_index_path() -> Path:
    index_path = FRONTEND_DIST_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail={"code": "frontend_not_built", "message": "Frontend build was not found."})
    return index_path


if (FRONTEND_DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST_DIR / "assets"), name="frontend-assets")


@app.get("/", include_in_schema=False)
def serve_frontend_root() -> FileResponse:
    return FileResponse(frontend_index_path())


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str) -> FileResponse:
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Not found."})

    requested_path = FRONTEND_DIST_DIR / full_path
    if requested_path.is_file():
        return FileResponse(requested_path)
    return FileResponse(frontend_index_path())
