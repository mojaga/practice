"""Provider registry.

A tiny in-memory registry that decouples the core/UI from concrete providers.
Providers register themselves (see `providers/__init__.py`); the agent and UI
discover them here by id. Adding a platform means registering a new package —
no edits to the agent's dispatch or the UI's routing.
"""
from core.interfaces import Provider

_REGISTRY: dict[str, Provider] = {}


def register(provider: Provider) -> None:
    """Add a provider to the registry, keyed by its spec id."""
    pid = provider.spec.id
    if pid in _REGISTRY:
        raise ValueError(f"Duplicate provider id: {pid!r}")
    _REGISTRY[pid] = provider


def all_providers() -> list[Provider]:
    """Every registered provider, in registration order."""
    return list(_REGISTRY.values())


def get(provider_id) -> Provider | None:
    """Look up a provider by id, or None if unknown/not selected."""
    return _REGISTRY.get(provider_id)
