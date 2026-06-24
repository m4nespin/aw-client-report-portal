import {
  ArrowDownUp,
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  Loader2,
  Search,
  SlidersHorizontal,
  UserRound,
  WalletCards
} from "lucide-react";
import { Fragment, FormEvent, useEffect, useMemo, useState } from "react";
import {
  createReportRun,
  getClient,
  getClients,
  getMeta,
  getReportPrefill,
  reportDownloadUrl
} from "./api";
import type {
  Account,
  ClientDetail,
  ClientListItem,
  ClientListResponse,
  Meta,
  ReportPayload,
  ReportPrefill
} from "./types";

type Filters = {
  search: string;
  status: string;
  tier: string;
  assigned_team_member: string;
  missing_data: boolean;
  sort_by: string;
  sort_dir: string;
  page: number;
  page_size: number;
};

type Route =
  | { name: "clients" }
  | { name: "client"; clientId: string }
  | { name: "report"; clientId: string };

const initialFilters: Filters = {
  search: "",
  status: "",
  tier: "",
  assigned_team_member: "",
  missing_data: false,
  sort_by: "next_meeting_date",
  sort_dir: "asc",
  page: 1,
  page_size: 25
};

function parseRoute(pathname: string): Route {
  const parts = pathname.split("/").filter(Boolean);
  if (parts[0] !== "clients") return { name: "clients" };
  if (parts[1] && parts[2] === "report") return { name: "report", clientId: parts[1] };
  if (parts[1]) return { name: "client", clientId: parts[1] };
  return { name: "clients" };
}

function currency(value: number | undefined) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  }).format(value ?? 0);
}

function shortDate(value: string | null) {
  if (!value) return "Not set";
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

function numberInput(value: number, onChange: (next: number) => void) {
  return (
    <input
      type="number"
      min="0"
      step="100"
      value={Number.isFinite(value) ? value : 0}
      onChange={(event) => onChange(Number(event.target.value))}
    />
  );
}

function statusTone(status: string) {
  if (status === "Ready" || status === "Draft Ready" || status === "Active") return "good";
  if (status.includes("Waiting") || status.includes("Missing")) return "warn";
  return "neutral";
}

function StatusPill({ value }: { value: string }) {
  return <span className={`status ${statusTone(value)}`}>{value}</span>;
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong className={accent}>{value}</strong>
    </div>
  );
}

function useClientList(filters: Filters) {
  const [data, setData] = useState<ClientListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== "" && value !== false) params.set(key, String(value));
      });
      setLoading(true);
      getClients(params)
        .then((next) => {
          setData(next);
          setError("");
        })
        .catch((err: Error) => setError(err.message))
        .finally(() => setLoading(false));
    }, 180);
    return () => window.clearTimeout(timer);
  }, [filters]);

  return { data, loading, error };
}

