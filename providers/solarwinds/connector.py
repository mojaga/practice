"""SolarWinds Orion connector — custom query functions.

Wraps the SolarWinds Information Service (SWIS) query endpoint as a direct REST
client. Vendor MCP integration for SolarWinds would live beside this in `mcp.py`.

Query language: SWQL (SolarWinds Query Language).
"""
import warnings

import requests
from requests.auth import HTTPBasicAuth

from utils.formatters import http_error_detail


def execute(server, username, password, swql_query, verify_ssl=False):
    """Run a SWQL query against the SWIS endpoint (port 17774)."""
    host = server.strip().rstrip("/")
    if host.startswith("http://") or host.startswith("https://"):
        host = host.split("://", 1)[1]
    host = host.split(":", 1)[0]  # drop any port the user may have typed
    endpoint = f"https://{host}:17774/SolarWinds/InformationService/v3/Json/Query"
    payload = {"query": swql_query}

    try:
        if not verify_ssl:
            # Silence the self-signed-cert warning when verification is disabled.
            warnings.simplefilter("ignore", requests.packages.urllib3.exceptions.InsecureRequestWarning)
        response = requests.post(
            endpoint,
            json=payload,
            auth=HTTPBasicAuth(username, password),
            headers={"Content-Type": "application/json"},
            verify=verify_ssl,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        # SWIS returns {"results": [ {...}, ... ]}
        return data.get("results", data)
    except requests.exceptions.HTTPError as e:
        return {"error": http_error_detail(e)}
    except Exception as e:
        return {"error": str(e)}
