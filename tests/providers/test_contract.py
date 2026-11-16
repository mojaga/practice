"""Contract tests — the guardrail that keeps providers isolated and uniform.

These run without network access or credentials: they verify every registered
provider satisfies the `Provider` protocol and exposes complete, unique
metadata. If a new platform package forgets part of the contract, this fails
fast instead of breaking the app at runtime.
"""
import providers  # noqa: F401  — registers all providers
from core import registry
from core.interfaces import Provider


def test_registry_is_populated():
    assert registry.all_providers(), "no providers registered"


def test_all_providers_satisfy_contract():
    for provider in registry.all_providers():
        assert isinstance(provider, Provider), f"{provider!r} does not satisfy Provider"
        assert callable(provider.execute)
        assert isinstance(provider.missing_credentials(), list)


def test_specs_are_complete():
    for provider in registry.all_providers():
        spec = provider.spec
        for field_name in ("id", "name", "icon", "tagline", "query_lang", "code_lang", "query_gen_prompt"):
            assert getattr(spec, field_name), f"{spec.id}: empty {field_name}"


def test_ids_are_unique():
    ids = [p.spec.id for p in registry.all_providers()]
    assert len(ids) == len(set(ids)), f"duplicate provider ids: {ids}"
