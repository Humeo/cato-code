"""FastAPI dependencies for session authentication."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException

from ..store import Store

logger = logging.getLogger(__name__)

# Store instance injected at app startup via app.state
_store: Store | None = None


def set_store(store: Store) -> None:
    global _store
    _store = store


def _get_store() -> Store:
    if _store is None:
        raise RuntimeError("Store not initialised in deps")
    return _store


async def get_current_user(
    session: str | None = Cookie(default=None),
    store: Store = Depends(_get_store),
) -> dict:
    """Validate session cookie and return the current user dict.

    Raises HTTP 401 if session is missing, expired, or invalid.
    """
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    row = store.get_session(session)
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = datetime.fromisoformat(row["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        store.delete_session(session)
        raise HTTPException(status_code=401, detail="Session expired")

    user = store.get_user(row["user_id"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return dict(user)


CurrentUser = Annotated[dict, Depends(get_current_user)]
