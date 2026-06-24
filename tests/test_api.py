from copy import deepcopy

from fastapi.testclient import TestClient

from backend.main import app
from backend.seed import UNIQUE_CLIENT_COUNT


def detail_update_payload(detail: dict) -> dict:
    primary = next(item for item in detail["members"] if item["relationship"] == "Primary")
    spouse = next(item for item in detail["members"] if item["relationship"] == "Spouse")
    return {
        "household_name": detail["household_name"],
        "status": detail["status"],
        "last_report_date": detail["last_report_date"],
        "primary_first_name": primary["first_name"],
        "primary_last_name": primary["last_name"],
        "primary_date_of_birth": primary["date_of_birth"],
        "spouse_first_name": spouse["first_name"],
        "spouse_last_name": spouse["last_name"],
        "spouse_date_of_birth": spouse["date_of_birth"],
        "notes": detail["notes"],
        "accounts": [
            {
                "id": item["id"],
                "owner": item["owner"],
                "category": item["category"],
                "name": item["name"],
                "institution": item["institution"],
                "account_type": item["account_type"],
                "balance": item["balance"],
                "as_of_date": item["as_of_date"],
            }
            for item in detail["accounts"]
        ],
        "liabilities": [
            {
                "id": item["id"],
                "name": item["name"],
                "liability_type": item["liability_type"],
                "balance": item["balance"],
                "as_of_date": item["as_of_date"],
            }
            for item in detail["liabilities"]
        ],
        "trust_assets": [
            {
                "id": item["id"],
                "name": item["name"],
                "value": item["value"],
                "as_of_date": item["as_of_date"],
            }
            for item in detail["trust_assets"]
        ],
    }


def test_clients_are_seeded_and_paginated() -> None:
    with TestClient(app) as client:
        response = client.get("/api/clients?page=1&page_size=10")
        all_clients = client.get(f"/api/clients?page=1&page_size={UNIQUE_CLIENT_COUNT}").json()["items"]

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == UNIQUE_CLIENT_COUNT
    assert len(payload["items"]) == 10
    assert len({item["household_name"] for item in all_clients}) == UNIQUE_CLIENT_COUNT
    assert {"household_name", "readiness_status", "total_assets"} <= set(payload["items"][0])
    assert {"tier", "assigned_team_member", "next_meeting_date"}.isdisjoint(payload["items"][0])


def test_client_profile_can_be_updated() -> None:
    with TestClient(app) as client:
        candidates = client.get("/api/clients?page=1&page_size=50").json()["items"]
        detail = next(
            item_detail
            for item_detail in (client.get(f"/api/clients/{item['id']}").json() for item in candidates)
            if item_detail["accounts"] and item_detail["liabilities"] and item_detail["trust_assets"]
        )
        payload = detail_update_payload(detail)
        restore_payload = deepcopy(payload)
        payload["household_name"] = f"{detail['household_name']} Updated"
        payload["status"] = "Active"
        payload["last_report_date"] = "2026-05-01"
        payload["primary_first_name"] = "Updated"
        payload["primary_last_name"] = "Primary"
        payload["spouse_first_name"] = "Updated"
        payload["spouse_last_name"] = "Spouse"
        payload["primary_date_of_birth"] = "1965-01-15"
        payload["spouse_date_of_birth"] = "1966-02-20"
        payload["notes"] = "Updated from API test."
        payload["accounts"][0]["name"] = "Updated Brokerage"
        payload["accounts"][0]["owner"] = "Joint"
        payload["accounts"][0]["balance"] = 123456.78
        payload["accounts"][0]["as_of_date"] = "2026-04-30"
        payload["liabilities"][0]["name"] = "Updated Mortgage"
        payload["liabilities"][0]["balance"] = 65432.1
        payload["trust_assets"][0]["name"] = "Updated Family Trust"
        payload["trust_assets"][0]["value"] = 765432.1
        response = client.put(f"/api/clients/{detail['id']}", json=payload)
        client.put(f"/api/clients/{detail['id']}", json=restore_payload)

    assert response.status_code == 200
    updated = response.json()
    assert updated["household_name"] == payload["household_name"]
    assert updated["primary_contact"] == "Updated Primary"
    assert updated["spouse_contact"] == "Updated Spouse"
    assert len(updated["members"]) == 2
    assert {member["relationship"] for member in updated["members"]} == {"Primary", "Spouse"}
    assert updated["notes"] == "Updated from API test."
    assert updated["last_report_date"] == "2026-05-01"
    updated_account = next(item for item in updated["accounts"] if item["id"] == payload["accounts"][0]["id"])
    updated_liability = next(item for item in updated["liabilities"] if item["id"] == payload["liabilities"][0]["id"])
    updated_trust_asset = next(item for item in updated["trust_assets"] if item["id"] == payload["trust_assets"][0]["id"])
    assert updated_account["name"] == "Updated Brokerage"
    assert updated_account["owner"] == "Joint"
    assert updated_account["balance"] == 123456.78
    assert updated_account["as_of_date"] == "2026-04-30"
    assert updated_liability["name"] == "Updated Mortgage"
    assert updated_liability["balance"] == 65432.1
    assert updated_trust_asset["name"] == "Updated Family Trust"
    assert updated_trust_asset["value"] == 765432.1


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
