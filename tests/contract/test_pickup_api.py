import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from tests.unit.test_pickup import _setup_pickup_fixtures


def test_pickup_api_contract_lifecycle(client: TestClient, db_session: Session, seed_test_users):
    truck, driver, trip = _setup_pickup_fixtures(db_session)

    # 1. Unauthenticated -> 401
    resp_unauth = client.post(f"/api/v1/trips/{trip.id}/pickup", json={
        "actual_pickup_time": "2026-12-01T09:30:00",
        "handover_person": "Nguyễn Văn Kho",
        "actual_cargo_weight_kg": 4000,
    })
    assert resp_unauth.status_code == 401

    # 2. Login as SAL -> 403 Forbidden
    client.post("/api/v1/auth/login", json={"username": "sal_test", "password": "password123"})
    resp_sal = client.post(f"/api/v1/trips/{trip.id}/pickup", json={
        "actual_pickup_time": "2026-12-01T09:30:00",
        "handover_person": "Nguyễn Văn Kho",
        "actual_cargo_weight_kg": 4000,
    })
    assert resp_sal.status_code == 403
    client.post("/api/v1/auth/logout")

    # 3. Login as DSP -> 200 OK
    client.post("/api/v1/auth/login", json={"username": "dsp_test", "password": "password123"})
    resp_dsp = client.post(f"/api/v1/trips/{trip.id}/pickup", json={
        "actual_pickup_time": "2026-12-01T09:30:00",
        "handover_person": "Nguyễn Văn Kho",
        "actual_cargo_weight_kg": 4500,
        "cargo_condition": "Hàng đủ số lượng",
    })
    assert resp_dsp.status_code == 200
    data = resp_dsp.json()["data"]
    assert data["status"] == "PICKED_UP"
    assert data["actual_cargo_weight_kg"] == 4500

    # 4. Check timeline events endpoint
    resp_events = client.get(f"/api/v1/trips/{trip.id}/events")
    assert resp_events.status_code == 200
    events_data = resp_events.json()["data"]
    assert len(events_data) == 1
    assert events_data[0]["event_type"] == "PICKUP_CONFIRMED"
