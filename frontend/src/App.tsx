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
  Pencil,
  Plus,
  Search,
  Trash2,
  UserRound,
  WalletCards
} from "lucide-react";
import { Fragment, FormEvent, useEffect, useMemo, useState } from "react";
import {
  createClient,
  createReportRun,
  getClient,
  getClients,
  getMeta,
  getReportPrefill,
  reportDownloadUrl,
  updateClient
} from "./api";
import type {
  Account,
  AccountUpdatePayload,
  ClientDetail,
  ClientListItem,
  ClientListResponse,
  ClientUpdatePayload,
  LiabilityUpdatePayload,
  Meta,
  ReportPayload,
  ReportPrefill,
  TrustAssetUpdatePayload
} from "./types";

type Filters = {
  search: string;
  status: string;
  missing_data: boolean;
  sort_by: string;
  sort_dir: string;
  page: number;
  page_size: number;
};

type Route =
  | { name: "clients" }
  | { name: "new-client" }
  | { name: "client"; clientId: string }
  | { name: "report"; clientId: string };

const initialFilters: Filters = {
  search: "",
  status: "",
  missing_data: false,
  sort_by: "household_name",
  sort_dir: "asc",
  page: 1,
  page_size: 25
};

function parseRoute(pathname: string): Route {
  const parts = pathname.split("/").filter(Boolean);
  if (parts[0] !== "clients") return { name: "clients" };
  if (parts[1] === "new") return { name: "new-client" };
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
  const normalized = status.toLowerCase();
  if (["ready", "draft ready", "active"].includes(normalized)) return "good";
  if (
    normalized.includes("waiting") ||
    normalized.includes("missing") ||
    normalized.includes("review") ||
    normalized.includes("due")
  ) return "warn";
  return "neutral";
}

function StatusPill({ value }: { value: string }) {
  return <span className={`status ${statusTone(value)}`}>{value}</span>;
}

function householdMember(client: ClientDetail, relationships: string[]) {
  const normalized = relationships.map((item) => item.toLowerCase());
  return client.members.find((member) => normalized.includes(member.relationship.toLowerCase()));
}

function clientToUpdatePayload(client: ClientDetail): ClientUpdatePayload {
  const primary = householdMember(client, ["Primary"]);
  const spouse = householdMember(client, ["Spouse"]);
  return {
    household_name: client.household_name,
    status: client.status,
    last_report_date: client.last_report_date,
    primary_first_name: primary?.first_name ?? "",
    primary_last_name: primary?.last_name ?? "",
    primary_date_of_birth: primary?.date_of_birth ?? null,
    spouse_first_name: spouse?.first_name ?? "",
    spouse_last_name: spouse?.last_name ?? "",
    spouse_date_of_birth: spouse?.date_of_birth ?? null,
    notes: client.notes,
    accounts: client.accounts.map((account) => ({
      id: account.id,
      owner: account.owner,
      category: account.category,
      name: account.name,
      institution: account.institution,
      account_type: account.account_type,
      balance: account.balance,
      as_of_date: account.as_of_date
    })),
    liabilities: client.liabilities.map((item) => ({
      id: item.id,
      name: item.name,
      liability_type: item.liability_type,
      balance: item.balance,
      as_of_date: item.as_of_date
    })),
    trust_assets: client.trust_assets.map((item) => ({
      id: item.id,
      name: item.name,
      value: item.value,
      as_of_date: item.as_of_date
    }))
  };
}

function newClientPayload(): ClientUpdatePayload {
  return {
    household_name: "",
    status: "Active",
    last_report_date: null,
    primary_first_name: "",
    primary_last_name: "",
    primary_date_of_birth: null,
    spouse_first_name: "",
    spouse_last_name: "",
    spouse_date_of_birth: null,
    notes: "",
    accounts: [],
    liabilities: [],
    trust_assets: []
  };
}

