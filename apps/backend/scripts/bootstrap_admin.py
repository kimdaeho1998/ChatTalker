from __future__ import annotations

import getpass
import os

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.services.bootstrap import BootstrapError, bootstrap_chief_admin


def main() -> int:
    configured = os.getenv("CHATTALKER_BOOTSTRAP_SECRET")
    entered = getpass.getpass("Operator one-time secret: ")
    login = input("Chief administrator login: ").strip()
    password = getpass.getpass("Initial administrator password: ")
    settings = get_settings()
    database_url = settings.database_url or ""
    try:
        with get_session_factory()() as db:
            account_id = bootstrap_chief_admin(
                db,
                login=login,
                password=password,
                database_url=database_url,
                operator_secret=entered,
                configured_secret=configured,
                sslmode=settings.database_sslmode,
                execution_mode=os.getenv("CHATTALKER_BOOTSTRAP_TARGET", "local_test"),
                expected_supabase_project_ref=os.getenv("CHATTALKER_SUPABASE_PROJECT_REF"),
            )
        print(f"Bootstrap completed for account {account_id}")
        return 0
    except BootstrapError as exc:
        print(f"Bootstrap denied: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
