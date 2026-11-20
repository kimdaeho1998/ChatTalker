import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.main import create_app
from app.services.auth import PasswordService
import app.api.auth as auth_api


@pytest.fixture()
def client(monkeypatch):
    database_url = os.getenv("AUTH_INTEGRATION_DATABASE_URL")
    if database_url is None:
        pytest.skip("AUTH_INTEGRATION_DATABASE_URL is not configured")
    parsed = make_url(database_url)
    if (parsed.host, parsed.port, parsed.database) != ("127.0.0.1", 5434, "chatalker_auth_migration_test"):
        pytest.fail("Authentication API tests require the isolated local test database")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("DATABASE_SSLMODE", "disable")
    monkeypatch.setenv("JWT_SECRET", "integration-test-secret-with-at-least-thirty-two-characters")
    get_settings.cache_clear()
    engine = create_engine(database_url, connect_args={"sslmode": "disable"})
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE authentication_audit_events, refresh_tokens, sessions, refresh_token_families, bootstrap_state, admin_scopes, accounts, departments CASCADE"))
    try:
        yield TestClient(create_app()), engine
    finally:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE authentication_audit_events, refresh_tokens, sessions, refresh_token_families, bootstrap_state, admin_scopes, accounts, departments CASCADE"))
        engine.dispose(); get_settings.cache_clear()


def seed_account(engine, login: str, password: str, role: str = "employee", *, required: bool = False, active: bool = True, department_id=None):
    account_id = uuid.uuid4()
    with engine.begin() as connection:
        role_id = connection.execute(text("SELECT id FROM roles WHERE code = :code"), {"code": role}).scalar_one()
        connection.execute(text("INSERT INTO accounts (id, login, status, password_verifier, password_change_required, auth_version, role_id, department_id) VALUES (:id, :login, :status, :verifier, :required, 1, :role_id, :department_id)"), {"id": account_id, "login": login, "status": "active" if active else "disabled", "verifier": PasswordService().hash(password), "required": required, "role_id": role_id, "department_id": department_id})
    return account_id


def access_token(http, login: str, password: str) -> str:
    result = http.post("/auth/login", json={"login": login, "password": password})
    assert result.status_code == 200
    return result.json()["data"]["access_token"]


def test_login_refresh_reuse_and_logout(client):
    http, engine = client
    seed_account(engine, "employee", "correct-password")
    invalid = http.post("/auth/login", json={"login": "unknown", "password": "wrong"})
    wrong = http.post("/auth/login", json={"login": "employee", "password": "wrong"})
    assert invalid.status_code == wrong.status_code == 401
    login = http.post("/auth/login", json={"login": "employee", "password": "correct-password"})
    assert login.status_code == 200
    tokens = login.json()["data"]
    assert tokens["access_expires_in"] == 900 and tokens["refresh_expires_in"] == 604800
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM refresh_tokens WHERE token_hash = :raw"), {"raw": tokens["refresh_token"]}).scalar_one() == 0
    refreshed = http.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["data"]["refresh_token"] != tokens["refresh_token"]
    reused = http.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401
    assert http.post("/auth/refresh", json={"refresh_token": refreshed.json()["data"]["refresh_token"]}).status_code == 401
    assert http.post("/auth/logout", headers={"Authorization": "Bearer " + tokens["access_token"]}).status_code == 401


def test_first_password_change_and_deactivation(client):
    http, engine = client
    account_id = seed_account(engine, "first", "old-password", required=True)
    response = http.post("/auth/login", json={"login": "first", "password": "old-password"})
    assert response.json()["code"] == "PASSWORD_CHANGE_REQUIRED"
    changed = http.post("/auth/password", json={"current_password": "old-password", "new_password": "new-password", "password_change_token": response.json()["data"]["password_change_token"]})
    assert changed.status_code == 200
    access = changed.json()["data"]["access_token"]
    with engine.begin() as connection:
        connection.execute(text("UPDATE accounts SET status = 'disabled', auth_version = auth_version + 1 WHERE id = :id"), {"id": account_id})
    assert http.post("/auth/logout", headers={"Authorization": "Bearer " + access}).status_code == 401


