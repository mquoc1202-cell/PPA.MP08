import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_unauthenticated_access_redirection(client: TestClient):
    """Unauthenticated users accessing web views are redirected to /login with next param."""
    # 1. Dashboard redirect
    res_dash = client.get("/dashboard", follow_redirects=False)
    assert res_dash.status_code == 303
    assert "/login" in res_dash.headers["location"]
    assert "next=" in res_dash.headers["location"]

    # 2. Admin Trucks redirect
    res_trucks = client.get("/admin/trucks", follow_redirects=False)
    assert res_trucks.status_code == 303
    assert "/login" in res_trucks.headers["location"]

    # 3. Admin Drivers redirect
    res_drivers = client.get("/admin/drivers", follow_redirects=False)
    assert res_drivers.status_code == 303
    assert "/login" in res_drivers.headers["location"]


def test_unauthenticated_api_access(client: TestClient):
    """Unauthenticated API mutating requests return HTTP 401."""
    res = client.post("/api/v1/trucks", json={
        "plate_number": "29C-111.22",
        "truck_type": "Xe 5T",
        "capacity_kg": 5000
    })
    assert res.status_code == 401


def test_sales_role_rbac_restrictions(client: TestClient, db_session: Session, seed_test_users):
    """
    SAL (Sales) role can view lists and dashboard,
    but is strictly blocked (HTTP 403) from write/modify operations.
    """
    # 1. Login as SAL
    login_res = client.post("/api/v1/auth/login", json={
        "username": "sal_test",
        "password": "password123"
    })
    assert login_res.status_code == 200
    assert login_res.json()["data"]["role"] == "SAL"

    # 2. SAL can view dashboard
    dash_res = client.get("/dashboard")
    assert dash_res.status_code == 200
    assert "Tổng Quan" in dash_res.text

    # 3. SAL can view trucks list
    trucks_res = client.get("/admin/trucks")
    assert trucks_res.status_code == 200

    # 4. SAL attempting to create a truck via API -> 403 Forbidden
    create_truck_res = client.post("/api/v1/trucks", json={
        "plate_number": "29C-999.00",
        "truck_type": "Xe 5T",
        "capacity_kg": 5000
    })
    assert create_truck_res.status_code == 403
    assert "không có quyền" in create_truck_res.json()["error"]

    # 5. SAL attempting to create a driver via API -> 403 Forbidden
    create_driver_res = client.post("/api/v1/drivers", json={
        "driver_code": "TX999",
        "full_name": "Tài xế mới",
        "phone_number": "0911223344"
    })
    assert create_driver_res.status_code == 403

    # 6. SAL attempting to create truck via Web Form -> 403 Forbidden
    web_post_res = client.post(
        "/admin/trucks/create",
        data={
            "plate_number": "29C-999.00",
            "truck_type": "Xe 5T",
            "capacity_kg": 5000
        }
    )
    assert web_post_res.status_code == 403
    assert "403" in web_post_res.text


def test_dispatcher_role_rbac_permitted(client: TestClient, db_session: Session, seed_test_users):
    """
    DSP (Dispatcher) role is authorized for write and mutation operations.
    """
    # 1. Login as DSP
    login_res = client.post("/api/v1/auth/login", json={
        "username": "dsp_test",
        "password": "password123"
    })
    assert login_res.status_code == 200
    assert login_res.json()["data"]["role"] == "DSP"

    # 2. DSP creating truck via API -> 201 Created
    create_res = client.post("/api/v1/trucks", json={
        "plate_number": "29C-333.44",
        "truck_type": "Xe 5T",
        "capacity_kg": 5000
    })
    assert create_res.status_code == 201
    assert create_res.json()["success"] is True
