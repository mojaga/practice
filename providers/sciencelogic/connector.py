"""ScienceLogic SL1 (SaaS) connector.

Supports two query modes, auto-detected from the query string:
  - GraphQL  — query starts with '{' or 'query ' → POST to /graphql
  - REST      — query starts with '/api/'         → GET  to /api/...

GraphQL is preferred for device performance metrics (CPU, memory) because
the classic REST /api/device endpoint does not expose real-time utilization.
REST is kept as a fallback for events, tickets, and other REST-only resources.
"""
import warnings

import requests
from requests.auth import HTTPBasicAuth

from utils.formatters import http_error_detail


def _base_host(server: str) -> str:
    host = server.strip().rstrip("/")
    if host.startswith("http://") or host.startswith("https://"):
        host = host.split("://", 1)[1]
    return host.split("/", 1)[0].rstrip("/")


def _execute_graphql(host, username, password, graphql_query, verify_ssl):
    """POST a GraphQL query to the SL1 /graphql endpoint."""
    endpoint = f"https://{host}/graphql"
    try:
        if not verify_ssl:
            warnings.simplefilter("ignore", requests.packages.urllib3.exceptions.InsecureRequestWarning)
        response = requests.post(
            endpoint,
            json={"query": graphql_query},
            auth=HTTPBasicAuth(username, password),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            verify=verify_ssl,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        # Surface GraphQL-layer errors (HTTP 200 but errors key present)
        if "errors" in payload and payload["errors"]:
            return {"error": payload["errors"]}
        return payload.get("data", payload)
    except requests.exceptions.HTTPError as e:
        return {"error": http_error_detail(e)}
    except Exception as e:
        return {"error": str(e)}


def _execute_post(host, username, password, api_path, payload, verify_ssl):
    """POST a JSON payload to a SL1 REST endpoint."""
    endpoint = f"https://{host}{api_path}"
    try:
        if not verify_ssl:
            warnings.simplefilter("ignore", requests.packages.urllib3.exceptions.InsecureRequestWarning)
        response = requests.post(
            endpoint,
            json=payload,
            auth=HTTPBasicAuth(username, password),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            verify=verify_ssl,
            timeout=30,
        )
        response.raise_for_status()
        return {
            "status": "created",
            "location": response.headers.get("Location", ""),
            "body": response.json() if response.content else {},
        }
    except requests.exceptions.HTTPError as e:
        return {"error": http_error_detail(e)}
    except Exception as e:
        return {"error": str(e)}


def _execute_rest(host, username, password, api_path, verify_ssl):
    """GET a relative SL1 REST path (e.g. /api/event?extended_fetch=1&limit=100)."""
    path = api_path.strip()
    if not path.startswith("/"):
        path = "/" + path
    endpoint = f"https://{host}{path}"
    try:
        if not verify_ssl:
            warnings.simplefilter("ignore", requests.packages.urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(
            endpoint,
            auth=HTTPBasicAuth(username, password),
            headers={"Accept": "application/json"},
            verify=verify_ssl,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        return {"error": http_error_detail(e)}
    except Exception as e:
        return {"error": str(e)}


def onboard_device(server, username, password, ip, cred_id,
                   collector_group_id, org_id, verify_ssl=True):
    """Onboard a new device to SL1 via POST /api/device.

    cred_id, collector_group_id, org_id are integer IDs; the connector
    converts them to the URI references SL1 expects.
    Returns {"status": "created", "location": "/api/device/42", "body": {...}}
    or {"error": "..."} on failure.
    """
    host = _base_host(server)
    payload = {
        "ip":                     ip,
        "aligned_credential":     f"/api/credential/snmp/{cred_id}",
        "aligned_collectorgroup": f"/api/collector_group/{collector_group_id}",
        "organization":           f"/api/organization/{org_id}",
    }
    return _execute_post(host, username, password, "/api/device", payload, verify_ssl)


def execute(server, username, password, query, verify_ssl=True):
    """Route to GraphQL or REST based on query format."""
    host = _base_host(server)
    q = query.strip()
    if q.startswith("{") or q.lower().startswith("query "):
        return _execute_graphql(host, username, password, q, verify_ssl)
    return _execute_rest(host, username, password, q, verify_ssl)
