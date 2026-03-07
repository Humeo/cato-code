"""FastAPI application factory for SaaS mode."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_frontend_url
from ..store import Store
from . import deps as _deps
from .oauth import router as oauth_router
from .routes import make_router as make_api_router


def create_app(store: Store) -> FastAPI:
    """Build and return the FastAPI application.

    Mounts:
    - /auth/*   — GitHub OAuth flow (oauth_router)
    - /api/*    — Protected REST API (api_router, session-guarded)
    - /webhook  — GitHub App webhooks (mounted externally by caller)
    """
    app = FastAPI(title="CatoCode SaaS API")

    # Store on app.state so route handlers can access it via request.app.state.store
    app.state.store = store

    # Inject store into session-dependency module
    _deps.set_store(store)

    frontend_url = get_frontend_url()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_url],
        allow_credentials=True,  # required for cookie-based sessions
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # OAuth flow (unauthenticated)
    app.include_router(oauth_router)

    # Protected API routes
    api_router = make_api_router(store)
    app.include_router(api_router, prefix="/api")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app
