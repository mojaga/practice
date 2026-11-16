"""SolarWinds provider package."""
from providers.solarwinds import connector
from providers.solarwinds.config import SolarWindsConfig
from providers.solarwinds.meta import SPEC


class SolarWindsProvider:
    spec = SPEC

    def _config(self):
        return SolarWindsConfig()

    def missing_credentials(self):
        return self._config().missing()

    def execute(self, query, verify_ssl=False):
        cfg = self._config()
        return connector.execute(cfg.server, cfg.user, cfg.password, query, verify_ssl=verify_ssl)

    def tools(self):
        return [
            {
                "name": "query_solarwinds",
                "description": (
                    "Run a SWQL (SolarWinds Query Language) query against SolarWinds Orion SWIS. "
                    "Returns nodes, interfaces, alerts, events, or any Orion entity."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "SWQL query, e.g. "
                                "SELECT NodeName, Status FROM Orion.Nodes WHERE Status = 2"
                            ),
                        }
                    },
                    "required": ["query"],
                },
            }
        ]

    def dispatch_tool(self, name, inputs, verify_ssl=False):
        if name == "query_solarwinds":
            return self.execute(inputs["query"], verify_ssl=verify_ssl)
        return {"error": f"Unknown tool: {name}"}


PROVIDER = SolarWindsProvider()