function useClientDetail(clientId: string) {
  const [client, setClient] = useState<ClientDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = () => {
    setLoading(true);
    getClient(clientId)
      .then((next) => {
        setClient(next);
        setError("");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
  }, [clientId]);

  return { client, setClient, loading, error, refresh };
}

function ClientTable({
  clients,
  onSelect
}: {
  clients: ClientListItem[];
  onSelect: (id: string) => void;
}) {
  return (
    <div className="table-wrap client-table">
      <table>
        <thead>
          <tr>
            <th>Household</th>
            <th>Owner</th>
            <th>Status</th>
            <th>Tier</th>
            <th>Next Meeting</th>
            <th>Assets</th>
            <th>Ready</th>
          </tr>
        </thead>
        <tbody>
          {clients.map((client) => (
            <tr key={client.id} onClick={() => onSelect(client.id)}>
              <td>
                <b>{client.household_name}</b>
                <span>{client.assigned_team_member}</span>
              </td>
              <td>{client.primary_contact}</td>
              <td><StatusPill value={client.status} /></td>
              <td>{client.tier}</td>
              <td>{shortDate(client.next_meeting_date)}</td>
              <td>{currency(client.total_assets)}</td>
              <td><StatusPill value={client.readiness_status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FiltersBar({
  filters,
  setFilters,
  meta
}: {
  filters: Filters;
  setFilters: (next: Filters) => void;
  meta: Meta | null;
}) {
  const patch = (next: Partial<Filters>) => setFilters({ ...filters, ...next, page: next.page ?? 1 });
  return (
    <section className="filters">
      <label className="search-box">
        <Search size={16} />
        <input
          value={filters.search}
          onChange={(event) => patch({ search: event.target.value })}
          placeholder="Search households"
        />
      </label>
      <select value={filters.status} onChange={(event) => patch({ status: event.target.value })}>
        <option value="">All statuses</option>
        {meta?.statuses.map((item) => <option key={item}>{item}</option>)}
      </select>
      <select value={filters.tier} onChange={(event) => patch({ tier: event.target.value })}>
        <option value="">All tiers</option>
        {meta?.tiers.map((item) => <option key={item}>{item}</option>)}
      </select>
      <select
        value={filters.assigned_team_member}
        onChange={(event) => patch({ assigned_team_member: event.target.value })}
      >
        <option value="">All advisors</option>
        {meta?.team.map((item) => <option key={item}>{item}</option>)}
      </select>
      <label className="check-row">
        <input
          type="checkbox"
          checked={filters.missing_data}
          onChange={(event) => patch({ missing_data: event.target.checked })}
        />
        Needs data
      </label>
      <label className="select-with-icon">
        <ArrowDownUp size={15} />
        <select value={filters.sort_by} onChange={(event) => patch({ sort_by: event.target.value })}>
          <option value="next_meeting_date">Next meeting</option>
          <option value="last_report_date">Last report</option>
          <option value="household_name">Household</option>
          <option value="status">Status</option>
          <option value="tier">Tier</option>
        </select>
      </label>
      <button
        className="icon-button"
        title="Toggle sort direction"
        onClick={() => patch({ sort_dir: filters.sort_dir === "asc" ? "desc" : "asc" })}
      >
        <SlidersHorizontal size={17} />
      </button>
    </section>
  );
}

function AccountTable({
  accounts,
  mode,
  values,
  setValue
}: {
  accounts: Account[];
  mode?: "edit";
  values?: Record<string, number>;
  setValue?: (id: string, value: number) => void;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Owner</th>
            <th>Account</th>
            <th>Institution</th>
            <th>Type</th>
            <th>Balance</th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((account) => (
            <tr key={account.id}>
              <td>{account.owner}</td>
              <td>{account.name}</td>
              <td>{account.institution}</td>
              <td>{account.account_type}</td>
              <td>
                {mode === "edit" && values && setValue
                  ? numberInput(values[account.id] ?? account.balance, (next) => setValue(account.id, next))
                  : currency(account.balance)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ClientsView({
  filters,
  setFilters,
  meta,
  navigate
}: {
  filters: Filters;
  setFilters: (next: Filters) => void;
  meta: Meta | null;
  navigate: (path: string) => void;
}) {
  const { data, loading, error } = useClientList(filters);
  const setPage = (page: number) => setFilters({ ...filters, page });

  return (
    <section className="view-shell command-center list-view">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Client Operations</p>
          <h1>Households</h1>
        </div>
        <span>{data?.total ?? 0} records</span>
      </div>
      <FiltersBar filters={filters} setFilters={setFilters} meta={meta} />
      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="loading-line"><Loader2 className="spin" size={17} /> Loading clients</div>}
      {data && (
        <>
          <ClientTable clients={data.items} onSelect={(id) => navigate(`/clients/${id}`)} />
          <div className="pager">
            <button className="icon-button" title="Previous page" disabled={data.page <= 1} onClick={() => setPage(data.page - 1)}>
              <ChevronLeft size={18} />
            </button>
            <span>Page {data.page} of {data.pages}</span>
            <button className="icon-button" title="Next page" disabled={data.page >= data.pages} onClick={() => setPage(data.page + 1)}>
              <ChevronRight size={18} />
            </button>
          </div>
        </>
      )}
    </section>
  );
}

function DetailView({
  client,
  loading,
  onBack,
  onOpenReport,
  onRefresh
}: {
  client: ClientDetail | null;
  loading: boolean;
  onBack: () => void;
  onOpenReport: () => void;
  onRefresh: () => void;
}) {
  if (loading) {
    return (
      <section className="view-shell detail empty-state">
        <Loader2 className="spin" />
      </section>
    );
  }
  if (!client) {
    return (
      <section className="view-shell detail empty-state">
        <button className="ghost-button" onClick={onBack}><ArrowLeft size={16} /> Clients</button>
        <span>No household selected.</span>
      </section>
    );
  }

  const retirementOwners = Object.entries(client.summary.retirement_by_owner);
  const latestRun = client.report_runs[0];

  return (
    <section className="view-shell detail">
      <div className="detail-header">
        <div>
          <button className="back-link" onClick={onBack}><ArrowLeft size={16} /> Clients</button>
          <p className="eyebrow">{client.tier} / {client.assigned_team_member}</p>
          <h1>{client.household_name}</h1>
          <div className="inline-facts">
            <span><UserRound size={15} /> {client.primary_contact}</span>
            <span><CalendarDays size={15} /> {shortDate(client.next_meeting_date)}</span>
            <StatusPill value={client.readiness_status} />
          </div>
        </div>
        <button className="primary-button" onClick={onOpenReport}>
          <FileText size={18} />
          Start Report
        </button>
      </div>

      <div className="metrics-grid">
        <Metric label="Grand Total" value={currency(client.summary.grand_total)} />
        <Metric label="Liabilities" value={currency(client.summary.liabilities_total)} accent="danger" />
        <Metric label="Net Worth" value={currency(client.summary.net_worth_after_liabilities)} accent="good-text" />
        <Metric label="Reports" value={`${client.report_runs.length}`} />
      </div>

      <div className="content-grid">
        <section className="panel">
          <h2>Household Members</h2>
          <div className="member-grid">
            {client.members.map((member) => (
              <div className="member" key={member.id}>
                <b>{member.first_name} {member.last_name}</b>
                <span>{member.relationship}</span>
                <span>{shortDate(member.date_of_birth)}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2>Capital Summary</h2>
          <div className="summary-list">
            <span>Retirement</span><b>{currency(client.summary.retirement_total)}</b>
            <span>Non-retirement</span><b>{currency(client.summary.non_retirement_total)}</b>
            <span>Trust assets</span><b>{currency(client.summary.trust_total)}</b>
            {retirementOwners.map(([owner, value]) => (
              <Fragment key={owner}><span>{owner} retirement</span><b>{currency(value)}</b></Fragment>
            ))}
          </div>
        </section>
      </div>

      <section className="panel">
        <div className="panel-title-row">
          <h2>Linked Accounts</h2>
          <span>{client.accounts.length} accounts</span>
        </div>
        <AccountTable accounts={client.accounts} />
      </section>

      <div className="content-grid">
        <section className="panel">
          <h2>Liabilities</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Name</th><th>Type</th><th>Balance</th></tr></thead>
              <tbody>
                {client.liabilities.length === 0 && <tr><td colSpan={3}>None entered</td></tr>}
                {client.liabilities.map((item) => (
                  <tr key={item.id}><td>{item.name}</td><td>{item.liability_type}</td><td>{currency(item.balance)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className="panel">
          <h2>Trust Assets</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Name</th><th>Value</th></tr></thead>
              <tbody>
                {client.trust_assets.length === 0 && <tr><td colSpan={2}>None entered</td></tr>}
                {client.trust_assets.map((item) => (
                  <tr key={item.id}><td>{item.name}</td><td>{currency(item.value)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <section className="panel">
        <div className="panel-title-row">
          <h2>Report History</h2>
          <button className="ghost-button" onClick={onRefresh}>Refresh</button>
        </div>
        <div className="history-list">
          {client.report_runs.length === 0 && <span>No report runs yet.</span>}
          {client.report_runs.map((run) => (
            <div className="history-row" key={run.id}>
              <div>
                <b>{run.quarter}</b>
                <span>{shortDate(run.created_at)} / Excess {currency(run.calculation_snapshot.sacs?.excess_transfer ?? 0)}</span>
              </div>
              <div className="download-group">
                {run.generated_reports.map((report) => (
                  <a className="icon-link" href={reportDownloadUrl(report.id)} key={report.id}>
                    <Download size={15} />
                    {report.report_type}
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>
        {latestRun && <p className="fine-print">Latest run: {latestRun.status} on {shortDate(latestRun.created_at)}</p>}
      </section>
    </section>
  );
}

function ClientDetailView({ clientId, navigate }: { clientId: string; navigate: (path: string) => void }) {
  const { client, loading, error, refresh } = useClientDetail(clientId);

  return (
    <>
      {error && <div className="toast error-banner">{error}</div>}
      <DetailView
        client={client}
        loading={loading}
        onBack={() => navigate("/clients")}
        onOpenReport={() => navigate(`/clients/${clientId}/report`)}
        onRefresh={refresh}
      />
    </>
  );
}

function ReportView({ clientId, navigate }: { clientId: string; navigate: (path: string) => void }) {
  const { client, setClient, loading: clientLoading, error: clientError } = useClientDetail(clientId);
  const [prefill, setPrefill] = useState<ReportPrefill | null>(null);
  const [payload, setPayload] = useState<ReportPayload | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
    setPrefill(null);
    setPayload(null);
    getReportPrefill(clientId)
      .then((next) => {
        setPrefill(next);
        setPayload({ ...next, notes: "" });
      })
      .catch((err: Error) => setError(err.message));
  }, [clientId]);

  const accountValues = useMemo(
    () => Object.fromEntries(payload?.account_updates.map((item) => [item.id, item.balance]) ?? []),
    [payload]
  );
  const liabilityValues = useMemo(
    () => Object.fromEntries(payload?.liability_updates.map((item) => [item.id, item.balance]) ?? []),
    [payload]
  );
  const trustValues = useMemo(
    () => Object.fromEntries(payload?.trust_asset_updates.map((item) => [item.id, item.value]) ?? []),
    [payload]
  );

  const patch = (next: Partial<ReportPayload>) => {
    if (!payload) return;
    setPayload({ ...payload, ...next });
  };

  const setAccountValue = (id: string, balance: number) => {
    if (!payload) return;
    patch({ account_updates: payload.account_updates.map((item) => item.id === id ? { ...item, balance } : item) });
  };

  const setLiabilityValue = (id: string, balance: number) => {
    if (!payload) return;
    patch({ liability_updates: payload.liability_updates.map((item) => item.id === id ? { ...item, balance } : item) });
  };

  const setTrustValue = (id: string, value: number) => {
    if (!payload) return;
    patch({ trust_asset_updates: payload.trust_asset_updates.map((item) => item.id === id ? { ...item, value } : item) });
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!payload) return;
    setSaving(true);
    setError("");
    createReportRun(clientId, payload)
      .then((result) => {
        setClient(result.client);
        navigate(`/clients/${result.client.id}`);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setSaving(false));
  };

  if (clientLoading || !prefill || !payload) {
    return (
      <section className="view-shell report-view empty-state">
        <Loader2 className="spin" />
      </section>
    );
  }

  if (!client) {
    return (
      <section className="view-shell report-view empty-state">
        <button className="ghost-button" onClick={() => navigate("/clients")}><ArrowLeft size={16} /> Clients</button>
        <span>{clientError || "Client not found."}</span>
      </section>
    );
  }

  return (
    <section className="view-shell report-view">
      <div className="detail-header">
        <div>
          <button className="back-link" onClick={() => navigate(`/clients/${client.id}`)}><ArrowLeft size={16} /> Client Details</button>
          <p className="eyebrow">{client.household_name}</p>
          <h1>Report Run</h1>
          <div className="inline-facts">
            <span><CalendarDays size={15} /> {shortDate(payload.meeting_date)}</span>
            <StatusPill value={client.readiness_status} />
          </div>
        </div>
      </div>

      <form onSubmit={onSubmit} className="report-form page-form">
        {(error || clientError) && <div className="error-banner">{error || clientError}</div>}
        <fieldset>
          <legend>Run Details</legend>
          <div className="field-grid">
            <label>Quarter<input value={payload.quarter} onChange={(event) => patch({ quarter: event.target.value })} /></label>
            <label>Meeting Date<input type="date" value={payload.meeting_date ?? ""} onChange={(event) => patch({ meeting_date: event.target.value || null })} /></label>
          </div>
        </fieldset>

        <fieldset>
          <legend>SACS</legend>
          <div className="field-grid">
            <label>Monthly Inflow{numberInput(payload.monthly_inflow, (value) => patch({ monthly_inflow: value }))}</label>
            <label>Monthly Outflow{numberInput(payload.monthly_outflow, (value) => patch({ monthly_outflow: value }))}</label>
            <label>Deductibles{numberInput(payload.deductibles, (value) => patch({ deductibles: value }))}</label>
            <label>Private Reserve{numberInput(payload.private_reserve_balance, (value) => patch({ private_reserve_balance: value }))}</label>
            <label>Investment Balance{numberInput(payload.investment_account_balance, (value) => patch({ investment_account_balance: value }))}</label>
          </div>
        </fieldset>

        <fieldset>
          <legend>TCC Account Balances</legend>
          <AccountTable accounts={client.accounts} mode="edit" values={accountValues} setValue={setAccountValue} />
        </fieldset>

        <div className="content-grid form-grid">
          <fieldset>
            <legend>Liabilities</legend>
            <div className="compact-list">
              {client.liabilities.length === 0 && <span>None entered</span>}
              {client.liabilities.map((item) => (
                <label key={item.id}>{item.name}{numberInput(liabilityValues[item.id] ?? item.balance, (value) => setLiabilityValue(item.id, value))}</label>
              ))}
            </div>
          </fieldset>

          <fieldset>
            <legend>Trust Assets</legend>
            <div className="compact-list">
              {client.trust_assets.length === 0 && <span>None entered</span>}
              {client.trust_assets.map((item) => (
                <label key={item.id}>{item.name}{numberInput(trustValues[item.id] ?? item.value, (value) => setTrustValue(item.id, value))}</label>
              ))}
            </div>
          </fieldset>
        </div>

        <label className="notes-field">Notes<textarea value={payload.notes} onChange={(event) => patch({ notes: event.target.value })} /></label>
        <div className="page-actions">
          <button type="button" className="ghost-button" onClick={() => navigate(`/clients/${client.id}`)}>Cancel</button>
          <button type="submit" className="primary-button" disabled={saving}>
            {saving ? <Loader2 className="spin" size={17} /> : <CheckCircle2 size={17} />}
            Generate PDFs
          </button>
        </div>
      </form>
    </section>
  );
}

export default function App() {
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.pathname));

  const navigate = (path: string) => {
    window.history.pushState({}, "", path);
    setRoute(parseRoute(path));
  };

  useEffect(() => {
    if (window.location.pathname === "/") navigate("/clients");
    const onPopState = () => setRoute(parseRoute(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    getMeta().then(setMeta).catch(() => setMeta(null));
  }, []);

  return (
    <main className="app-shell">
      <header className="topbar">
        <button className="brand-mark nav-button" onClick={() => navigate("/clients")}>
          <WalletCards size={23} />
          <span>WealthPortal</span>
        </button>
        <nav>
          <button className={route.name === "clients" ? "active" : ""} onClick={() => navigate("/clients")}>Clients</button>
          <span>Report Runs</span>
          <span>PDF History</span>
        </nav>
      </header>

      <section className="workspace single-view">
        {route.name === "clients" && (
          <ClientsView filters={filters} setFilters={setFilters} meta={meta} navigate={navigate} />
        )}
        {route.name === "client" && <ClientDetailView clientId={route.clientId} navigate={navigate} />}
        {route.name === "report" && <ReportView clientId={route.clientId} navigate={navigate} />}
      </section>
    </main>
  );
}
