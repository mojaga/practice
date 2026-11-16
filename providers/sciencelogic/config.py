"""ScienceLogic credential schema.

Reads and validates only ScienceLogic's own .env variables.
"""
from core.config import _env


class ScienceLogicConfig:
    def __init__(self):
        self.server = _env("SCIENCELOGIC_SERVER", "your-tenant.sciencelogic.io")
        self.user = _env("SCIENCELOGIC_USERNAME", "your-sl1-username")
        self.password = _env("SCIENCELOGIC_PASSWORD", "your-sl1-password")

    def missing(self):
        required = {
            "SCIENCELOGIC_SERVER": self.server,
            "SCIENCELOGIC_USERNAME": self.user,
            "SCIENCELOGIC_PASSWORD": self.password,
        }
        return [name for name, value in required.items() if not value]
