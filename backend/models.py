from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from .database import Base


def new_id() -> str:
    return uuid4().hex


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_name: Mapped[str] = mapped_column(String(160), nullable=False)
    primary_contact: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Active")
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="Core")
    assigned_team_member: Mapped[str] = mapped_column(String(80), nullable=False)
    next_meeting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    members: Mapped[list["HouseholdMember"]] = orm_relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    accounts: Mapped[list["Account"]] = orm_relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    liabilities: Mapped[list["Liability"]] = orm_relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    trust_assets: Mapped[list["TrustAsset"]] = orm_relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    report_runs: Mapped[list["ReportRun"]] = orm_relationship(
        back_populates="client", cascade="all, delete-orphan"
    )


Index("ix_clients_household_name", Client.household_name)
Index("ix_clients_status", Client.status)
Index("ix_clients_next_meeting_date", Client.next_meeting_date)
Index("ix_clients_last_report_date", Client.last_report_date)


class HouseholdMember(Base):
    __tablename__ = "household_members"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    relationship: Mapped[str] = mapped_column(String(50), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)

    client: Mapped[Client] = orm_relationship(back_populates="members")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(40), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    institution: Mapped[str] = mapped_column(String(120), nullable=False)
    account_type: Mapped[str] = mapped_column(String(80), nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    as_of_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    client: Mapped[Client] = orm_relationship(back_populates="accounts")


Index("ix_accounts_category", Account.category)


class Liability(Base):
    __tablename__ = "liabilities"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    liability_type: Mapped[str] = mapped_column(String(80), nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    as_of_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    client: Mapped[Client] = orm_relationship(back_populates="liabilities")


class TrustAsset(Base):
    __tablename__ = "trust_assets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    as_of_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    client: Mapped[Client] = orm_relationship(back_populates="trust_assets")


class ReportRun(Base):
    __tablename__ = "report_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    quarter: Mapped[str] = mapped_column(String(20), nullable=False)
    meeting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Generated")
    monthly_inflow: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_outflow: Mapped[float] = mapped_column(Float, nullable=False)
    deductibles: Mapped[float] = mapped_column(Float, nullable=False)
    private_reserve_balance: Mapped[float] = mapped_column(Float, nullable=False)
    investment_account_balance: Mapped[float] = mapped_column(Float, nullable=False)
    calculation_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    client: Mapped[Client] = orm_relationship(back_populates="report_runs")
    generated_reports: Mapped[list["GeneratedReport"]] = orm_relationship(
        back_populates="report_run", cascade="all, delete-orphan"
    )


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    report_run_id: Mapped[str] = mapped_column(ForeignKey("report_runs.id"), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)
    filename: Mapped[str] = mapped_column(String(180), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    report_run: Mapped[ReportRun] = orm_relationship(back_populates="generated_reports")
