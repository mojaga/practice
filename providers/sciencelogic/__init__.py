"""ScienceLogic provider package."""
from providers.sciencelogic import connector
from providers.sciencelogic.config import ScienceLogicConfig
from providers.sciencelogic.meta import SPEC


class ScienceLogicProvider:
    spec = SPEC

    def _config(self):
        return ScienceLogicConfig()

    def missing_credentials(self):
        return self._config().missing()

    def execute(self, query, verify_ssl=True):
        cfg = self._config()
        return connector.execute(cfg.server, cfg.user, cfg.password, query, verify_ssl=verify_ssl)

    def onboard_device(self, ip, cred_id, collector_group_id, org_id, verify_ssl=True):
        cfg = self._config()
        return connector.onboard_device(
            cfg.server, cfg.user, cfg.password,
            ip, cred_id, collector_group_id, org_id,
            verify_ssl=verify_ssl,
        )

    def tools(self):
        return [
            {
                "name": "query_sciencelogic",
                "description": (
                    "Read from ScienceLogic SL1 — use a REST path (/api/...) for "
                    "devices, events, and tickets, or a GraphQL block ({ ... }) for "
                    "real-time CPU/memory metrics."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "REST path e.g. /api/device?extended_fetch=1&limit=100, "
                                "or GraphQL e.g. { devices(limit:10) { id name cpuUtilization } }"
                            ),
                        }
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "onboard_device",
                "description": (
                    "Onboard a new device to ScienceLogic SL1 by IP address. "
                    "Call query_sciencelogic first to find cred_id (/api/credential/snmp) "
                    "and collector_group_id (/api/collector_group) if unknown."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ip":                 {"type": "string",  "description": "Device IP address"},
                        "cred_id":            {"type": "integer", "description": "SNMP credential ID"},
                        "collector_group_id": {"type": "integer", "description": "Collector group ID"},
                        "org_id":             {"type": "integer", "description": "Organization ID (0 = root org)"},
                    },
                    "required": ["ip", "cred_id", "collector_group_id", "org_id"],
                },
            },
        ]

    def dispatch_tool(self, name, inputs, verify_ssl=True):
        if name == "query_sciencelogic":
            return self.execute(inputs["query"], verify_ssl=verify_ssl)
        if name == "onboard_device":
            return self.onboard_device(
                inputs["ip"], inputs["cred_id"],
                inputs["collector_group_id"], inputs["org_id"],
                verify_ssl=verify_ssl,
            )
        return {"error": f"Unknown tool: {name}"}


PROVIDER = ScienceLogicProvider()
