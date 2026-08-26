"""FastAPI application factory.

The lifespan handler builds the workspace client, runtime configuration, and storage
executor once and stores them on ``app.state`` for the request dependencies to read. Domain
exceptions from the library are translated to appropriate HTTP status codes, and the built
React SPA (when present) is served as static files.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from policy_agent.config import config_from_env, create_executor
from policy_agent.errors import (
    AuthorizationError,
    InvalidPolicyError,
    PolicyAgentError,
    UnsupportedResourceException,
    WorkflowError,
)

from policy_agent_app.backend.routes import api_router

_UI_DIST = Path(__file__).resolve().parent.parent / "ui" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Builds process-wide state at startup and exposes it on ``app.state``."""
    from databricks.sdk import WorkspaceClient

    config = config_from_env()
    workspace_client = WorkspaceClient()
    app.state.config = config
    app.state.workspace_client = workspace_client
    app.state.executor = create_executor(config, workspace_client)
    yield


def create_app() -> FastAPI:
    """Builds and configures the FastAPI application.

    Returns:
        The configured application.
    """
    app = FastAPI(title="Databricks Policy Agent", version="0.1.0", lifespan=lifespan)
    app.include_router(api_router)
    _register_exception_handlers(app)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    if _UI_DIST.is_dir():
        app.mount("/", StaticFiles(directory=str(_UI_DIST), html=True), name="ui")
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    handlers = {
        InvalidPolicyError: 400,
        UnsupportedResourceException: 400,
        AuthorizationError: 403,
        WorkflowError: 409,
        PolicyAgentError: 500,
    }
    for error_type, status_code in handlers.items():
        app.add_exception_handler(error_type, _make_handler(status_code))


def _make_handler(status_code: int):
    async def handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handler


app = create_app()
