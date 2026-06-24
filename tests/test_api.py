from fastapi.testclient import TestClient

from backend.main import app


def test_clients_are_seeded_and_paginated() -> None:
    with TestClient(app) as client:
        response = client.get("/api/clients?page=1&page_size=10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 100
    assert len(payload["items"]) == 10
    assert {"household_name", "readiness_status", "total_assets"} <= set(payload["items"][0])


def test_report_generation_creates_downloadable_metadata() -> None:
    with TestClient(app) as client:
        first = client.get("/api/clients?page=1&page_size=5").json()["items"][0]
        detail = client.get(f"/api/clients/{first['id']}").json()
        prefill = client.get(f"/api/clients/{first['id']}/report-prefill").json()
        payload = {
            **prefill,
            "notes": "API smoke test report.",
            "monthly_inflow": 30_000,
            "monthly_outflow": 18_000,
            "deductibles": 5_000,
            "private_reserve_balance": 120_000,
            "investment_account_balance": 450_000,
            "account_updates": [{"id": item["id"], "balance": item["balance"]} for item in detail["accounts"]],
            "liability_updates": [{"id": item["id"], "balance": item["balance"]} for item in detail["liabilities"]],
            "trust_asset_updates": [{"id": item["id"], "value": item["value"]} for item in detail["trust_assets"]],
        }
        response = client.post(f"/api/clients/{first['id']}/report-runs", json=payload)

    assert response.status_code == 201
    created = response.json()["client"]["report_runs"][0]
    assert created["calculation_snapshot"]["sacs"]["excess_transfer"] == 12_000
    assert {report["report_type"] for report in created["generated_reports"]} == {"SACS", "TCC"}
    assert all(report["size_bytes"] > 0 for report in created["generated_reports"])