def test_concurrent_refresh_has_one_winner(client):
    http, engine = client
    seed_account(engine, "concurrent", "password")
    refresh_token = http.post("/auth/login", json={"login": "concurrent", "password": "password"}).json()["data"]["refresh_token"]
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: http.post("/auth/refresh", json={"refresh_token": refresh_token}), range(2)))
    results = [response.status_code for response in responses]
    assert sorted(results) == [200, 401]
    winner = next(response for response in responses if response.status_code == 200).json()["data"]["refresh_token"]
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM refresh_tokens t JOIN refresh_token_families f ON f.id = t.family_id WHERE t.consumed_at IS NULL AND f.revoked_at IS NULL")).scalar_one() == 0
        assert connection.execute(text("SELECT count(*) FROM refresh_token_families WHERE revoked_at IS NOT NULL")).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM sessions WHERE revoked_at IS NOT NULL")).scalar_one() >= 1
    assert http.post("/auth/refresh", json={"refresh_token": winner}).status_code == 401


def test_rbac_scope_and_employee_denial(client):
    http, engine = client
    department_a, department_b = uuid.uuid4(), uuid.uuid4()
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO departments (id, code, name) VALUES (:id, 'a', 'A'), (:id2, 'b', 'B')"), {"id": department_a, "id2": department_b})
    standard_id = seed_account(engine, "standard", "password", "standard_admin", department_id=department_a)
    seed_account(engine, "other", "password", department_id=department_b)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO admin_scopes (admin_account_id, department_id) VALUES (:id, :department_id)"), {"id": standard_id, "department_id": department_a})
    token = http.post("/auth/login", json={"login": "standard", "password": "password"}).json()["data"]["access_token"]
    denied = http.post("/admin/accounts", headers={"Authorization": "Bearer " + token}, json={"login": "bad", "initial_password": "pass", "role_code": "employee", "department_id": str(department_b)})
    allowed = http.post("/admin/accounts", headers={"Authorization": "Bearer " + token}, json={"login": "good", "initial_password": "pass", "role_code": "employee", "department_id": str(department_a)})
    assert denied.status_code == 403 and allowed.status_code == 200
    employee_token = http.post("/auth/login", json={"login": "other", "password": "password"}).json()["data"]["access_token"]
    assert http.post("/admin/accounts", headers={"Authorization": "Bearer " + employee_token}, json={"login": "no", "initial_password": "pass", "role_code": "employee", "department_id": str(department_b)}).status_code == 403


def test_chief_admin_self_protection_stale_authorization_and_audit(client):
    http, engine = client
    chief_id = seed_account(engine, "chief", "password", "chief_admin")
    standard_id = seed_account(engine, "standard", "password", "standard_admin")
    chief_token = http.post("/auth/login", json={"login": "chief", "password": "password"}).json()["data"]["access_token"]
    headers = {"Authorization": "Bearer " + chief_token}
    provisioned = http.post("/admin/accounts", headers=headers, json={"login": "new-admin", "initial_password": "pass", "role_code": "standard_admin"})
    assert provisioned.status_code == 200
    assert http.patch(f"/admin/accounts/{chief_id}", headers=headers, json={"role_code": "employee"}).status_code == 403
    with engine.begin() as connection:
        employee_role = connection.execute(text("SELECT id FROM roles WHERE code = 'employee'")).scalar_one()
        connection.execute(text("UPDATE accounts SET role_id = :role_id, auth_version = auth_version + 1 WHERE id = :id"), {"role_id": employee_role, "id": chief_id})
    assert http.post(f"/admin/accounts/{standard_id}/sessions/revoke", headers=headers, json={}).status_code == 401
    with engine.connect() as connection:
        events = set(connection.execute(text("SELECT event_type FROM authentication_audit_events")).scalars())
    assert {"login", "account_provision"}.issubset(events)


