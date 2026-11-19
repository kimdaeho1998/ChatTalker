import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError


@pytest.fixture()
def integration_engine() -> Engine:
    database_url = os.getenv("AUTH_INTEGRATION_DATABASE_URL")
    if database_url is None:
        pytest.skip("AUTH_INTEGRATION_DATABASE_URL is not configured")

    parsed = make_url(database_url)
    if (parsed.host, parsed.port, parsed.database) != (
        "127.0.0.1",
        5434,
        "chatalker_auth_migration_test",
    ):
        pytest.fail("Authentication integration tests require the isolated local test database")

    engine = create_engine(database_url, connect_args={"sslmode": "disable"})
    try:
        yield engine
    finally:
        engine.dispose()


def _insert_account(connection, *, login: str, status: str = "active", auth_version: int = 1) -> uuid.UUID:
    account_id = uuid.uuid4()
    connection.execute(
        text(
            """
            INSERT INTO accounts (id, login, status, password_verifier, password_change_required, auth_version)
            VALUES (:id, :login, :status, 'argon2id-placeholder', true, :auth_version)
            """
        ),
        {"id": account_id, "login": login, "status": status, "auth_version": auth_version},
    )
    return account_id


def test_postgres_schema_has_six_auth_tables_and_required_catalog_constraints(integration_engine: Engine) -> None:
    with integration_engine.connect() as connection:
        tables = set(
            connection.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                    "AND tablename IN ('accounts', 'sessions', 'refresh_token_families', "
                    "'refresh_tokens', 'bootstrap_state', 'authentication_audit_events')"
                )
            ).scalars()
        )
        constraint_names = set(
            connection.execute(
                text(
                    "SELECT conname FROM pg_constraint WHERE conrelid IN "
                    "('accounts'::regclass, 'sessions'::regclass, 'refresh_token_families'::regclass, "
                    "'refresh_tokens'::regclass, 'bootstrap_state'::regclass, "
                    "'authentication_audit_events'::regclass)"
                )
            ).scalars()
        )
        index_names = set(
            connection.execute(
                text(
                    "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' "
                    "AND tablename IN ('sessions', 'refresh_token_families', 'refresh_tokens', "
                    "'authentication_audit_events')"
                )
            ).scalars()
        )

    assert tables == {
        "accounts",
        "sessions",
        "refresh_token_families",
        "refresh_tokens",
        "bootstrap_state",
        "authentication_audit_events",
    }
    assert {"ck_accounts_status", "ck_accounts_auth_version", "ck_bootstrap_state_singleton"}.issubset(
        constraint_names
    )
    assert "uq_refresh_tokens_token_hash" in constraint_names
    assert "bootstrap_state_account_id_key" in constraint_names
    assert {
        "ix_sessions_account_id",
        "ix_refresh_token_families_account_id",
        "ix_refresh_tokens_family_id",
        "ix_authentication_audit_events_account_id_occurred_at",
    }.issubset(index_names)


def test_postgres_rejects_duplicate_login_invalid_status_and_auth_version(integration_engine: Engine) -> None:
    with integration_engine.connect() as connection:
        transaction = connection.begin()
        try:
            _insert_account(connection, login="duplicate-login")
            with pytest.raises(IntegrityError):
                _insert_account(connection, login="duplicate-login")
            transaction.rollback()
        finally:
            if transaction.is_active:
                transaction.rollback()

    for status, auth_version in (("invalid", 1), ("active", 0)):
        with integration_engine.connect() as connection:
            transaction = connection.begin()
            try:
                with pytest.raises(IntegrityError):
                    _insert_account(connection, login=str(uuid.uuid4()), status=status, auth_version=auth_version)
                transaction.rollback()
            finally:
                if transaction.is_active:
                    transaction.rollback()


def test_postgres_rejects_invalid_foreign_keys_and_duplicate_refresh_hash(integration_engine: Engine) -> None:
    with integration_engine.connect() as connection:
        transaction = connection.begin()
        try:
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO refresh_token_families (id, account_id, expires_at) "
                        "VALUES (:id, :account_id, now() + interval '7 days')"
                    ),
                    {"id": uuid.uuid4(), "account_id": uuid.uuid4()},
                )
            transaction.rollback()
        finally:
            if transaction.is_active:
                transaction.rollback()

    with integration_engine.connect() as connection:
        transaction = connection.begin()
        try:
            account_id = _insert_account(connection, login=str(uuid.uuid4()))
            family_id = uuid.uuid4()
            session_id = uuid.uuid4()
            connection.execute(
                text(
                    "INSERT INTO refresh_token_families (id, account_id, expires_at) "
                    "VALUES (:id, :account_id, now() + interval '7 days')"
                ),
                {"id": family_id, "account_id": account_id},
            )
            connection.execute(
                text(
                    "INSERT INTO sessions (id, account_id, auth_version, token_family_id, expires_at) "
                    "VALUES (:id, :account_id, 1, :family_id, now() + interval '15 minutes')"
                ),
                {"id": session_id, "account_id": account_id, "family_id": family_id},
            )
            token_parameters = {"family_id": family_id, "session_id": session_id, "token_hash": "hash-once"}
            connection.execute(
                text(
                    "INSERT INTO refresh_tokens (id, family_id, session_id, token_hash, expires_at) "
                    "VALUES (:id, :family_id, :session_id, :token_hash, now() + interval '7 days')"
                ),
                {"id": uuid.uuid4(), **token_parameters},
            )
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO refresh_tokens (id, family_id, session_id, token_hash, expires_at) "
                        "VALUES (:id, :family_id, :session_id, :token_hash, now() + interval '7 days')"
                    ),
                    {"id": uuid.uuid4(), **token_parameters},
                )
            transaction.rollback()
        finally:
            if transaction.is_active:
                transaction.rollback()


def test_postgres_enforces_bootstrap_singleton_and_audit_foreign_keys(integration_engine: Engine) -> None:
    with integration_engine.connect() as connection:
        transaction = connection.begin()
        try:
            first_account_id = _insert_account(connection, login=str(uuid.uuid4()))
            second_account_id = _insert_account(connection, login=str(uuid.uuid4()))
            connection.execute(
                text("INSERT INTO bootstrap_state (singleton_key, account_id) VALUES (true, :account_id)"),
                {"account_id": first_account_id},
            )
            with pytest.raises(IntegrityError):
                connection.execute(
                    text("INSERT INTO bootstrap_state (singleton_key, account_id) VALUES (true, :account_id)"),
                    {"account_id": second_account_id},
                )
            transaction.rollback()
        finally:
            if transaction.is_active:
                transaction.rollback()

    with integration_engine.connect() as connection:
        transaction = connection.begin()
        try:
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO authentication_audit_events "
                        "(id, account_id, event_type, result_code) VALUES (:id, :account_id, 'login', 'ok')"
                    ),
                    {"id": uuid.uuid4(), "account_id": uuid.uuid4()},
                )
            transaction.rollback()
        finally:
            if transaction.is_active:
                transaction.rollback()


def test_postgres_advisory_lock_is_single_winner_per_transaction(integration_engine: Engine) -> None:
    first = integration_engine.connect()
    second = integration_engine.connect()
    first_transaction = first.begin()
    second_transaction = second.begin()
    try:
        assert first.execute(text("SELECT pg_try_advisory_xact_lock(2026111901)")).scalar() is True
        assert second.execute(text("SELECT pg_try_advisory_xact_lock(2026111901)")).scalar() is False
    finally:
        first_transaction.rollback()
        second_transaction.rollback()
        first.close()
        second.close()
