"""Dynatrace provider package.

Assembles the identity (meta), credential schema (config), and connector into a
single object satisfying the `Provider` contract. `PROVIDER` is what the
registry registers.
"""
from providers.dynatrace import connector
from providers.dynatrace.config import DynatraceConfig
from providers.dynatrace.meta import SPEC


class DynatraceProvider:
    spec = SPEC

    def _config(self):
        # Read fresh each call so .env edits take effect on the next Streamlit run.
        return DynatraceConfig()

    def missing_credentials(self):
        return self._config().missing()

    def execute(self, query, verify_ssl=True):
        cfg = self._config()
        return connector.execute(cfg.env_url, cfg.token, query, verify_ssl=verify_ssl)

    def tools(self):
        return [
            {
                "name": "query_dynatrace",
                "description": (
                    "GET a Dynatrace Environment API v2 path. Use for problems, events, "
                    "metrics, entities, SLOs, and security problems."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "Relative API v2 path, e.g. "
                                "/api/v2/problems?from=now-24h&problemSelector=status(\"open\")&pageSize=100"
                            ),
                        }
                    },
                    "required": ["query"],
                },
            }
        ]

    def dispatch_tool(self, name, inputs, verify_ssl=True):
        if name == "query_dynatrace":
            return self.execute(inputs["query"], verify_ssl=verify_ssl)
        return {"error": f"Unknown tool: {name}"}


PROVIDER = DynatraceProvider()
