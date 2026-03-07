"""Registry that manages one ContainerManager per user (lazy initialization)."""

from __future__ import annotations

import logging

from .manager import ContainerManager

logger = logging.getLogger(__name__)


class ContainerRegistry:
    """Maintain a pool of ContainerManager instances, one per user_id."""

    def __init__(self) -> None:
        self._managers: dict[str, ContainerManager] = {}

    def get(self, user_id: str) -> ContainerManager:
        """Return the ContainerManager for the given user, creating it if needed."""
        if user_id not in self._managers:
            logger.debug("Creating ContainerManager for user %s", user_id[:8])
            self._managers[user_id] = ContainerManager(user_id=user_id)
        return self._managers[user_id]

    def stop_all(self) -> None:
        """Stop all managed containers (used during daemon shutdown)."""
        for user_id, mgr in self._managers.items():
            try:
                mgr.stop()
            except Exception as e:
                logger.error("Error stopping container for user %s: %s", user_id[:8], e)
