export type ClientListItem = {
  id: string;
  household_name: string;
  primary_contact: string;
  status: string;
  tier: string;
  assigned_team_member: string;
  next_meeting_date: string | null;
  last_report_date: string | null;
  member_count: number;
  account_count: number;
  report_count: number;
  total_assets: number;
  liabilities_total: number;
  net_worth_after_liabilities: number;
  readiness_status: string;
};

export type ClientListResponse = {
  items: ClientListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type HouseholdMember = {
  id: string;
  first_name: string;
  last_name: string;
  relationship: string;
  date_of_birth: string | null;
};

export type Account = {
  id: string;
  owner: string;
  category: string;
  name: string;
  institution: string;
  account_type: string;
  balance: number;
  as_of_date: string | null;
};

export type Liability = {
  id: string;
  name: string;
  liability_type: string;
  balance: number;
  as_of_date: string | null;
};

export type TrustAsset = {
  id: string;
  name: string;
  value: number;
  as_of_date: string | null;
};

export type GeneratedReport = {
  id: string;
  report_type: string;
  filename: string;
  size_bytes: number;
  created_at: string;
};

export type ReportRun = {
  id: string;
  quarter: string;
  meeting_date: string | null;
  status: string;
  monthly_inflow: number;
  monthly_outflow: number;
  deductibles: number;
  private_reserve_balance: number;
  investment_account_balance: number;
  calculation_snapshot: {
    sacs?: Record<string, number>;
    household?: Record<string, number | Record<string, number>>;
  };
  notes: string;
  created_at: string;
  generated_reports: GeneratedReport[];
};

export type ClientDetail = {
  id: string;
  household_name: string;
  primary_contact: string;
  status: string;
  tier: string;
  assigned_team_member: string;
  next_meeting_date: string | null;
  last_report_date: string | null;
  notes: string;
  members: HouseholdMember[];
  accounts: Account[];
  liabilities: Liability[];
  trust_assets: TrustAsset[];
  report_runs: ReportRun[];
  summary: {
    retirement_by_owner: Record<string, number>;
    retirement_total: number;
    non_retirement_total: number;
    trust_total: number;
    grand_total: number;
    liabilities_total: number;
    net_worth_after_liabilities: number;
  };
  readiness_status: string;
};

export type Meta = {
  statuses: string[];
  tiers: string[];
  team: string[];
};

export type ReportPrefill = {
  quarter: string;
  meeting_date: string | null;
  monthly_inflow: number;
  monthly_outflow: number;
  deductibles: number;
  private_reserve_balance: number;
  investment_account_balance: number;
  account_updates: { id: string; balance: number }[];
  liability_updates: { id: string; balance: number }[];
  trust_asset_updates: { id: string; value: number }[];
};

export type ReportPayload = ReportPrefill & {
  notes: string;
};
