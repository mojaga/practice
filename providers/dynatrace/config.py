"""Dynatrace credential schema.

Reads and validates only Dynatrace's own .env variables. Isolated here so
changing Dynatrace auth never touches another platform's config.
"""
from core.config import _env


class DynatraceConfig:
    def __init__(self):
        self.env_url = _env("DYNATRACE_ENV_URL", "https://<your-env-id>.apps.dynatrace.com")
        self.token = _env("DYNATRACE_API_TOKEN", "your-dynatrace-api-token")

    def missing(self):
        required = {
            "DYNATRACE_ENV_URL": self.env_url,
            "DYNATRACE_API_TOKEN": self.token,
        }
        return [name for name, value in required.items() if not value]
