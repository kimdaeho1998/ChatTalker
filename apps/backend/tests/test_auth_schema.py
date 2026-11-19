from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.models import Base


def test_auth_models_register_expected_metadata() -> None:
    expected_tables = {
        "accounts",
        "sessions",
        "refresh_token_families",
        "refresh_tokens",
        "bootstrap_state",
        "authentication_audit_events",
    }

    assert expected_tables.issubset(Base.metadata.tables)


def test_auth_metadata_uses_required_constraints_and_relationships() -> None:
    accounts = Base.metadata.tables["accounts"]
    sessions = Base.metadata.tables["sessions"]
    refresh_tokens = Base.metadata.tables["refresh_tokens"]
    bootstrap_state = Base.metadata.tables["bootstrap_state"]
    audit_events = Base.metadata.tables["authentication_audit_events"]

    assert accounts.c.login.unique is True
    assert accounts.c.password_verifier.nullable is False
    assert sessions.c.account_id.foreign_keys
    assert sessions.c.token_family_id.foreign_keys
    assert refresh_tokens.c.family_id.foreign_keys
    assert refresh_tokens.c.session_id.foreign_keys
    assert refresh_tokens.c.token_hash.unique is None
    assert any(constraint.name == "uq_refresh_tokens_token_hash" for constraint in refresh_tokens.constraints)
    assert list(bootstrap_state.primary_key.columns.keys()) == ["singleton_key"]
    assert bootstrap_state.c.account_id.unique is True
    assert audit_events.c.account_id.foreign_keys
    assert audit_events.c.session_id.foreign_keys


def test_auth_metadata_compiles_for_postgresql() -> None:
    ddl = "\n".join(
        str(CreateTable(table).compile(dialect=postgresql.dialect()))
        for table in Base.metadata.sorted_tables
    )

    assert "CREATE TABLE accounts" in ddl
    assert "UUID" in ddl
    assert "bootstrap_state" in ddl
    assert "uq_refresh_tokens_token_hash" in ddl


def test_auth_migration_is_the_single_head_revision() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    script = ScriptDirectory.from_config(config)

    assert script.get_current_head() == "20261119_01"
    revision = script.get_revision("20261119_01")
    assert revision is not None
    assert revision.down_revision is None