def test_audit_failure_rolls_back_provisioning(client, monkeypatch):
    http, engine = client
    seed_account(engine, "chief", "password", "chief_admin")
    token = http.post("/auth/login", json={"login": "chief", "password": "password"}).json()["data"]["access_token"]

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("injected audit failure")

    monkeypatch.setattr(auth_api, "_audit", fail_audit)
    with pytest.raises(RuntimeError):
        http.post("/admin/accounts", headers={"Authorization": "Bearer " + token}, json={"login": "rolled-back", "initial_password": "pass", "role_code": "employee"})
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM accounts WHERE login = 'rolled-back'")).scalar_one() == 0


def test_stale_department_scope_is_rechecked(client):
    http, engine = client
    department_id = uuid.uuid4()
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO departments (id, code, name) VALUES (:id, 'scope', 'Scope')"), {"id": department_id})
    standard_id = seed_account(engine, "standard", "password", "standard_admin", department_id=department_id)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO admin_scopes (admin_account_id, department_id) VALUES (:id, :department_id)"), {"id": standard_id, "department_id": department_id})
    access = http.post("/auth/login", json={"login": "standard", "password": "password"}).json()["data"]["access_token"]
    headers = {"Authorization": "Bearer " + access}
    assert http.post("/admin/accounts", headers=headers, json={"login": "before", "initial_password": "pass", "role_code": "employee", "department_id": str(department_id)}).status_code == 200
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM admin_scopes WHERE admin_account_id = :id"), {"id": standard_id})
    denied = http.post("/admin/accounts", headers=headers, json={"login": "after", "initial_password": "pass", "role_code": "employee", "department_id": str(department_id)})
    assert denied.status_code == 403
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM accounts WHERE login = 'after'")).scalar_one() == 0


def test_refresh_audit_failure_rolls_back_rotation(client, monkeypatch):
    http, engine = client
    seed_account(engine, "refresh-rollback", "password")
    raw = http.post("/auth/login", json={"login": "refresh-rollback", "password": "password"}).json()["data"]["refresh_token"]
    before = engine.connect().execute(text("SELECT count(*) FROM refresh_tokens")).scalar_one()
    original = auth_api._audit
    monkeypatch.setattr(auth_api, "_audit", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("injected")))
    with pytest.raises(RuntimeError):
        http.post("/auth/refresh", json={"refresh_token": raw})
    monkeypatch.setattr(auth_api, "_audit", original)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM refresh_tokens")).scalar_one() == before
        assert connection.execute(text("SELECT consumed_at FROM refresh_tokens")).scalar_one() is None
    assert http.post("/auth/refresh", json={"refresh_token": raw}).status_code == 200


def test_deactivation_audit_failure_rolls_back(client, monkeypatch):
    http, engine = client
    chief_id = seed_account(engine, "chief", "password", "chief_admin")
    target_id = seed_account(engine, "target", "password")
    chief_token = http.post("/auth/login", json={"login": "chief", "password": "password"}).json()["data"]["access_token"]
    target_access = http.post("/auth/login", json={"login": "target", "password": "password"}).json()["data"]["access_token"]
    monkeypatch.setattr(auth_api, "_audit", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("injected")))
    with pytest.raises(RuntimeError):
        http.patch(f"/admin/accounts/{target_id}", headers={"Authorization": "Bearer " + chief_token}, json={"status": "disabled"})
    with engine.connect() as connection:
        status, version = connection.execute(text("SELECT status, auth_version FROM accounts WHERE id = :id"), {"id": target_id}).one()
    assert (status, version) == ("active", 1)
    monkeypatch.undo()
    assert http.post("/auth/logout", headers={"Authorization": "Bearer " + target_access}).status_code == 200


def test_authentication_audit_event_coverage_and_redaction(client):
    http, engine = client
    chief_id = seed_account(engine, "chief", "audit-password", "chief_admin")
    target_id = seed_account(engine, "target", "audit-password")
    chief = http.post("/auth/login", json={"login": "chief", "password": "audit-password"}).json()["data"]
    headers = {"Authorization": "Bearer " + chief["access_token"]}
    assert http.post("/auth/login", json={"login": "chief", "password": "wrong"}).status_code == 401
    assert http.post("/admin/accounts", headers=headers, json={"login": "provisioned", "initial_password": "provision-password", "role_code": "employee"}).status_code == 200
    assert http.post(f"/admin/accounts/{target_id}/sessions/revoke", headers=headers, json={}).status_code == 200
    assert http.patch(f"/admin/accounts/{target_id}", headers=headers, json={"status": "disabled"}).status_code == 200
    assert http.post("/auth/logout", headers=headers).status_code == 200
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT event_type, result_code, correlation_id FROM authentication_audit_events")).all()
        rendered = str(rows)
    event_types = {row[0] for row in rows}
    assert {"login", "account_provision", "session_revoke", "account_update", "logout"}.issubset(event_types)
    assert "audit-password" not in rendered and "provision-password" not in rendered and chief["access_token"] not in rendered


