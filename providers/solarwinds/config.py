"""SolarWinds credential schema.

Reads and validates only SolarWinds' own .env variables.
"""
from core.config import _env


class SolarWindsConfig:
    def __init__(self):
        self.server = _env("SOLARWINDS_SERVER", "your-orion-server")
        self.user = _env("SOLARWINDS_USERNAME", "your-swis-username")
        self.password = _env("SOLARWINDS_PASSWORD", "your-swis-password")

    def missing(self):
        required = {
            "SOLARWINDS_SERVER": self.server,
            "SOLARWINDS_USERNAME": self.user,
            "SOLARWINDS_PASSWORD": self.password,
        }
        return [name for name, value in required.items() if not value]
