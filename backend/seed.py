from datetime import date, timedelta
import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Account, Client, GeneratedReport, HouseholdMember, Liability, ReportRun, TrustAsset

FIRST_NAMES = [
    "Avery",
    "Jordan",
    "Morgan",
    "Casey",
    "Taylor",
    "Riley",
    "Quinn",
    "Cameron",
    "Drew",
    "Harper",
    "Reese",
    "Parker",
    "Alex",
    "Blair",
    "Sage",
    "Rowan",
]
LAST_NAMES = [
    "Anderson",
    "Bennett",
    "Caldwell",
    "Diaz",
    "Ellis",
    "Foster",
    "Garcia",
    "Hayes",
    "Iverson",
    "Johnson",
    "Kaplan",
    "Lopez",
    "Miller",
    "Nguyen",
    "Ortiz",
    "Patel",
]
STATUSES = ["Active", "Review Due", "Waiting on Data", "Draft Ready"]
INSTITUTIONS = ["Pinnacle Bank", "Schwab", "Fidelity", "Vanguard", "Northern Trust"]
UNIQUE_CLIENT_COUNT = min(len(FIRST_NAMES), len(LAST_NAMES))


def seed_if_empty(db: Session, count: int = UNIQUE_CLIENT_COUNT) -> None:
    existing = db.scalar(select(Client.id).limit(1))
    if existing:
        return

    rng = random.Random(42)
    today = date.today()
    for idx in range(min(count, UNIQUE_CLIENT_COUNT)):
        last_name = LAST_NAMES[idx % len(LAST_NAMES)]
        primary = FIRST_NAMES[idx % len(FIRST_NAMES)]
        secondary = FIRST_NAMES[(idx + 5) % len(FIRST_NAMES)]
        client = Client(
            household_name=f"{last_name} Household",
            primary_contact=f"{primary} {last_name}",
            status=STATUSES[idx % len(STATUSES)],
            last_report_date=today - timedelta(days=(idx % 120) + 18) if idx % 4 != 0 else None,
            notes="Quarterly review cadence with manually entered balances.",
        )
        db.add(client)
        db.flush()

        db.add_all(
            [
                HouseholdMember(
                    client_id=client.id,
                    first_name=primary,
                    last_name=last_name,
                    relationship="Primary",
                    date_of_birth=date(1960 + (idx % 22), (idx % 12) + 1, (idx % 26) + 1),
                ),
                HouseholdMember(
                    client_id=client.id,
                    first_name=secondary,
                    last_name=last_name,
                    relationship="Spouse",
                    date_of_birth=date(1962 + (idx % 20), ((idx + 4) % 12) + 1, ((idx + 7) % 26) + 1),
                ),
            ]
        )

        retirement_count = 2 + idx % 4
        non_retirement_count = 2 + idx % 5
        for acct_idx in range(retirement_count):
            owner = "Primary" if acct_idx % 2 == 0 else "Spouse"
            db.add(
                Account(
                    client_id=client.id,
                    owner=owner,
                    category="retirement",
                    name=f"{owner} Retirement {acct_idx + 1}",
                    institution=INSTITUTIONS[(idx + acct_idx) % len(INSTITUTIONS)],
                    account_type=["IRA", "Roth IRA", "401(k)", "SEP IRA"][acct_idx % 4],
                    balance=round(rng.uniform(85000, 850000), 2),
                    as_of_date=today - timedelta(days=idx % 14),
                )
            )
        for acct_idx in range(non_retirement_count):
            db.add(
                Account(
                    client_id=client.id,
                    owner=["Joint", "Primary", "Spouse"][acct_idx % 3],
                    category="bank" if acct_idx == 0 else "non_retirement",
                    name=["Checking", "Brokerage", "Savings", "Private Reserve", "Taxable Portfolio"][acct_idx % 5],
                    institution=INSTITUTIONS[(idx + acct_idx + 2) % len(INSTITUTIONS)],
                    account_type=["Cash", "Brokerage", "Savings", "Money Market", "Taxable"][acct_idx % 5],
                    balance=round(rng.uniform(25000, 600000), 2),
                    as_of_date=today - timedelta(days=idx % 10),
                )
            )

        if idx % 3 != 1:
            db.add(
                TrustAsset(
                    client_id=client.id,
                    name="Family Trust",
                    value=round(rng.uniform(150000, 1250000), 2),
                    as_of_date=today - timedelta(days=idx % 21),
                )
            )

        for liability_idx in range(idx % 4):
            db.add(
                Liability(
                    client_id=client.id,
                    name=["Mortgage", "Credit Line", "Auto Loan"][liability_idx % 3],
                    liability_type=["Mortgage", "Line of Credit", "Loan"][liability_idx % 3],
                    balance=round(rng.uniform(15000, 420000), 2),
                    as_of_date=today - timedelta(days=idx % 16),
                )
            )

        if idx < 20:
            run = ReportRun(
                client_id=client.id,
                quarter="2026 Q1",
                meeting_date=today - timedelta(days=45),
                monthly_inflow=24000 + idx * 350,
                monthly_outflow=15500 + idx * 190,
                deductibles=4200,
                private_reserve_balance=90000 + idx * 1500,
                investment_account_balance=325000 + idx * 5000,
                calculation_snapshot="{}",
                notes="Seeded prior report.",
            )
            db.add(run)
            db.flush()
            db.add_all(
                [
                    GeneratedReport(
                        report_run_id=run.id,
                        client_id=client.id,
                        report_type="SACS",
                        filename=f"{client.household_name.replace(' ', '_')}_SACS_seed.pdf",
                        file_path="",
                        size_bytes=0,
                    ),
                    GeneratedReport(
                        report_run_id=run.id,
                        client_id=client.id,
                        report_type="TCC",
                        filename=f"{client.household_name.replace(' ', '_')}_TCC_seed.pdf",
                        file_path="",
                        size_bytes=0,
                    ),
                ]
            )

    db.commit()