@pytest.mark.parametrize("case", ["missing_sid", "tampered_sid", "missing_av"])
def test_api_rejects_missing_or_tampered_session_claims(client, case):
    http, engine = client
    account_id = seed_account(engine, "claims", "password")
    issued = http.post("/auth/login", json={"login": "claims", "password": "password"}).json()["data"]
    now = datetime.now(UTC)
    claims = {"sub": str(account_id), "sid": issued["session_id"], "av": 1, "purpose": "access", "iat": now, "exp": now + timedelta(minutes=5), "iss": "chatalker-api", "aud": "chatalker-desktop"}
    if case == "missing_sid": claims.pop("sid")
    if case == "tampered_sid": claims["sid"] = str(uuid.uuid4())
    if case == "missing_av": claims.pop("av")
    token = jwt.encode(claims, "integration-test-secret-with-at-least-thirty-two-characters", algorithm="HS256")
    assert http.post("/auth/logout", headers={"Authorization": "Bearer " + token}).status_code == 401
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM authentication_audit_events WHERE event_type = 'logout'")).scalar_one() == 0


def test_password_change_creates_redacted_audit_event(client):
    http, engine = client
    seed_account(engine, "password-change", "old-password", required=True)
    required = http.post("/auth/login", json={"login": "password-change", "password": "old-password"}).json()["data"]
    changed = http.post("/auth/password", json={"current_password": "old-password", "new_password": "new-password", "password_change_token": required["password_change_token"]})
    assert changed.status_code == 200
    assert http.post("/auth/login", json={"login": "password-change", "password": "old-password"}).status_code == 401
    assert http.post("/auth/login", json={"login": "password-change", "password": "new-password"}).status_code == 200
    with engine.connect() as connection:
        row = connection.execute(text("SELECT account_id, occurred_at, event_type FROM authentication_audit_events WHERE event_type = 'password_change'")).one()
        text_values = str(connection.execute(text("SELECT event_type, result_code, correlation_id FROM authentication_audit_events")).all())
    assert row[0] is not None and row[1] is not None and row[2] == "password_change"
    assert "old-password" not in text_values and "new-password" not in text_values and required["password_change_token"] not in text_values


