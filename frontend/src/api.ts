import type { ClientDetail, ClientListResponse, ClientUpdatePayload, Meta, ReportPayload, ReportPrefill } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    let message = "Request failed.";
    try {
      const payload = await response.json();
      message = payload?.detail?.message ?? payload?.detail ?? message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function getMeta() {
  return apiFetch<Meta>("/meta");
}

export function getClients(params: URLSearchParams) {
  return apiFetch<ClientListResponse>(`/clients?${params.toString()}`);
}

export function getClient(id: string) {
  return apiFetch<ClientDetail>(`/clients/${id}`);
}

export function createClient(payload: ClientUpdatePayload) {
  return apiFetch<ClientDetail>("/clients", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateClient(id: string, payload: ClientUpdatePayload) {
  return apiFetch<ClientDetail>(`/clients/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getReportPrefill(id: string) {
  return apiFetch<ReportPrefill>(`/clients/${id}/report-prefill`);
}

export function createReportRun(id: string, payload: ReportPayload) {
  return apiFetch<{ client: ClientDetail }>(`/clients/${id}/report-runs`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function reportDownloadUrl(reportId: string) {
  return `${API_BASE}/generated-reports/${reportId}/download`;
}
