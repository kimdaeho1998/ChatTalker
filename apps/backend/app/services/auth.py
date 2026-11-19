from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Account, AdminScope, AuthenticationAuditEvent, Department, RefreshToken, RefreshTokenFamily, Role, Session as AuthSession

ACCESS_TTL = timedelta(minutes=15)
REFRESH_TTL = timedelta(days=7)
JWT_ALGORITHM = "HS256"


class AuthError(Exception):
    pass


class ForbiddenError(Exception):
    pass


class PasswordService:
    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def hash(self, value: str) -> str:
        return self._hasher.hash(value)

    def verify(self, verifier: str, value: str) -> bool:
        try:
            return self._hasher.verify(verifier, value)
        except (InvalidHashError, VerifyMismatchError):
            return False


class TokenService:
    def __init__(self, settings: Settings) -> None:
        if settings.jwt_secret is None or len(settings.jwt_secret.get_secret_value()) < 32:
            raise RuntimeError("JWT_SECRET must be at least 32 characters")
        self._secret = settings.jwt_secret.get_secret_value()
        self._issuer = settings.jwt_issuer
        self._audience = settings.jwt_audience

    def issue_access(self, account: Account, session_id: uuid.UUID) -> str:
        now = datetime.now(UTC)
        return jwt.encode({"sub": str(account.id), "sid": str(session_id), "av": account.auth_version,
                           "purpose": "access", "iat": now, "exp": now + ACCESS_TTL,
                           "iss": self._issuer, "aud": self._audience}, self._secret, algorithm=JWT_ALGORITHM)

    def issue_password_change(self, account: Account) -> str:
        now = datetime.now(UTC)
        return jwt.encode({"sub": str(account.id), "av": account.auth_version, "purpose": "password_change",
                           "iat": now, "exp": now + ACCESS_TTL, "iss": self._issuer,
                           "aud": self._audience}, self._secret, algorithm=JWT_ALGORITHM)

    def decode(self, token: str, purpose: str) -> dict[str, object]:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[JWT_ALGORITHM], issuer=self._issuer,
                                audience=self._audience, options={"require": ["exp", "iat", "iss", "aud", "sub", "av", "purpose"]})
        except jwt.PyJWTError as exc:
            raise AuthError() from exc
        if claims.get("purpose") != purpose:
            raise AuthError()
        return claims


def _hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _audit(db: Session, event: str, result: str, actor: uuid.UUID | None = None, account: uuid.UUID | None = None,
           session: uuid.UUID | None = None) -> None:
    db.add(AuthenticationAuditEvent(actor_id=actor, account_id=account, session_id=session,
                                    event_type=event, result_code=result))


def _revoke_account(db: Session, account_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    db.execute(update(AuthSession).where(AuthSession.account_id == account_id, AuthSession.revoked_at.is_(None)).values(revoked_at=now))
    db.execute(update(RefreshTokenFamily).where(RefreshTokenFamily.account_id == account_id, RefreshTokenFamily.revoked_at.is_(None)).values(revoked_at=now))


def issue_session(db: Session, account: Account, token_service: TokenService,
                  family: RefreshTokenFamily | None = None) -> dict[str, object]:
    now = datetime.now(UTC)
    if family is None:
        family = RefreshTokenFamily(account_id=account.id, expires_at=now + REFRESH_TTL)
        db.add(family); db.flush()
    session = AuthSession(account_id=account.id, auth_version=account.auth_version, token_family_id=family.id, expires_at=now + ACCESS_TTL)
    db.add(session); db.flush()
    raw_refresh = secrets.token_urlsafe(48)
    db.add(RefreshToken(family_id=family.id, session_id=session.id, token_hash=_hash_refresh(raw_refresh), expires_at=now + REFRESH_TTL))
    return {"access_token": token_service.issue_access(account, session.id), "access_expires_in": 900,
            "refresh_token": raw_refresh, "refresh_expires_in": 604800, "session_id": str(session.id)}


def validate_access(db: Session, token_service: TokenService, bearer: str) -> Account:
    claims = token_service.decode(bearer, "access")
    try:
        account_id, session_id, version = uuid.UUID(str(claims["sub"])), uuid.UUID(str(claims["sid"])), int(claims["av"])
    except (ValueError, KeyError) as exc:
        raise AuthError() from exc
    account = db.scalar(select(Account).where(Account.id == account_id))
    session = db.scalar(select(AuthSession).where(AuthSession.id == session_id))
    if account is None or session is None or account.status != "active" or account.auth_version != version or session.revoked_at is not None or session.auth_version != version or session.expires_at <= datetime.now(UTC):
        raise AuthError()
    family = db.scalar(select(RefreshTokenFamily).where(RefreshTokenFamily.id == session.token_family_id))
    if family is None or family.revoked_at is not None:
        raise AuthError()
    return account


def role_code(db: Session, account: Account) -> str:
    if account.role_id is None:
        raise ForbiddenError()
    role = db.scalar(select(Role).where(Role.id == account.role_id))
    if role is None or role.code not in {"chief_admin", "standard_admin", "employee"}:
        raise ForbiddenError()
    return role.code


def can_manage(db: Session, actor: Account, target: Account, administrator_change: bool = False) -> bool:
    actor_role, target_role = role_code(db, actor), role_code(db, target)
    if actor_role == "chief_admin":
        return not (actor.id == target.id and administrator_change)
    if actor_role != "standard_admin" or target_role != "employee" or target.department_id is None:
        return False
    return db.scalar(select(AdminScope).where(AdminScope.admin_account_id == actor.id, AdminScope.department_id == target.department_id)) is not None
