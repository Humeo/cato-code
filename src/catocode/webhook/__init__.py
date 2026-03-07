"""Webhook infrastructure for real-time GitHub event processing."""

from .verifier import verify_signature

__all__ = ["WebhookServer", "verify_signature"]


def __getattr__(name: str):
    if name == "WebhookServer":
        from .server import WebhookServer
        return WebhookServer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
