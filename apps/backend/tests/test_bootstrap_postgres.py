import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.services.bootstrap import BootstrapError, assert_local_target, bootstrap_chief_admin
import app.services.bootstrap as bootstrap_service


@pytest.fixture()
def db():
    url = os.getenv("AUTH_INTEGRATION_DATABASE_URL")
    if not url or (make_url(url).host, make_url(url).port, make_url(url).database) != ("127.0.0.1", 5434, "chatalker_auth_migration_test"):
        pytest.skip("isolated local DB required")
    engine = create_engine(url, connect_args={"sslmode": "disable"})
    with engine.begin() as c: c.execute(text("TRUNCATE authentication_audit_events, bootstrap_state, accounts CASCADE"))
    yield sessionmaker(bind=engine)
    with engine.begin() as c: c.execute(text("TRUNCATE authentication_audit_events, bootstrap_state, accounts CASCADE"))
    engine.dispose()


def test_bootstrap_success_reentry_and_secret_guards(db):
    with db() as session:
        account_id = bootstrap_chief_admin(session, login="chief", password="password", database_url="postgresql+psycopg://x:x@127.0.0.1:5434/chatalker_auth_migration_test", operator_secret="entered", configured_secret="entered")
    with db() as session:
        assert session.execute(text("SELECT password_verifier LIKE '$argon2id%', password_change_required FROM accounts WHERE id=:id"), {"id": account_id}).one() == (True, True)
        assert session.execute(text("SELECT count(*) FROM bootstrap_state")).scalar_one() == 1
        assert session.execute(text("SELECT count(*) FROM authentication_audit_events WHERE event_type='bootstrap'")).scalar_one() == 1
        session.rollback()
        with pytest.raises(BootstrapError): bootstrap_chief_admin(session, login="again", password="password", database_url="postgresql+psycopg://x:x@127.0.0.1:5434/chatalker_auth_migration_test", operator_secret="entered", configured_secret="entered")
    with pytest.raises(BootstrapError): assert_local_target("postgresql+psycopg://x:x@host:5432/postgres")


def test_bootstrap_rejects_bad_or_missing_secret(db):
    with db() as session:
        for secret in (None, "wrong"):
            with pytest.raises(BootstrapError): bootstrap_chief_admin(session, login="chief", password="password", database_url="postgresql+psycopg://x:x@127.0.0.1:5434/chatalker_auth_migration_test", operator_secret="entered", configured_secret=secret)
        assert session.execute(text("SELECT count(*) FROM accounts")).scalar_one() == 0


def test_concurrent_bootstrap_has_single_winner(db):
    def run(login):
        with db() as session:
            try:
                return bootstrap_chief_admin(session, login=login, password="password", database_url="postgresql+psycopg://x:x@127.0.0.1:5434/chatalker_auth_migration_test", operator_secret="secret", configured_secret="secret")
            except BootstrapError:
                return None
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(run, ("chief-one", "chief-two")))
    assert sum(result is not None for result in results) == 1
    with db() as session:
        assert session.execute(text("SELECT count(*) FROM accounts a JOIN roles r ON r.id=a.role_id WHERE r.code='chief_admin'")).scalar_one() == 1
        assert session.execute(text("SELECT count(*) FROM bootstrap_state")).scalar_one() == 1
        assert session.execute(text("SELECT count(*) FROM authentication_audit_events WHERE event_type='bootstrap'")).scalar_one() == 1


def test_bootstrap_audit_failure_rolls_back(db, monkeypatch):
    original = bootstrap_service.AuthenticationAuditEvent
    monkeypatch.setattr(bootstrap_service, "AuthenticationAuditEvent", lambda **_: (_ for _ in ()).throw(RuntimeError("injected")))
    with db() as session:
        with pytest.raises(RuntimeError): bootstrap_chief_admin(session, login="chief", password="password", database_url="postgresql+psycopg://x:x@127.0.0.1:5434/chatalker_auth_migration_test", operator_secret="secret", configured_secret="secret")
    with db() as session:
        assert session.execute(text("SELECT count(*) FROM accounts")).scalar_one() == 0
        assert session.execute(text("SELECT count(*) FROM bootstrap_state")).scalar_one() == 0
        assert session.execute(text("SELECT count(*) FROM authentication_audit_events")).scalar_one() == 0
    monkeypatch.setattr(bootstrap_service, "AuthenticationAuditEvent", original)


def test_bootstrap_retries_after_rollback_with_new_secret(db, monkeypatch):
    monkeypatch.setattr(bootstrap_service, "AuthenticationAuditEvent", lambda **_: (_ for _ in ()).throw(RuntimeError("injected")))
    with db() as session:
        with pytest.raises(RuntimeError): bootstrap_chief_admin(session, login="chief", password="password", database_url="postgresql+psycopg://x:x@127.0.0.1:5434/chatalker_auth_migration_test", operator_secret="old", configured_secret="old")
    monkeypatch.undo()
    with db() as session:
        account_id = bootstrap_chief_admin(session, login="chief", password="password", database_url="postgresql+psycopg://x:x@127.0.0.1:5434/chatalker_auth_migration_test", operator_secret="new", configured_secret="new")
        assert account_id
    with db() as session:
        assert session.execute(text("SELECT count(*) FROM accounts")).scalar_one() == 1
        assert session.execute(text("SELECT count(*) FROM bootstrap_state")).scalar_one() == 1
        assert session.execute(text("SELECT count(*) FROM authentication_audit_events WHERE event_type='bootstrap'")).scalar_one() == 1
