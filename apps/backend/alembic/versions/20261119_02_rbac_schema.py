"""Add RBAC reference schema and delegated department scopes.

Revision ID: 20261119_02
Revises: 20261119_01
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261119_02"
down_revision: str | None = "20261119_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# These UUIDs are migration data only. Application authorization resolves stable role codes,
# never a numeric or UUID role identifier supplied by a client.
REFERENCE_ROLES = (
    ("6c55ca72-3734-5f2b-a3a8-fc17ed4bf301", "chief_admin"),
    ("cd1b7e4e-8c57-5d16-873f-11a188eb4c5d", "standard_admin"),
    ("69e1c351-171d-5085-aac9-10c02d7d1d8a", "employee"),
)


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )
    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_departments_code"),
    )

    role_values = ", ".join(f"('{role_id}', '{code}')" for role_id, code in REFERENCE_ROLES)
    op.execute(
        sa.text(
            "INSERT INTO roles (id, code) VALUES "
            f"{role_values} "
            "ON CONFLICT (code) DO NOTHING"
        )
    )
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF (SELECT count(*) FROM roles WHERE code IN "
            "('chief_admin', 'standard_admin', 'employee')) <> 3 THEN "
            "RAISE EXCEPTION 'RBAC reference roles are incomplete'; "
            "END IF; END $$"
        )
    )
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM accounts a WHERE a.role_id IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM roles r WHERE r.id = a.role_id)) THEN "
            "RAISE EXCEPTION 'accounts.role_id contains an unrecognized role reference'; "
            "END IF; "
            "IF EXISTS (SELECT 1 FROM accounts WHERE department_id IS NOT NULL) THEN "
            "RAISE EXCEPTION 'accounts.department_id requires approved department reference data'; "
            "END IF; END $$"
        )
    )

    op.create_foreign_key(
        "fk_accounts_role_id_roles",
        "accounts",
        "roles",
        ["role_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_accounts_department_id_departments",
        "accounts",
        "departments",
        ["department_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_accounts_role_id", "accounts", ["role_id"])
    op.create_index("ix_accounts_department_id", "accounts", ["department_id"])

    op.create_table(
        "admin_scopes",
        sa.Column("admin_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("admin_account_id", "department_id", name="pk_admin_scopes"),
    )
    op.create_index("ix_admin_scopes_department_id", "admin_scopes", ["department_id"])


def downgrade() -> None:
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM admin_scopes) "
            "OR EXISTS (SELECT 1 FROM accounts WHERE role_id IS NOT NULL OR department_id IS NOT NULL) THEN "
            "RAISE EXCEPTION 'RBAC downgrade is blocked while role, department, or scope data exists'; "
            "END IF; END $$"
        )
    )
    op.drop_index("ix_admin_scopes_department_id", table_name="admin_scopes")
    op.drop_table("admin_scopes")
    op.drop_index("ix_accounts_department_id", table_name="accounts")
    op.drop_index("ix_accounts_role_id", table_name="accounts")
    op.drop_constraint("fk_accounts_department_id_departments", "accounts", type_="foreignkey")
    op.drop_constraint("fk_accounts_role_id_roles", "accounts", type_="foreignkey")
    op.drop_table("departments")
    op.drop_table("roles")
