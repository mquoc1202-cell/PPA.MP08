from fastapi.testclient import TestClient

def test_api_truck_flow(client: TestClient, seed_test_users):
    """Verifies complete Truck REST API lifecycle matching contracts/trucks-api.yaml."""
    # Authenticate as DSP to perform admin mutations
    client.post("/api/v1/auth/login", json={"username": "dsp_test", "password": "password123"})

    # 1. Create Truck
    create_res = client.post("/api/v1/trucks", json={
        "plate_number": "29C-789.01",
        "truck_type": "Xe thùng kín 8T",
        "capacity_kg": 8000,
        "description": "Xe giao hàng miền Bắc"
    })
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["success"] is True
    assert created_data["data"]["normalized_plate"] == "29C78901"
    truck_id = created_data["data"]["id"]

    # 2. Duplicate normalized plate rejection
    dup_res = client.post("/api/v1/trucks", json={
        "plate_number": "29c 789.01",
        "truck_type": "Xe thùng bạt",
        "capacity_kg": 5000
    })
    assert dup_res.status_code == 409
    assert dup_res.json()["success"] is False

    # 3. Get Truck by ID
    get_res = client.get(f"/api/v1/trucks/{truck_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["plate_number"] == "29C-789.01"

    # 4. List Trucks
    list_res = client.get("/api/v1/trucks?search=29C")
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # 5. Change Truck Status
    patch_res = client.patch(f"/api/v1/trucks/{truck_id}/status", json={
        "status": "MAINTENANCE",
        "reason": "Bảo dưỡng 5000km"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["status"] == "MAINTENANCE"

    # 6. Delete Truck (no history -> allowed)
    del_res = client.delete(f"/api/v1/trucks/{truck_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

def test_api_driver_flow(client: TestClient, seed_test_users):
    """Verifies complete Driver REST API lifecycle matching contracts/drivers-api.yaml."""
    # Authenticate as DSP to perform admin mutations
    client.post("/api/v1/auth/login", json={"username": "dsp_test", "password": "password123"})

    # 1. Create Driver
    create_res = client.post("/api/v1/drivers", json={
        "driver_code": "TX100",
        "full_name": "Phạm Văn K",
        "phone_number": "0912345678"
    })
    assert create_res.status_code == 201
    driver_data = create_res.json()
    assert driver_data["success"] is True
    assert driver_data["data"]["driver_code"] == "TX100"
    driver_id = driver_data["data"]["id"]

    # 2. Duplicate driver code rejection
    dup_res = client.post("/api/v1/drivers", json={
        "driver_code": "tx100",
        "full_name": "Người khác",
        "phone_number": "0987654321"
    })
    assert dup_res.status_code == 409
    assert dup_res.json()["success"] is False

    # 3. Update Driver
    put_res = client.put(f"/api/v1/drivers/{driver_id}", json={
        "full_name": "Phạm Văn K (Trưởng đoàn)",
        "phone_number": "0988888888"
    })
    assert put_res.status_code == 200
    assert put_res.json()["data"]["full_name"] == "Phạm Văn K (Trưởng đoàn)"

    # 4. Change Status
    patch_res = client.patch(f"/api/v1/drivers/{driver_id}/status", json={
        "status": "INACTIVE",
        "reason": "Nghỉ phép thường niên"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["status"] == "INACTIVE"
