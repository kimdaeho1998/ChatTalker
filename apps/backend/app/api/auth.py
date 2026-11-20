from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.models import Account, AdminScope, Department, RefreshToken, RefreshTokenFamily, Role, Session as AuthSession
from app.services.auth import (AuthError, ForbiddenError, PasswordService, TokenService, _audit, _hash_refresh,
                               _revoke_account, can_manage, issue_session, role_code, validate_access)

router = APIRouter(tags=["authentication"])


def response(code: str, message: str, data: dict | None = None) -> dict:
    return {"code": code, "message": message, "correlation_id": str(uuid.uuid4()), "data": data or {}}


def db_session():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def tokens() -> TokenService:
    return TokenService(get_settings())


def current_account(authorization: Annotated[str | None, Header()] = None, db: Session = Depends(db_session), token_service: TokenService = Depends(tokens)) -> Account:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, detail="AUTH_INVALID")
    try:
        return validate_access(db, token_service, authorization[7:])
    except AuthError as exc:
        raise HTTPException(401, detail="AUTH_INVALID") from exc


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class PasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1)
    password_change_token: str = Field(min_length=1)


class ProvisionRequest(BaseModel):
    login: str = Field(min_length=1, max_length=320)
    initial_password: str = Field(min_length=1)
    department_id: uuid.UUID | None = None
    role_code: str = Field(pattern="^(chief_admin|standard_admin|employee)$")


class AccountPatch(BaseModel):
    status: str | None = Field(default=None, pattern="^(active|disabled)$")
    role_code: str | None = Field(default=None, pattern="^(chief_admin|standard_admin|employee)$")
    department_id: uuid.UUID | None = None
    scope_department_ids: list[uuid.UUID] | None = None


class RevokeRequest(BaseModel):
    session_id: uuid.UUID | None = None


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(db_session), token_service: TokenService = Depends(tokens)) -> dict:
    password_service = PasswordService()
    account = db.scalar(select(Account).where(Account.login == payload.login))
    if account is None or account.status != "active" or not password_service.verify(account.password_verifier, payload.password):
        _audit(db, "login", "AUTH_INVALID", account=account.id if account else None); db.commit()
        raise HTTPException(401, detail="AUTH_INVALID")
    if account.password_change_required:
        _audit(db, "login", "PASSWORD_CHANGE_REQUIRED", account=account.id); db.commit()
        return response("PASSWORD_CHANGE_REQUIRED", "Password change required", {"password_change_token": token_service.issue_password_change(account)})
    result = issue_session(db, account, token_service); _audit(db, "login", "OK", account=account.id); db.commit()
    return response("OK", "Authenticated", result)


@router.post("/auth/password")
def change_password(payload: PasswordRequest, db: Session = Depends(db_session), token_service: TokenService = Depends(tokens)) -> dict:
    try:
        claims = token_service.decode(payload.password_change_token, "password_change")
        account = db.scalar(select(Account).where(Account.id == uuid.UUID(str(claims["sub"]))).with_for_update())
    except (AuthError, ValueError, KeyError) as exc:
        raise HTTPException(401, detail="AUTH_INVALID") from exc
    if account is None or account.status != "active" or account.auth_version != int(claims["av"]) or not PasswordService().verify(account.password_verifier, payload.current_password):
        raise HTTPException(400, detail="AUTH_INVALID")
    account.password_verifier = PasswordService().hash(payload.new_password); account.password_change_required = False
    _revoke_account(db, account.id); account.auth_version += 1
    result = issue_session(db, account, token_service); _audit(db, "password_change", "OK", account=account.id); db.commit()
    return response("OK", "Password changed", result)


@router.post("/auth/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(db_session), token_service: TokenService = Depends(tokens)) -> dict:
    now = datetime.now(UTC)
    invalid = False
    with db.begin():
        token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash_refresh(payload.refresh_token)).with_for_update())
        if token is None:
            invalid = True
        else:
            family = db.scalar(select(RefreshTokenFamily).where(RefreshTokenFamily.id == token.family_id).with_for_update())
            session = db.scalar(select(AuthSession).where(AuthSession.id == token.session_id).with_for_update())
            account = db.scalar(select(Account).where(Account.id == family.account_id).with_for_update()) if family else None
            if token.consumed_at or token.expires_at <= now or family is None or session is None or account is None or family.revoked_at or session.revoked_at or account.status != "active":
                if family: family.revoked_at = now
                if account: _revoke_account(db, account.id)
                _audit(db, "refresh_reuse", "AUTH_INVALID", account=account.id if account else None)
                invalid = True
            else:
                token.consumed_at = now
                result = issue_session(db, account, token_service, family); _audit(db, "refresh", "OK", account=account.id)
    if invalid:
        raise HTTPException(401, detail="AUTH_INVALID")
    return response("OK", "Refreshed", result)


