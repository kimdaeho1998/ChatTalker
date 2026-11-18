# Chatalker Backend

The SM-R01-A backend foundation targets Python 3.12 and exposes `GET /health`. Its response deliberately reports `database: not_checked`; a healthy HTTP response is not a PostgreSQL connectivity assertion.

Create a local Python 3.12 environment, install `.[dev]`, then run `uvicorn app.main:app --reload`. Copy `.env.example` to local `.env` only for a separately provisioned development database. Alembic refuses to run without `DATABASE_URL`.
