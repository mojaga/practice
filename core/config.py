"""Base configuration primitives.

Loads the .env file once and exposes shared settings (the Claude model, the
Anthropic key) plus the `_env` helper that each provider's own config module
uses to read its credentials. Per-provider credentials deliberately do NOT live
here — they belong to each package under `providers/<name>/config.py`, so a
change to one platform's auth never touches shared code.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the project's .env file a single time.
# Anchor to this file's location (ObservIQ/core/config.py -> ObservIQ/.env) so
# the key loads no matter which directory the app is launched from.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Current Claude model. Opus 4.8 is the most capable; swap for
# "claude-sonnet-4-6" (faster/cheaper) or "claude-haiku-4-5-20251001".
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6").strip()  # or "claude-opus-4-8"


def _env(name, placeholder=""):
    """Read an env var, treating the default placeholder value as unset."""
    value = os.getenv(name, "").strip()
    return "" if value == placeholder else value


def anthropic_key():
    """The Anthropic API key, or "" if unset/placeholder."""
    return _env("ANTHROPIC_API_KEY", "your-anthropic-api-key-here")


def has_anthropic():
    return bool(anthropic_key())
