from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class Account(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled')", name="ck_accounts_status"),
        CheckConstraint("auth_version >= 1", name="ck_accounts_auth_version"),
    )

    login: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    password_verifier: Mapped[str] = mapped_column(Text, nullable=False)
    password_change_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    auth_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    department_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    role_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    sessions: Mapped[list[Session]] = relationship(back_populates="account")
    refresh_token_families: Mapped[list[RefreshTokenFamily]] = relationship(back_populates="account")


class RefreshTokenFamily(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "refresh_token_families"
    __table_args__ = (Index("ix_refresh_token_families_account_id", "account_id"),)

    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reuse_detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    account: Mapped[Account] = relationship(back_populates="refresh_token_families")
    sessions: Mapped[list[Session]] = relationship(back_populates="token_family")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(back_populates="family")


class Session(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_account_id", "account_id"),)

    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    auth_version: Mapped[int] = mapped_column(Integer, nullable=False)
    token_family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("refresh_token_families.id", ondelete="CASCADE"), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    account: Mapped[Account] = relationship(back_populates="sessions")
    token_family: Mapped[RefreshTokenFamily] = relationship(back_populates="sessions")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(back_populates="session")


class RefreshToken(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        Index("ix_refresh_tokens_family_id", "family_id"),
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("refresh_token_families.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    family: Mapped[RefreshTokenFamily] = relationship(back_populates="refresh_tokens")
    session: Mapped[Session] = relationship(back_populates="refresh_tokens")


class BootstrapState(CreatedAtMixin, Base):
    __tablename__ = "bootstrap_state"
    __table_args__ = (CheckConstraint("singleton_key", name="ck_bootstrap_state_singleton"),)

    singleton_key: Mapped[bool] = mapped_column(Boolean, primary_key=True, default=True)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuthenticationAuditEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "authentication_audit_events"
    __table_args__ = (Index("ix_authentication_audit_events_account_id_occurred_at", "account_id", "occurred_at"),)

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    result_code: Mapped[str] = mapped_column(String(64), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