function uniqueOptions(current: string, options: string[] | undefined) {
  return Array.from(new Set([current, ...(options ?? [])].filter(Boolean)));
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
            <th>Primary</th>
            <th>Spouse</th>
            <th>Assets</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {clients.map((client) => (
            <tr key={client.id} onClick={() => onSelect(client.id)}>
              <td>
                <b>{client.household_name}</b>
                <span>{client.member_count} household members</span>
              </td>
              <td>{client.primary_contact}</td>
              <td>{client.spouse_contact || "Not set"}</td>
              <td>{currency(client.total_assets)}</td>
              <td><StatusPill value={client.status} /></td>
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
          <option value="last_report_date">Last report</option>
          <option value="household_name">Household</option>
          <option value="status">Status</option>
        </select>
      </label>
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
        <div className="header-actions">
          <span className="record-count">{data?.total ?? 0} records</span>
          <button className="primary-button" onClick={() => navigate("/clients/new")}>
            <Plus size={17} />
            Add Client
          </button>
        </div>
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

function ClientProfileForm({
  draft,
  setDraft,
  meta,
  saving,
  error,
  onCancel,
  onSubmit,
  title = "Client Data",
  submitLabel = "Save Client"
}: {
  draft: ClientUpdatePayload;
  setDraft: (next: ClientUpdatePayload) => void;
  meta: Meta | null;
  saving: boolean;
  error: string;
  onCancel: () => void;
  onSubmit: (event: FormEvent) => void;
  title?: string;
  submitLabel?: string;
}) {
  const patch = (next: Partial<ClientUpdatePayload>) => setDraft({ ...draft, ...next });
  const statuses = uniqueOptions(draft.status, meta?.statuses);
  const setAccount = (index: number, next: Partial<AccountUpdatePayload>) => {
    patch({ accounts: draft.accounts.map((item, idx) => idx === index ? { ...item, ...next } : item) });
  };
  const setLiability = (index: number, next: Partial<LiabilityUpdatePayload>) => {
    patch({ liabilities: draft.liabilities.map((item, idx) => idx === index ? { ...item, ...next } : item) });
  };
  const setTrustAsset = (index: number, next: Partial<TrustAssetUpdatePayload>) => {
    patch({ trust_assets: draft.trust_assets.map((item, idx) => idx === index ? { ...item, ...next } : item) });
  };
  const addAccount = () => {
    patch({
      accounts: [
        ...draft.accounts,
        {
          owner: "Primary",
          category: "non_retirement",
          name: "",
          institution: "",
          account_type: "",
          balance: 0,
          as_of_date: null
        }
      ]
    });
  };
  const addLiability = () => {
    patch({
      liabilities: [
        ...draft.liabilities,
        {
          name: "",
          liability_type: "",
          balance: 0,
          as_of_date: null
        }
      ]
    });
  };
  const addTrustAsset = () => {
    patch({
      trust_assets: [
        ...draft.trust_assets,
        {
          name: "",
          value: 0,
          as_of_date: null
        }
      ]
    });
  };

  return (
    <form className="panel client-profile-form" onSubmit={onSubmit}>
      <div className="panel-title-row">
        <h2>{title}</h2>
      </div>
      {error && <div className="error-banner">{error}</div>}

      <fieldset>
        <legend>Household</legend>
        <div className="field-grid">
          <label>
            Household Name
            <input
              required
              maxLength={160}
              value={draft.household_name}
              onChange={(event) => patch({ household_name: event.target.value })}
            />
          </label>
          <label>
            Status
            <input
              required
              list="client-status-options"
              maxLength={40}
              value={draft.status}
              onChange={(event) => patch({ status: event.target.value })}
            />
            <datalist id="client-status-options">
              {statuses.map((item) => <option key={item} value={item} />)}
            </datalist>
          </label>
          <label>
            Last Report Date
            <input
              type="date"
              value={draft.last_report_date ?? ""}
              onChange={(event) => patch({ last_report_date: event.target.value || null })}
            />
          </label>
          <label>
            Primary First Name
            <input
              required
              maxLength={80}
              value={draft.primary_first_name}
              onChange={(event) => patch({ primary_first_name: event.target.value })}
            />
          </label>
          <label>
            Primary Last Name
            <input
              required
              maxLength={80}
              value={draft.primary_last_name}
              onChange={(event) => patch({ primary_last_name: event.target.value })}
            />
          </label>
          <label>
            Primary Date of Birth
            <input
              type="date"
              value={draft.primary_date_of_birth ?? ""}
              onChange={(event) => patch({ primary_date_of_birth: event.target.value || null })}
            />
          </label>
          <label>
            Spouse First Name
            <input
              required
              maxLength={80}
              value={draft.spouse_first_name}
              onChange={(event) => patch({ spouse_first_name: event.target.value })}
            />
          </label>
          <label>
            Spouse Last Name
            <input
              required
              maxLength={80}
              value={draft.spouse_last_name}
              onChange={(event) => patch({ spouse_last_name: event.target.value })}
            />
          </label>
          <label>
            Spouse Date of Birth
            <input
              type="date"
              value={draft.spouse_date_of_birth ?? ""}
              onChange={(event) => patch({ spouse_date_of_birth: event.target.value || null })}
            />
          </label>
        </div>
        <label className="notes-field">
          Notes
          <textarea maxLength={5000} value={draft.notes} onChange={(event) => patch({ notes: event.target.value })} />
        </label>
      </fieldset>

      <fieldset>
        <legend>Accounts</legend>
        <div className="fieldset-title-row">
          <span>{draft.accounts.length} rows</span>
          <button type="button" className="ghost-button" onClick={addAccount}><Plus size={16} /> Add Account</button>
        </div>
        <div className="table-wrap edit-table-wrap">
          <table className="edit-table">
            <thead><tr><th>Owner</th><th>Category</th><th>Name</th><th>Institution</th><th>Type</th><th>Balance</th><th>As Of</th><th></th></tr></thead>
            <tbody>
              {draft.accounts.map((account, index) => (
                <tr key={account.id ?? `new-account-${index}`}>
                  <td><input required aria-label="Account owner" value={account.owner} onChange={(event) => setAccount(index, { owner: event.target.value })} /></td>
                  <td><input required aria-label="Account category" value={account.category} onChange={(event) => setAccount(index, { category: event.target.value })} /></td>
                  <td><input required aria-label="Account name" value={account.name} onChange={(event) => setAccount(index, { name: event.target.value })} /></td>
                  <td><input required aria-label="Account institution" value={account.institution} onChange={(event) => setAccount(index, { institution: event.target.value })} /></td>
                  <td><input required aria-label="Account type" value={account.account_type} onChange={(event) => setAccount(index, { account_type: event.target.value })} /></td>
                  <td><input type="number" min="0" step="0.01" value={account.balance} onChange={(event) => setAccount(index, { balance: Number(event.target.value) })} /></td>
                  <td><input type="date" value={account.as_of_date ?? ""} onChange={(event) => setAccount(index, { as_of_date: event.target.value || null })} /></td>
                  <td>
                    <button
                      type="button"
                      className="icon-button danger-button"
                      title="Remove account"
                      onClick={() => patch({ accounts: draft.accounts.filter((_, idx) => idx !== index) })}
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
              {draft.accounts.length === 0 && <tr><td colSpan={8}>No accounts entered</td></tr>}
            </tbody>
          </table>
        </div>
      </fieldset>

      <div className="content-grid form-grid">
        <fieldset>
          <legend>Liabilities</legend>
          <div className="fieldset-title-row">
            <span>{draft.liabilities.length} rows</span>
            <button type="button" className="ghost-button" onClick={addLiability}><Plus size={16} /> Add Liability</button>
          </div>
          <div className="table-wrap edit-table-wrap">
            <table className="edit-table">
              <thead><tr><th>Name</th><th>Type</th><th>Balance</th><th>As Of</th><th></th></tr></thead>
              <tbody>
                {draft.liabilities.map((item, index) => (
                  <tr key={item.id ?? `new-liability-${index}`}>
                    <td><input required value={item.name} onChange={(event) => setLiability(index, { name: event.target.value })} /></td>
                    <td><input required value={item.liability_type} onChange={(event) => setLiability(index, { liability_type: event.target.value })} /></td>
                    <td><input type="number" min="0" step="0.01" value={item.balance} onChange={(event) => setLiability(index, { balance: Number(event.target.value) })} /></td>
                    <td><input type="date" value={item.as_of_date ?? ""} onChange={(event) => setLiability(index, { as_of_date: event.target.value || null })} /></td>
                    <td>
                      <button
                        type="button"
                        className="icon-button danger-button"
                        title="Remove liability"
                        onClick={() => patch({ liabilities: draft.liabilities.filter((_, idx) => idx !== index) })}
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
                {draft.liabilities.length === 0 && <tr><td colSpan={5}>No liabilities entered</td></tr>}
              </tbody>
            </table>
          </div>
        </fieldset>

        <fieldset>
          <legend>Trust Assets</legend>
          <div className="fieldset-title-row">
            <span>{draft.trust_assets.length} rows</span>
            <button type="button" className="ghost-button" onClick={addTrustAsset}><Plus size={16} /> Add Trust Asset</button>
          </div>
          <div className="table-wrap edit-table-wrap">
            <table className="edit-table">
              <thead><tr><th>Name</th><th>Value</th><th>As Of</th><th></th></tr></thead>
              <tbody>
                {draft.trust_assets.map((item, index) => (
                  <tr key={item.id ?? `new-trust-${index}`}>
                    <td><input required value={item.name} onChange={(event) => setTrustAsset(index, { name: event.target.value })} /></td>
                    <td><input type="number" min="0" step="0.01" value={item.value} onChange={(event) => setTrustAsset(index, { value: Number(event.target.value) })} /></td>
                    <td><input type="date" value={item.as_of_date ?? ""} onChange={(event) => setTrustAsset(index, { as_of_date: event.target.value || null })} /></td>
                    <td>
                      <button
                        type="button"
                        className="icon-button danger-button"
                        title="Remove trust asset"
                        onClick={() => patch({ trust_assets: draft.trust_assets.filter((_, idx) => idx !== index) })}
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
                {draft.trust_assets.length === 0 && <tr><td colSpan={4}>No trust assets entered</td></tr>}
              </tbody>
            </table>
          </div>
        </fieldset>
      </div>

      <div className="page-actions">
        <button type="button" className="ghost-button" onClick={onCancel}>Cancel</button>
        <button type="submit" className="primary-button" disabled={saving}>
          {saving ? <Loader2 className="spin" size={17} /> : <CheckCircle2 size={17} />}
          {submitLabel}
        </button>
      </div>
    </form>
  );
}

function DetailView({
  client,
  loading,
  meta,
  onBack,
  onSaveClient,
  onOpenReport,
  onRefresh
}: {
  client: ClientDetail | null;
  loading: boolean;
  meta: Meta | null;
  onBack: () => void;
  onSaveClient: (payload: ClientUpdatePayload) => Promise<void>;
  onOpenReport: () => void;
  onRefresh: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<ClientUpdatePayload | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  useEffect(() => {
    setEditing(false);
    setDraft(null);
    setFormError("");
  }, [client?.id]);

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
  const primary = householdMember(client, ["Primary"]);
  const spouse = householdMember(client, ["Spouse"]);
  const startEditing = () => {
    setDraft(clientToUpdatePayload(client));
    setEditing(true);
    setFormError("");
  };
  const cancelEditing = () => {
    setDraft(null);
    setEditing(false);
    setFormError("");
  };
  const saveEditing = (event: FormEvent) => {
    event.preventDefault();
    if (!draft) return;
    setSaving(true);
    setFormError("");
    onSaveClient(draft)
      .then(() => cancelEditing())
      .catch((err: Error) => setFormError(err.message))
      .finally(() => setSaving(false));
  };

  return (
    <section className="view-shell detail">
      <div className="detail-header">
        <div>
          <button className="back-link" onClick={onBack}><ArrowLeft size={16} /> Clients</button>
          <p className="eyebrow">{client.status}</p>
          <h1>{client.household_name}</h1>
          <div className="inline-facts">
            <span><UserRound size={15} /> Primary: {primary ? `${primary.first_name} ${primary.last_name}` : client.primary_contact}</span>
            <span><UserRound size={15} /> Spouse: {spouse ? `${spouse.first_name} ${spouse.last_name}` : "Not set"}</span>
            <StatusPill value={client.readiness_status} />
          </div>
          {client.notes && <p className="profile-notes">{client.notes}</p>}
        </div>
        <div className="header-actions">
          <button className="ghost-button" onClick={startEditing}>
            <Pencil size={17} />
            Edit Client
          </button>
          <button className="primary-button" onClick={onOpenReport}>
            <FileText size={18} />
            Start Report
          </button>
        </div>
      </div>

      {editing && draft && (
        <ClientProfileForm
          draft={draft}
          setDraft={setDraft}
          meta={meta}
          saving={saving}
          error={formError}
          onCancel={cancelEditing}
          onSubmit={saveEditing}
        />
      )}

      <div className="metrics-grid">
        <Metric label="Grand Total" value={currency(client.summary.grand_total)} />
        <Metric label="Liabilities" value={currency(client.summary.liabilities_total)} accent="danger" />
        <Metric label="Net Worth" value={currency(client.summary.net_worth_after_liabilities)} accent="good-text" />
        <Metric label="Reports" value={`${client.report_runs.length}`} />
      </div>

      <div className="content-grid">
        <section className="panel">
          <h2>Household</h2>
          <div className="member-grid">
            {client.members.map((member) => (
              <div className="member" key={member.id}>
                <b>{member.first_name} {member.last_name}</b>
                <span>{member.relationship === "Primary" ? "Primary" : "Spouse"}</span>
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

function ClientDetailView({
  clientId,
  meta,
  navigate,
  refreshMeta
}: {
  clientId: string;
  meta: Meta | null;
  navigate: (path: string) => void;
  refreshMeta: () => void;
}) {
  const { client, setClient, loading, error, refresh } = useClientDetail(clientId);

  const saveClient = (payload: ClientUpdatePayload) =>
    updateClient(clientId, payload).then((updated) => {
      setClient(updated);
      refreshMeta();
    });

  return (
    <>
      {error && <div className="toast error-banner">{error}</div>}
      <DetailView
        client={client}
        loading={loading}
        meta={meta}
        onBack={() => navigate("/clients")}
        onSaveClient={saveClient}
        onOpenReport={() => navigate(`/clients/${clientId}/report`)}
        onRefresh={refresh}
      />
    </>
  );
}

function NewClientView({
  meta,
  navigate,
  refreshMeta
}: {
  meta: Meta | null;
  navigate: (path: string) => void;
  refreshMeta: () => void;
}) {
  const [draft, setDraft] = useState<ClientUpdatePayload>(() => newClientPayload());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    createClient(draft)
      .then((client) => {
        refreshMeta();
        navigate(`/clients/${client.id}`);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setSaving(false));
  };

  return (
    <section className="view-shell detail">
      <div className="detail-header">
        <div>
          <button className="back-link" onClick={() => navigate("/clients")}><ArrowLeft size={16} /> Clients</button>
          <p className="eyebrow">New Household</p>
          <h1>Add Client</h1>
        </div>
      </div>
      <ClientProfileForm
        draft={draft}
        setDraft={setDraft}
        meta={meta}
        saving={saving}
        error={error}
        onCancel={() => navigate("/clients")}
        onSubmit={onSubmit}
        title="New Client Data"
        submitLabel="Create Client"
      />
    </section>
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

  const refreshMeta = () => {
    getMeta().then(setMeta).catch(() => setMeta(null));
  };

  useEffect(() => {
    if (window.location.pathname === "/") navigate("/clients");
    const onPopState = () => setRoute(parseRoute(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    refreshMeta();
  }, []);

  return (
    <main className="app-shell">
      <header className="topbar">
        <button className="brand-mark nav-button" onClick={() => navigate("/clients")}>
          <WalletCards size={23} />
          <span>Client Report Portal</span>
        </button>
        <nav>
          <button className={route.name === "clients" || route.name === "new-client" ? "active" : ""} onClick={() => navigate("/clients")}>Clients</button>
        </nav>
      </header>

      <section className="workspace single-view">
        {route.name === "clients" && (
          <ClientsView filters={filters} setFilters={setFilters} meta={meta} navigate={navigate} />
        )}
        {route.name === "new-client" && (
          <NewClientView meta={meta} navigate={navigate} refreshMeta={refreshMeta} />
        )}
        {route.name === "client" && (
          <ClientDetailView clientId={route.clientId} meta={meta} navigate={navigate} refreshMeta={refreshMeta} />
        )}
        {route.name === "report" && <ReportView clientId={route.clientId} navigate={navigate} />}
      </section>
    </main>
  );
}
