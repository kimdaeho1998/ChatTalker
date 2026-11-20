from __future__ import annotations

import hmac
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.models import Account, AuthenticationAuditEvent, BootstrapState, Role
from app.services.auth import PasswordService

TEST_TARGET = ("127.0.0.1", 5434, "chatalker_auth_migration_test")
SUPABASE_TARGET = ("aws-0-ap-northeast-2.pooler.supabase.com", 5432, "postgres")
TLS_MODES = frozenset({"require", "verify-ca", "verify-full"})


class BootstrapError(Exception):
    pass


@dataclass(frozen=True)
class BootstrapTarget:
    kind: str
    database: str


def assert_local_target(database_url: str) -> None:
    resolve_bootstrap_target(
        database_url,
        sslmode="disable",
        execution_mode="local_test",
        expected_supabase_project_ref=None,
    )


def resolve_bootstrap_target(
    database_url: str,
    *,
    sslmode: str,
    execution_mode: str,
    expected_supabase_project_ref: str | None,
) -> BootstrapTarget:
    """Fail closed unless the URL is the local test DB or explicitly approved Supabase DB."""
    parsed = make_url(database_url)
    endpoint = (parsed.host, parsed.port, parsed.database)
    if endpoint == TEST_TARGET:
        if execution_mode != "local_test":
            raise BootstrapError("Local bootstrap requires local_test execution mode")
        return BootstrapTarget(kind="local_test", database=TEST_TARGET[2])

    if endpoint != SUPABASE_TARGET:
        raise BootstrapError("Bootstrap target is not approved")
    if execution_mode != "supabase":
        raise BootstrapError("Supabase bootstrap requires explicit supabase execution mode")
    if sslmode.lower() not in TLS_MODES:
        raise BootstrapError("Supabase bootstrap requires TLS")
    project_ref = _pooler_project_ref(parsed.username)
    if not expected_supabase_project_ref or not hmac.compare_digest(
        project_ref, expected_supabase_project_ref
    ):
        raise BootstrapError("Supabase project identifier is not approved")
    return BootstrapTarget(kind="supabase", database=SUPABASE_TARGET[2])


def assert_connected_target(db: Session, target: BootstrapTarget) -> None:
    if db.scalar(text("SELECT current_database()")) != target.database:
        raise BootstrapError("Connected database does not match approved bootstrap target")
    if target.kind == "supabase":
        raw_connection = db.connection().connection.driver_connection
        if not raw_connection.pgconn.ssl_in_use:
            raise BootstrapError("Supabase bootstrap connection is not using TLS")


def _pooler_project_ref(username: str | None) -> str:
    if not username or not username.startswith("postgres."):
        raise BootstrapError("Supabase pooler username does not contain a project identifier")
    project_ref = username.removeprefix("postgres.")
    if not re.fullmatch(r"[a-z0-9]{8,64}", project_ref):
        raise BootstrapError("Supabase project identifier format is invalid")
    return project_ref


def verify_operator_secret(entered: str, configured: str | None) -> None:
    if not configured or not entered or not hmac.compare_digest(entered, configured):
        raise BootstrapError("Operator authorization failed")


def bootstrap_chief_admin(
    db: Session,
    *,
    login: str,
    password: str,
    database_url: str,
    operator_secret: str,
    configured_secret: str | None,
    sslmode: str = "disable",
    execution_mode: str = "local_test",
    expected_supabase_project_ref: str | None = None,
) -> uuid.UUID:
    target = resolve_bootstrap_target(
        database_url,
        sslmode=sslmode,
        execution_mode=execution_mode,
        expected_supabase_project_ref=expected_supabase_project_ref,
    )
    verify_operator_secret(operator_secret, configured_secret)
    try:
        with db.begin():
            assert_connected_target(db, target)
            db.execute(text("SELECT pg_advisory_xact_lock(2026111901)"))
            if db.scalar(select(BootstrapState.singleton_key)) is not None:
                raise BootstrapError("Bootstrap already completed")
            chief = db.scalar(select(Role).where(Role.code == "chief_admin"))
            if chief is None:
                raise BootstrapError("chief_admin role seed is missing")
            if db.scalar(select(Account.id).join(Role).where(Role.code == "chief_admin")) is not None:
                raise BootstrapError("Chief administrator already exists")
            account = Account(login=login, password_verifier=PasswordService().hash(password), password_change_required=True, role_id=chief.id)
            db.add(account); db.flush()
            db.add(BootstrapState(singleton_key=True, account_id=account.id))
            db.add(AuthenticationAuditEvent(actor_id=None, account_id=account.id, event_type="bootstrap", result_code="OK"))
        return account.id
    finally:
        operator_secret = ""

