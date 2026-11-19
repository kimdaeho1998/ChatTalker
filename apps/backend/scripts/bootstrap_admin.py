from __future__ import annotations

import getpass
import os

from app.core.database import get_session_factory
from app.services.bootstrap import BootstrapError, bootstrap_chief_admin


def main() -> int:
    configured = os.getenv("CHATTALKER_BOOTSTRAP_SECRET")
    entered = getpass.getpass("Operator one-time secret: ")
    login = input("Chief administrator login: ").strip()
    password = getpass.getpass("Initial administrator password: ")
    database_url = os.getenv("DATABASE_URL", "")
    try:
        with get_session_factory()() as db:
            account_id = bootstrap_chief_admin(db, login=login, password=password, database_url=database_url, operator_secret=entered, configured_secret=configured)
        print(f"Bootstrap completed for account {account_id}")
        return 0
    except BootstrapError as exc:
        print(f"Bootstrap denied: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
