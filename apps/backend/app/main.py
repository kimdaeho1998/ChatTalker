from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=[],
        allow_private_network=True,
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        # Deliberately does not create or query a DB connection.
        return {"status": "ok", "service": "chatalker-backend", "database": "not_checked"}

    return app


app = create_app()