@router.post("/auth/logout")
def logout(account: Account = Depends(current_account), db: Session = Depends(db_session)) -> dict:
    _revoke_account(db, account.id); _audit(db, "logout", "OK", actor=account.id, account=account.id); db.commit()
    return response("OK", "Logged out")


def _require_admin(db: Session, actor: Account) -> str:
    try: return role_code(db, actor)
    except ForbiddenError as exc: raise HTTPException(403, detail="FORBIDDEN") from exc


ROLE_DISPLAY_NAMES = {
    "chief_admin": "Chief administrator",
    "standard_admin": "Standard administrator",
    "employee": "Employee",
}


def _department_data(department: Department | None) -> dict | None:
    if department is None:
        return None
    return {"department_id": str(department.id), "code": department.code, "name": department.name}


def _account_data(account: Account) -> dict:
    return {
        "account_id": str(account.id),
        "login": account.login,
        "status": account.status,
        "role": (
            {"code": account.role.code, "display_name": ROLE_DISPLAY_NAMES[account.role.code]}
            if account.role is not None
            else None
        ),
        "department": _department_data(account.department),
        "password_change_required": account.password_change_required,
    }


def _admin_account_filters(actor: Account, actor_role: str) -> list:
    if actor_role == "chief_admin":
        return []
    if actor_role == "standard_admin":
        scoped_departments = select(AdminScope.department_id).where(AdminScope.admin_account_id == actor.id)
        return [Account.department_id.in_(scoped_departments), Account.role.has(Role.code == "employee")]
    raise HTTPException(403, detail="FORBIDDEN")


@router.get("/auth/me")
def me(actor: Account = Depends(current_account), db: Session = Depends(db_session)) -> dict:
    account = db.scalar(
        select(Account)
        .options(selectinload(Account.role), selectinload(Account.department))
        .where(Account.id == actor.id)
    )
    if account is None:
        raise HTTPException(401, detail="AUTH_INVALID")
    current_role = role_code(db, account)
    scopes = db.scalars(
        select(Department)
        .join(AdminScope, AdminScope.department_id == Department.id)
        .where(AdminScope.admin_account_id == account.id)
        .order_by(Department.code.asc(), Department.id.asc())
    ).all()
    return response(
        "OK",
        "Current account",
        {
            **_account_data(account),
            "role_code": current_role,
            "admin_scopes": [_department_data(scope) for scope in scopes],
        },
    )


@router.get("/admin/accounts")
def list_accounts(
    actor: Account = Depends(current_account),
    db: Session = Depends(db_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(min_length=1, max_length=320)] = None,
    status: Literal["active", "disabled"] | None = None,
    department_id: uuid.UUID | None = None,
) -> dict:
    filters = _admin_account_filters(actor, _require_admin(db, actor))
    if search is not None:
        filters.append(Account.login.ilike(f"%{search}%"))
    if status is not None:
        filters.append(Account.status == status)
    if department_id is not None:
        filters.append(Account.department_id == department_id)
    total = db.scalar(select(func.count()).select_from(Account).where(*filters)) or 0
    accounts = db.scalars(
        select(Account)
        .options(selectinload(Account.role), selectinload(Account.department))
        .where(*filters)
        .order_by(Account.created_at.asc(), Account.id.asc())
        .offset(offset)
        .limit(limit)
    ).all()
    return response("OK", "Accounts", {"items": [_account_data(account) for account in accounts], "total": total, "limit": limit, "offset": offset})


@router.get("/admin/accounts/{account_id}")
def account_detail(account_id: uuid.UUID, actor: Account = Depends(current_account), db: Session = Depends(db_session)) -> dict:
    _require_admin(db, actor)
    account = db.scalar(
        select(Account)
        .options(selectinload(Account.role), selectinload(Account.department))
        .where(Account.id == account_id)
    )
    if account is None:
        raise HTTPException(404, detail="NOT_FOUND")
    # The established administrator error contract uses 403 for an existing, out-of-scope account.
    if not can_manage(db, actor, account):
        raise HTTPException(403, detail="FORBIDDEN")
    return response("OK", "Account", _account_data(account))


@router.get("/admin/departments")
def list_departments(actor: Account = Depends(current_account), db: Session = Depends(db_session)) -> dict:
    actor_role = _require_admin(db, actor)
    statement = select(Department)
    if actor_role == "standard_admin":
        statement = statement.join(AdminScope, AdminScope.department_id == Department.id).where(AdminScope.admin_account_id == actor.id)
    elif actor_role != "chief_admin":
        raise HTTPException(403, detail="FORBIDDEN")
    departments = db.scalars(statement.order_by(Department.code.asc(), Department.id.asc())).all()
    return response("OK", "Departments", {"items": [_department_data(department) for department in departments]})


