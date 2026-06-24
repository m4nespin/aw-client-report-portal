from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class HouseholdMemberOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    relationship: str
    date_of_birth: date | None

    model_config = ConfigDict(from_attributes=True)


class AccountOut(BaseModel):
    id: str
    owner: str
    category: str
    name: str
    institution: str
    account_type: str
    balance: float
    as_of_date: date | None

    model_config = ConfigDict(from_attributes=True)


class LiabilityOut(BaseModel):
    id: str
    name: str
    liability_type: str
    balance: float
    as_of_date: date | None

    model_config = ConfigDict(from_attributes=True)


class TrustAssetOut(BaseModel):
    id: str
    name: str
    value: float
    as_of_date: date | None

    model_config = ConfigDict(from_attributes=True)


class GeneratedReportOut(BaseModel):
    id: str
    report_type: str
    filename: str
    size_bytes: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportRunOut(BaseModel):
    id: str
    quarter: str
    meeting_date: date | None
    status: str
    monthly_inflow: float
    monthly_outflow: float
    deductibles: float
    private_reserve_balance: float
    investment_account_balance: float
    calculation_snapshot: dict
    notes: str
    created_at: datetime
    generated_reports: list[GeneratedReportOut]


class ClientListItem(BaseModel):
    id: str
    household_name: str
    primary_contact: str
    spouse_contact: str
    status: str
    last_report_date: date | None
    member_count: int
    account_count: int
    report_count: int
    total_assets: float
    liabilities_total: float
    net_worth_after_liabilities: float
    readiness_status: str


class ClientListResponse(BaseModel):
    items: list[ClientListItem]
    total: int
    page: int
    page_size: int
    pages: int


class ClientDetail(BaseModel):
    id: str
    household_name: str
    primary_contact: str
    spouse_contact: str
    status: str
    last_report_date: date | None
    notes: str
    members: list[HouseholdMemberOut]
    accounts: list[AccountOut]
    liabilities: list[LiabilityOut]
    trust_assets: list[TrustAssetOut]
    report_runs: list[ReportRunOut]
    summary: dict
    readiness_status: str


class AccountClientUpdate(BaseModel):
    id: str | None = None
    owner: str = Field(min_length=1, max_length=40)
    category: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    institution: str = Field(min_length=1, max_length=120)
    account_type: str = Field(min_length=1, max_length=80)
    balance: float = Field(ge=0)
    as_of_date: date | None = None


class LiabilityClientUpdate(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1, max_length=120)
    liability_type: str = Field(min_length=1, max_length=80)
    balance: float = Field(ge=0)
    as_of_date: date | None = None


class TrustAssetClientUpdate(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1, max_length=120)
    value: float = Field(ge=0)
    as_of_date: date | None = None


class ClientUpdate(BaseModel):
    household_name: str = Field(min_length=1, max_length=160)
    status: str = Field(min_length=1, max_length=40)
    last_report_date: date | None = None
    primary_first_name: str = Field(min_length=1, max_length=80)
    primary_last_name: str = Field(min_length=1, max_length=80)
    primary_date_of_birth: date | None = None
    spouse_first_name: str = Field(min_length=1, max_length=80)
    spouse_last_name: str = Field(min_length=1, max_length=80)
    spouse_date_of_birth: date | None = None
    notes: str = Field(default="", max_length=5000)
    accounts: list[AccountClientUpdate] = Field(default_factory=list)
    liabilities: list[LiabilityClientUpdate] = Field(default_factory=list)
    trust_assets: list[TrustAssetClientUpdate] = Field(default_factory=list)


class BalanceUpdate(BaseModel):
    id: str
    balance: float = Field(ge=0)


class TrustAssetUpdate(BaseModel):
    id: str
    value: float = Field(ge=0)


class ReportRunCreate(BaseModel):
    quarter: str = Field(min_length=2, max_length=20)
    meeting_date: date | None = None
    monthly_inflow: float = Field(ge=0)
    monthly_outflow: float = Field(ge=0)
    deductibles: float = Field(ge=0)
    private_reserve_balance: float = Field(ge=0)
    investment_account_balance: float = Field(ge=0)
    notes: str = ""
    account_updates: list[BalanceUpdate] = Field(default_factory=list)
    liability_updates: list[BalanceUpdate] = Field(default_factory=list)
    trust_asset_updates: list[TrustAssetUpdate] = Field(default_factory=list)


class ReportRunCreated(BaseModel):
    report_run: ReportRunOut
    client: ClientDetail
