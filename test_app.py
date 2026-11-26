import pytest

from conftest import auth



@pytest.mark.asyncio
async def test_register_success(client, user_data):
    r = await client.post("/api/register", json=user_data)
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"]
    assert "password" not in body


@pytest.mark.asyncio
async def test_register_duplicate_username(client, registered_user):
    r = await client.post("/api/register", json=registered_user_payload(registered_user))
    assert r.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("email", "not-an-email"),
    ("email", ""),
    ("password", ""),
    ("username", "   "),
    ("name", ""),
])
async def test_register_invalid_input(client, user_data, field, value):
    user_data[field] = value
    r = await client.post("/api/register", json=user_data)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_field(client, user_data):
    del user_data["email"]
    r = await client.post("/api/register", json=user_data)
    assert r.status_code == 422



@pytest.mark.asyncio
async def test_login_success(client, registered_user):
    r = await client.post("/api/login", json={
        "username": registered_user["username"],
        "password": registered_user["password"],
    })
    assert r.status_code == 200
    assert r.json()["access_token"]


@pytest.mark.asyncio
async def test_login_wrong_password(client, registered_user):
    r = await client.post("/api/login", json={
        "username": registered_user["username"],
        "password": "wrong-password",
    })
    assert r.status_code == 401
    assert "access_token" not in r.json()


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    r = await client.post("/api/login", json={"username": "no_such_user_xyz", "password": "x"})
    assert r.status_code == 401



@pytest.mark.asyncio
async def test_get_profile_success(client, registered_user):
    r = await client.get("/api/profile", headers=auth(registered_user["token"]))
    assert r.status_code == 200
    assert r.json() == {
        "username": registered_user["username"],
        "email": registered_user["email"],
        "name": registered_user["name"],
    }


@pytest.mark.asyncio
async def test_get_profile_does_not_leak_password(client, registered_user):
    r = await client.get("/api/profile", headers=auth(registered_user["token"]))
    assert "password" not in r.text.lower()


@pytest.mark.asyncio
async def test_get_profile_without_token(client):
    r = await client.get("/api/profile")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_profile_invalid_token(client):
    r = await client.get("/api/profile", headers=auth("invalid.token.value"))
    assert r.status_code == 401



@pytest.mark.asyncio
async def test_update_profile_success(client, registered_user):
    new = {"email": "new_" + registered_user["email"], "name": "Test User 2"}
    r = await client.put("/api/profile", headers=auth(registered_user["token"]), json=new)
    assert r.status_code == 200
    assert r.json() == {"username": registered_user["username"], **new}


@pytest.mark.asyncio
async def test_update_profile_is_persisted(client, registered_user):
    new = {"email": "persist_" + registered_user["email"], "name": "Persisted Name"}
    await client.put("/api/profile", headers=auth(registered_user["token"]), json=new)
    r = await client.get("/api/profile", headers=auth(registered_user["token"]))
    assert r.json()["email"] == new["email"]
    assert r.json()["name"] == new["name"]


@pytest.mark.asyncio
async def test_update_profile_invalid_email(client, registered_user):
    r = await client.put("/api/profile", headers=auth(registered_user["token"]),
                         json={"email": "broken-email"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_profile_without_token(client):
    r = await client.put("/api/profile", json={"name": "Hacker"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_username_cannot_be_changed(client, registered_user):
    r = await client.put("/api/profile", headers=auth(registered_user["token"]),
                         json={"username": "hacked", "name": "Same User"})
    assert r.status_code in (200, 422)
    p = await client.get("/api/profile", headers=auth(registered_user["token"]))
    assert p.json()["username"] == registered_user["username"]


@pytest.mark.asyncio
async def test_full_flow_register_login_view_edit(client, user_data):
    reg = await client.post("/api/register", json=user_data)
    assert reg.status_code == 201

    login = await client.post("/api/login", json={
        "username": user_data["username"], "password": user_data["password"]})
    assert login.status_code == 200
    headers = auth(login.json()["access_token"])

    assert (await client.get("/api/profile", headers=headers)).status_code == 200

    upd = await client.put("/api/profile", headers=headers, json={"name": "Flow User"})
    assert upd.status_code == 200
    assert upd.json()["name"] == "Flow User"


def registered_user_payload(ru: dict) -> dict:
    return {k: ru[k] for k in ("username", "password", "email", "name")}