@router.get("/admin/roles")
def list_roles(actor: Account = Depends(current_account), db: Session = Depends(db_session)) -> dict:
    actor_role = _require_admin(db, actor)
    statement = select(Role)
    if actor_role == "standard_admin":
        statement = statement.where(Role.code == "employee")
    elif actor_role != "chief_admin":
        raise HTTPException(403, detail="FORBIDDEN")
    roles = db.scalars(statement.order_by(Role.code.asc())).all()
    return response("OK", "Roles", {"items": [{"code": role.code, "display_name": ROLE_DISPLAY_NAMES[role.code]} for role in roles]})


@router.post("/admin/accounts")
def provision(payload: ProvisionRequest, actor: Account = Depends(current_account), db: Session = Depends(db_session)) -> dict:
    actor_role = _require_admin(db, actor)
    role = db.scalar(select(Role).where(Role.code == payload.role_code)); department = db.scalar(select(Department).where(Department.id == payload.department_id)) if payload.department_id else None
    if role is None or (payload.department_id and department is None) or (actor_role == "standard_admin" and (payload.role_code != "employee" or payload.department_id is None or db.scalar(select(AdminScope).where(AdminScope.admin_account_id == actor.id, AdminScope.department_id == payload.department_id)) is None)) or actor_role == "employee":
        raise HTTPException(403, detail="FORBIDDEN")
    try:
        account = Account(login=payload.login, password_verifier=PasswordService().hash(payload.initial_password), password_change_required=True, role_id=role.id, department_id=payload.department_id)
        db.add(account); db.flush(); _audit(db, "account_provision", "OK", actor=actor.id, account=account.id); db.commit()
        return response("OK", "Account provisioned", {"account_id": str(account.id)})
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, detail="CONFLICT") from exc


@router.patch("/admin/accounts/{account_id}")
def update_account(account_id: uuid.UUID, payload: AccountPatch, actor: Account = Depends(current_account), db: Session = Depends(db_session)) -> dict:
    actor_role = _require_admin(db, actor)
    target = db.scalar(select(Account).where(Account.id == account_id).with_for_update())
    if target is None: raise HTTPException(404, detail="NOT_FOUND")
    admin_change = payload.role_code is not None or payload.scope_department_ids is not None
    if not can_manage(db, actor, target, administrator_change=admin_change): raise HTTPException(403, detail="FORBIDDEN")
    if actor_role == "standard_admin" and (admin_change or payload.status is None and payload.department_id is None): raise HTTPException(403, detail="FORBIDDEN")
    if payload.role_code is not None:
            role = db.scalar(select(Role).where(Role.code == payload.role_code))
            if role is None: raise HTTPException(400, detail="INVALID_ROLE")
            target.role_id = role.id
    if payload.department_id is not None:
            if db.scalar(select(Department).where(Department.id == payload.department_id)) is None: raise HTTPException(400, detail="INVALID_DEPARTMENT")
            target.department_id = payload.department_id
    if payload.status is not None:
            target.status = payload.status
    if payload.scope_department_ids is not None:
            if payload.role_code is None and role_code(db, target) != "standard_admin": raise HTTPException(400, detail="INVALID_SCOPE")
            db.query(AdminScope).filter(AdminScope.admin_account_id == target.id).delete(synchronize_session=False)
            for department_id in set(payload.scope_department_ids): db.add(AdminScope(admin_account_id=target.id, department_id=department_id))
    if payload.status == "disabled" or admin_change:
        target.auth_version += 1; _revoke_account(db, target.id)
    _audit(db, "account_update", "OK", actor=actor.id, account=target.id); db.commit()
    return response("OK", "Account updated", {"account_id": str(target.id)})


@router.post("/admin/accounts/{account_id}/sessions/revoke")
def revoke_sessions(account_id: uuid.UUID, payload: RevokeRequest, actor: Account = Depends(current_account), db: Session = Depends(db_session)) -> dict:
    _require_admin(db, actor)
    target = db.scalar(select(Account).where(Account.id == account_id).with_for_update())
    if target is None: raise HTTPException(404, detail="NOT_FOUND")
    if not can_manage(db, actor, target): raise HTTPException(403, detail="FORBIDDEN")
    if payload.session_id:
            session = db.scalar(select(AuthSession).where(AuthSession.id == payload.session_id, AuthSession.account_id == target.id).with_for_update())
            if session: session.revoked_at = datetime.now(UTC)
    else: _revoke_account(db, target.id)
    _audit(db, "session_revoke", "OK", actor=actor.id, account=target.id); db.commit()
    return response("OK", "Sessions revoked")
