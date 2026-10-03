import pytest


def test_register_and_login_flow(client):
    # 1. Register new user
    reg_payload = {
        "email": "developer@test.com",
        "password": "SecurePassword123!",
        "full_name": "Test Developer",
    }
    res = client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["email"] == "developer@test.com"
    assert "id" in data

    # 2. Duplicate registration should fail
    res_dup = client.post("/api/v1/auth/register", json=reg_payload)
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.json()["detail"]

    # 3. Login with wrong password should fail
    res_fail = client.post("/api/v1/auth/login", json={
        "email": "developer@test.com",
        "password": "WrongPassword",
    })
    assert res_fail.status_code == 401

    # 4. Login with correct password succeeds and returns JWT
    res_login = client.post("/api/v1/auth/login", json={
        "email": "developer@test.com",
        "password": "SecurePassword123!",
    })
    assert res_login.status_code == 200
    token_data = res_login.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 5. Access /me endpoint with token
    headers = {"Authorization": f"Bearer {token}"}
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert me_data["email"] == "developer@test.com"

    # 6. Access /me without token fails
    res_unauth = client.get("/api/v1/auth/me")
    assert res_unauth.status_code == 401


def test_projects_and_api_keys_flow(client):
    # Setup: Register and get token
    reg_res = client.post("/api/v1/auth/register", json={
        "email": "founder@startup.io",
        "password": "Password789!",
        "full_name": "Startup Founder",
    })
    token = client.post("/api/v1/auth/login", json={
        "email": "founder@startup.io",
        "password": "Password789!",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a project
    create_proj = client.post("/api/v1/projects", headers=headers, json={
        "name": "Production API",
        "description": "Main e-commerce backend",
        "retention_days": 14,
    })
    assert create_proj.status_code == 201
    proj_data = create_proj.json()
    project_id = proj_data["id"]
    assert proj_data["name"] == "Production API"
    assert proj_data["retention_days"] == 14

    # 2. List projects
    list_res = client.get("/api/v1/projects", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 3. Generate an API Key for project
    key_res = client.post(f"/api/v1/projects/{project_id}/api-keys", headers=headers, json={
        "name": "Prod Ingestion Key",
    })
    assert key_res.status_code == 201
    key_data = key_res.json()
    assert "raw_key" in key_data
    raw_key = key_data["raw_key"]
    assert raw_key.startswith("pw_live_")
    key_id = key_data["id"]
    assert key_data["key_prefix"] == raw_key[:12]

    # 4. List API keys (should NOT contain raw_key)
    keys_list_res = client.get(f"/api/v1/projects/{project_id}/api-keys", headers=headers)
    assert keys_list_res.status_code == 200
    keys = keys_list_res.json()
    assert len(keys) == 1
    assert "raw_key" not in keys[0]
    assert keys[0]["key_prefix"] == raw_key[:12]

    # 5. Revoke API key
    del_key_res = client.delete(f"/api/v1/projects/{project_id}/api-keys/{key_id}", headers=headers)
    assert del_key_res.status_code == 204

    # 6. Verify key list is now empty
    keys_after = client.get(f"/api/v1/projects/{project_id}/api-keys", headers=headers).json()
    assert len(keys_after) == 0

    # 7. Delete project
    del_proj_res = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert del_proj_res.status_code == 204

    # 8. Verify project list is now empty
    projs_after = client.get("/api/v1/projects", headers=headers).json()
    assert len(projs_after) == 0


def test_cross_tenant_isolation(client):
    # Register User A
    client.post("/api/v1/auth/register", json={
        "email": "alice@company.com",
        "password": "Password123!",
    })
    token_a = client.post("/api/v1/auth/login", json={
        "email": "alice@company.com",
        "password": "Password123!",
    }).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register User B
    client.post("/api/v1/auth/register", json={
        "email": "bob@rival.com",
        "password": "Password456!",
    })
    token_b = client.post("/api/v1/auth/login", json={
        "email": "bob@rival.com",
        "password": "Password456!",
    }).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Alice creates a project
    proj_a = client.post("/api/v1/projects", headers=headers_a, json={
        "name": "Alice Secret Project"
    }).json()
    proj_a_id = proj_a["id"]

    # Bob attempts to get Alice's project -> 404
    bob_get = client.get(f"/api/v1/projects/{proj_a_id}", headers=headers_b)
    assert bob_get.status_code == 404

    # Bob attempts to delete Alice's project -> 404
    bob_del = client.delete(f"/api/v1/projects/{proj_a_id}", headers=headers_b)
    assert bob_del.status_code == 404
