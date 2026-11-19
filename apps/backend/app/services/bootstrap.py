from __future__ import annotations

import hmac
import os
import uuid

from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.models import Account, AuthenticationAuditEvent, BootstrapState, Role
from app.services.auth import PasswordService

TEST_TARGET = ("127.0.0.1", 5434, "chatalker_auth_migration_test")


class BootstrapError(Exception):
    pass


def assert_local_target(database_url: str) -> None:
    parsed = make_url(database_url)
    if (parsed.host, parsed.port, parsed.database) != TEST_TARGET:
        raise BootstrapError("Bootstrap target is not the approved isolated local test database")


def verify_operator_secret(entered: str, configured: str | None) -> None:
    if not configured or not entered or not hmac.compare_digest(entered, configured):
        raise BootstrapError("Operator authorization failed")


def bootstrap_chief_admin(db: Session, *, login: str, password: str, database_url: str, operator_secret: str, configured_secret: str | None) -> uuid.UUID:
    assert_local_target(database_url)
    verify_operator_secret(operator_secret, configured_secret)
    try:
        with db.begin():
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