def test_admin_read_apis_enforce_scope_and_redact_sensitive_fields(client):
    http, engine = client
    department_a, department_b = uuid.uuid4(), uuid.uuid4()
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO departments (id, code, name) VALUES (:a, 'alpha', 'Alpha'), (:b, 'bravo', 'Bravo')"),
            {"a": department_a, "b": department_b},
        )
    chief_id = seed_account(engine, "read-chief", "password", "chief_admin")
    standard_id = seed_account(engine, "read-standard", "password", "standard_admin", department_id=department_a)
    allowed_first = seed_account(engine, "alpha-visible-one", "password", department_id=department_a)
    allowed_second = seed_account(engine, "alpha-visible-two", "password", department_id=department_a)
    disabled_id = seed_account(engine, "alpha-disabled", "password", active=False, department_id=department_a)
    blocked_id = seed_account(engine, "bravo-hidden", "password", department_id=department_b)
    employee_id = seed_account(engine, "read-employee", "password", department_id=department_a)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO admin_scopes (admin_account_id, department_id) VALUES (:admin, :department)"),
            {"admin": standard_id, "department": department_a},
        )

    chief_headers = {"Authorization": "Bearer " + access_token(http, "read-chief", "password")}
    standard_headers = {"Authorization": "Bearer " + access_token(http, "read-standard", "password")}
    employee_headers = {"Authorization": "Bearer " + access_token(http, "read-employee", "password")}

    chief_list = http.get("/admin/accounts", headers=chief_headers)
    assert chief_list.status_code == 200
    assert {item["account_id"] for item in chief_list.json()["data"]["items"]} == {
        str(chief_id), str(standard_id), str(allowed_first), str(allowed_second), str(disabled_id), str(blocked_id), str(employee_id)
    }
    assert "password_verifier" not in str(chief_list.json()) and "token_hash" not in str(chief_list.json())
    assert http.get(f"/admin/accounts/{blocked_id}", headers=chief_headers).status_code == 200

    scoped = http.get("/admin/accounts", headers=standard_headers, params={"limit": 1, "offset": 0})
    assert scoped.status_code == 200
    assert scoped.json()["data"]["total"] == 4 and len(scoped.json()["data"]["items"]) == 1
    assert http.get(f"/admin/accounts/{allowed_first}", headers=standard_headers).status_code == 200
    assert http.get(f"/admin/accounts/{blocked_id}", headers=standard_headers).status_code == 403
    assert http.get("/admin/accounts", headers=standard_headers, params={"search": "bravo-hidden"}).json()["data"]["total"] == 0
    assert http.get("/admin/accounts", headers=standard_headers, params={"department_id": str(department_b)}).json()["data"]["total"] == 0
    assert http.get("/admin/accounts", headers=standard_headers, params={"department_id": str(department_a)}).json()["data"]["total"] == 4
    assert http.get("/admin/accounts", headers=standard_headers, params={"status": "active"}).json()["data"]["total"] == 3
    assert http.get("/admin/accounts", headers=standard_headers, params={"status": "disabled"}).json()["data"]["total"] == 1

    standard_departments = http.get("/admin/departments", headers=standard_headers)
    assert standard_departments.status_code == 200
    assert standard_departments.json()["data"]["items"] == [{"department_id": str(department_a), "code": "alpha", "name": "Alpha"}]
    standard_roles = http.get("/admin/roles", headers=standard_headers)
    assert standard_roles.status_code == 200
    assert standard_roles.json()["data"]["items"] == [{"code": "employee", "display_name": "Employee"}]
    chief_roles = http.get("/admin/roles", headers=chief_headers)
    assert {role["code"] for role in chief_roles.json()["data"]["items"]} == {"chief_admin", "standard_admin", "employee"}

    for path in ("/admin/accounts", f"/admin/accounts/{allowed_first}", "/admin/departments", "/admin/roles"):
        assert http.get(path, headers=employee_headers).status_code == 403


def test_current_user_reflects_current_scope_and_rejects_disabled_or_revoked_sessions(client):
    http, engine = client
    department_id = uuid.uuid4()
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO departments (id, code, name) VALUES (:id, 'current', 'Current')"), {"id": department_id})
    standard_id = seed_account(engine, "current-standard", "password", "standard_admin", department_id=department_id)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO admin_scopes (admin_account_id, department_id) VALUES (:admin, :department)"),
            {"admin": standard_id, "department": department_id},
        )
    headers = {"Authorization": "Bearer " + access_token(http, "current-standard", "password")}
    current = http.get("/auth/me", headers=headers)
    assert current.status_code == 200
    data = current.json()["data"]
    assert data["account_id"] == str(standard_id)
    assert data["role_code"] == "standard_admin"
    assert data["department"]["department_id"] == str(department_id)
    assert data["admin_scopes"] == [{"department_id": str(department_id), "code": "current", "name": "Current"}]
    assert "password_verifier" not in str(data) and "refresh_token" not in str(data)

    assert http.post("/auth/logout", headers=headers).status_code == 200
    assert http.get("/auth/me", headers=headers).status_code == 401

    disabled_id = seed_account(engine, "current-disabled", "password")
    disabled_headers = {"Authorization": "Bearer " + access_token(http, "current-disabled", "password")}
    with engine.begin() as connection:
        connection.execute(text("UPDATE accounts SET status = 'disabled', auth_version = auth_version + 1 WHERE id = :id"), {"id": disabled_id})
    assert http.get("/auth/me", headers=disabled_headers).status_code == 401
